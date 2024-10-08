import os
from dotenv import load_dotenv

load_dotenv()
from dsl.factory import DslInstructionFactory
from dsl.base import DslInstruction
import os
import subprocess
import tempfile
import sys
import re
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel
import shutil
import time
import asyncio
from typing import Dict, Any, List, Optional
import logging

app = FastAPI()
# Mount the static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def root():
    with open("static/index.html", "r") as f:
        content = f.read()
    return HTMLResponse(content=content)


# Cache to store cloned repositories
repo_cache: Dict[str, Dict[str, Any]] = {}
CACHE_EXPIRATION = int(os.getenv('CACHE_EXPIRATION', 3600))
REPO_BASE_DIR = Path(os.getenv('REPO_BASE_DIR', '/tmp/repos'))




class PullRequestRequest(BaseModel):
    git_url: str
    github_token: str
    summary: str
    branch: str = "main"
    pr_branch: Optional[str] = None
    pr_title: Optional[str] = None
    pr_description: Optional[str] = None


def extract_repo_info(git_url: str) -> tuple:
    match = re.search(r'github\.com[:/]([^/]+)/([^/]+?)(.git)?$', git_url)
    if match:
        return match.group(1), match.group(2)
    return None, None


def clone_repo(git_url: str, clone_dir: Path):
    try:
        subprocess.run(["git", "clone", git_url, str(clone_dir)], check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=400, detail=f"Error cloning repository: {e.stderr}")


async def run_code2prompt(clone_dir: Path, git_url: str, filter_patterns: Optional[str] = None,
                          exclude_patterns: Optional[str] = None, case_sensitive: bool = False,
                          suppress_comments: bool = False, line_number: bool = False):
    cmd = ["code2prompt", "--path", str(clone_dir), "--template", 'template.j2']

    if filter_patterns:
        cmd.extend(["--filter", filter_patterns])
    if exclude_patterns:
        cmd.extend(["--exclude", exclude_patterns])
    if case_sensitive:
        cmd.append("--case-sensitive")
    if suppress_comments:
        cmd.append("--suppress-comments")
    if line_number:
        cmd.append("--line-number")

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    if process.returncode != 0:
        raise HTTPException(status_code=500, detail=f"Error running code2prompt: {stderr.decode()}")

    output = stdout.decode()
    return process_relative_paths(output, clone_dir, git_url)


def process_relative_paths(output: str, base_path: Path, git_url: str) -> str:
    repo_user, repo_name = extract_repo_info(git_url)
    friendly_base = f"/{repo_user}/{repo_name}" if repo_user and repo_name else "/unknown/repo"

    lines = output.split('\n')
    processed_lines = []
    for line in lines:
        if base_path.as_posix() in line:
            relative_path = Path(line.split(base_path.as_posix())[-1].strip()).as_posix().lstrip('/')
            if line.startswith("- "):
                processed_lines.append(f"- {friendly_base}/{relative_path}")
            elif "## File: " in line:
                processed_lines.append(f"## File: {friendly_base}/{relative_path}")
        else:
            processed_lines.append(line)
    return '\n'.join(processed_lines)


def parse_summary(summary: str, repo_path: Path, user: Optional[str] = None, repo: Optional[str] = None):
    file_pattern = re.compile(r'# File (.*?)(::.*?)?\n(.*?)# EndFile \1', re.DOTALL)
    files = []
    last_end = 0

    for match in file_pattern.finditer(summary):
        if match.start() < last_end:
            continue  # Skip nested matches

        path = match.group(1).strip()
        command = match.group(2) and match.group(2).strip()
        content = match.group(3).strip()
        last_end = match.end()

        # Remove repo path from path (repo_path is of type Path)
        if path.startswith(str(repo_path)):
            path = path[len(str(repo_path)):]
        elif user and repo and path.startswith(f"/{user}/{repo}"):
            path = path[len(f"/{user}/{repo}"):]

        # Parse the DSL instructions
        dsl_instructions = parse_dsl(command[2:] if command else "")

        files.append({'path': path, 'content': content, 'dsl': dsl_instructions, 'pathAndCommand': str(path)+str(command if command else '')})

    return files


def parse_dsl(dsl_string: str) -> DslInstruction:
    return DslInstructionFactory.create(dsl_string)



def get_safe_path(repo_path: Path, file_path: str) -> Path:
    """Ensure the file path is within the repo directory."""
    normalized_path = os.path.normpath(file_path).lstrip('/')

    # If the path doesn't start with the repo_path, prepend it
    if not normalized_path.startswith(str(repo_path)):
        full_path = (repo_path / normalized_path).resolve()
    else:
        full_path = Path(normalized_path).resolve()

    # Check if the resolved path starts with any parent of repo_path
    repo_parents = [repo_path] + list(repo_path.parents)
    if not any(str(full_path).startswith(str(parent)) for parent in repo_parents):
        logging.warning(f"Attempted to access path outside repo: {full_path}")
        raise HTTPException(status_code=400, detail=f"Invalid file path: {file_path}")

    logging.info(f"repo_path: {repo_path}")
    logging.info(f"file_path: {file_path}")
    logging.info(f"normalized_path: {normalized_path}")
    logging.info(f"full_path: {full_path}")
    logging.info(f"repo_parents: {repo_parents}")

    return full_path


def update_repo(files: list, repo_path: Path):
    sorted_files = sorted(files, key=lambda x: x['pathAndCommand'], reverse=True)  # this prevents

    for file in sorted_files:
        path = file['path']
        content = file['content']
        dsl_instruction = file['dsl']

        try:
            file_path = get_safe_path(repo_path, path)
            logging.info(f"Processing file: {file_path}")

            if dsl_instruction:
                with open(file_path, 'r') as f:
                    lines = f.readlines()
                new_lines, message = dsl_instruction.apply(file_path, content, lines)
                if new_lines:
                    with open(file_path, 'w') as f:
                        f.writelines(new_lines)
            else:
                file_path.parent.mkdir(parents=True, exist_ok=True)
                with open(file_path, 'w') as f:
                    f.write(content.strip())
                logging.info(f"Updated file: {file_path}")
        except Exception as e:
            logging.error(f"Error processing file {path}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error processing file {path}: {str(e)}")


def create_pull_request(repo_path: Path, github_token: str, source_branch: str, pr_branch: Optional[str] = None, pr_title: Optional[str] = None, pr_description: Optional[str] = None):
    try:
        # Set up Git configuration
        subprocess.run(["git", "config", "user.name", "GitHub Actions"], cwd=repo_path, check=True, capture_output=True,
                       text=True)
        subprocess.run(["git", "config", "user.email", "actions@github.com"], cwd=repo_path, check=True,
                       capture_output=True, text=True)

        # Check if there are any changes
        status_output = subprocess.check_output(["git", "status", "--porcelain"], cwd=repo_path, text=True)
        if not status_output.strip():
            logging.info("No changes to commit")
            return "No changes to commit"

        # Create a new branch
        branch_name = pr_branch if pr_branch else f"update-{int(time.time())}_txt-repo_{int(time.time())}"
        subprocess.run(["git", "checkout", "-b", branch_name], cwd=repo_path, check=True, capture_output=True,
                       text=True)

        # Commit changes
        subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True, text=True)
        subprocess.run(["git", "commit", "-m", "Update repository"], cwd=repo_path, check=True, capture_output=True,
                       text=True)

        # Get the remote URL and add the token
        remote_url = subprocess.check_output(["git", "remote", "get-url", "origin"], cwd=repo_path, text=True).strip()
        auth_remote = re.sub(r"https://", f"https://x-access-token:{github_token}@", remote_url)

        # Push changes
        logging.info(f"Pushing changes to branch: {branch_name}")
        push_result = subprocess.run(["git", "push", "-u", auth_remote, branch_name], cwd=repo_path,
                                     capture_output=True, text=True)
        if push_result.returncode != 0:
            raise subprocess.CalledProcessError(push_result.returncode, push_result.args, push_result.stdout,
                                                push_result.stderr)

        # Create pull request using GitHub CLI
        logging.info("Authenticating with GitHub CLI")
        auth_result = subprocess.run(["gh", "auth", "login", "--with-token"], input=github_token, text=True,
                                     capture_output=True)
        if auth_result.returncode != 0:
            raise subprocess.CalledProcessError(auth_result.returncode, auth_result.args, auth_result.stdout,
                                                auth_result.stderr)

        logging.info("Creating pull request")
        pr_command = ["gh", "pr", "create", "--head", branch_name, "--base", source_branch]
        if pr_title:
            pr_command.extend(["--title", pr_title])
        else:
            pr_command.extend(["--title", "Update repository"])
        if pr_description:
            pr_command.extend(["--body", pr_description])
        else:
            pr_command.extend(["--body", "Automated update"])
        pr_result = subprocess.run(pr_command, cwd=repo_path, capture_output=True, text=True)
        if pr_result.returncode != 0:
            raise subprocess.CalledProcessError(pr_result.returncode, pr_result.args, pr_result.stdout,
                                                pr_result.stderr)

        logging.info("Pull request created successfully")
        return pr_result.stdout.strip()
    except subprocess.CalledProcessError as e:
        error_message = f"Command '{e.cmd}' returned non-zero exit status {e.returncode}.\nStdout: {e.stdout}\nStderr: {e.stderr}"
        logging.error(error_message)
        raise HTTPException(status_code=500, detail=error_message)
    except Exception as e:
        error_message = f"Unexpected error: {str(e)}"
        logging.error(error_message)
        raise HTTPException(status_code=500, detail=error_message)


def get_cached_repo(git_url: str, branch: str, user: Optional[str] = None, repo: Optional[str] = None) -> Path:
    # Extract user and repo name from git_url
    if not user or not repo:
        raise HTTPException(status_code=400, detail="Invalid git URL")
    
    repo_path = REPO_BASE_DIR / user / repo
    if not repo_path.exists():
        repo_path.mkdir(parents=True, exist_ok=True)
        clone_repo(git_url, repo_path)

    # Clean all previous changes
    subprocess.run(["git", "clean", "-fd"], cwd=repo_path, check=True, capture_output=True, text=True)
    subprocess.run(["git", "reset", "--hard"], cwd=repo_path, check=True, capture_output=True, text=True)

    # Checkout to the specified branch
    subprocess.run(["git", "checkout", branch], cwd=repo_path, check=True, capture_output=True, text=True)
    subprocess.run(["git", "pull", "origin", branch], cwd=repo_path, check=True, capture_output=True, text=True)

    return repo_path

@app.get("/repo")
async def get_repo_summary(
        background_tasks: BackgroundTasks,
        git_url: str = Query(..., description="The URL of the GitHub repository"),
        branch: str = Query("main", description="Branch to fetch"),
        filter_patterns: Optional[str] = Query(None,
                                               description="Comma-separated filter patterns to include files (e.g., '*.py,*.js')"),
        exclude_patterns: Optional[str] = Query(None,
                                                description="Comma-separated patterns to exclude files (e.g., '*.txt,*.md')"),
        case_sensitive: bool = Query(False, description="Perform case-sensitive pattern matching"),
        suppress_comments: bool = Query(False, description="Strip comments from the code files"),
        line_number: bool = Query(False, description="Add line numbers to source code blocks")
):
    user, repo = extract_repo_info(git_url)

    repo_path = get_cached_repo(git_url, branch, user, repo)
    summary = await run_code2prompt(
        repo_path,
        git_url,
        filter_patterns,
        exclude_patterns,
        case_sensitive,
        suppress_comments,
        line_number
    )
    return {"summary": summary}
def clean_old_repos(background_tasks: BackgroundTasks):
    def cleanup():
        current_time = time.time()
        for git_url, cache_info in list(repo_cache.items()):
            if current_time - cache_info['timestamp'] >= CACHE_EXPIRATION:
                shutil.rmtree(cache_info['path'])
                del repo_cache[git_url]

    background_tasks.add_task(cleanup)


@app.post("/repo")
async def apply_changes_and_create_pr(pr_request: PullRequestRequest, background_tasks: BackgroundTasks):
    user, repo = extract_repo_info(pr_request.git_url)
    repo_path = get_cached_repo(pr_request.git_url, pr_request.branch, user, repo)

    files = parse_summary(pr_request.summary, repo_path, user, repo)
    update_repo(files, repo_path)

    try:
        pr_url = create_pull_request(
            repo_path,
            pr_request.github_token,
            pr_request.branch,
            pr_request.pr_branch,
            pr_request.pr_title,
            pr_request.pr_description
        )
        return {"pull_request_url": pr_url}
    except HTTPException as e:
        return {"error": e.detail}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    REPO_BASE_DIR.mkdir(parents=True, exist_ok=True)
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
