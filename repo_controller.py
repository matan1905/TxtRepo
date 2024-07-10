import os
import subprocess
import tempfile
import sys
import re
from pathlib import Path
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
import shutil
import time
import asyncio
from typing import Dict, Any
import logging

app = FastAPI()

# Cache to store cloned repositories
repo_cache: Dict[str, Dict[str, Any]] = {}
CACHE_EXPIRATION = 3600  # 1 hour
REPO_BASE_DIR = Path("/tmp/repos")  # Base directory for repositories


class RepoRequest(BaseModel):
    git_url: str


class PullRequestRequest(BaseModel):
    git_url: str
    github_token: str
    summary: str


def clone_repo(git_url: str, clone_dir: Path):
    try:
        subprocess.run(["git", "clone", git_url, str(clone_dir)], check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=400, detail=f"Error cloning repository: {e.stderr}")


async def run_code2prompt(clone_dir: Path):
    process = await asyncio.create_subprocess_exec(
        "code2prompt", "--path", str(clone_dir), "--template",'template.j2',
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    if process.returncode != 0:
        raise HTTPException(status_code=500, detail=f"Error running code2prompt: {stderr.decode()}")

    # Process the output to use relative paths
    output = stdout.decode()
    return process_relative_paths(output, clone_dir)


def process_relative_paths(output: str, base_path: Path) -> str:
    lines = output.split('\n')
    processed_lines = []
    for line in lines:
        if line.startswith("- ") and base_path.as_posix() in line:
            relative_path = Path(line.split(base_path.as_posix())[-1].strip()).as_posix().lstrip('/')
            processed_lines.append(f"- {relative_path}")
        elif "## File: " in line and base_path.as_posix() in line:
            relative_path = Path(line.split(base_path.as_posix())[-1].strip()).as_posix().lstrip('/')
            processed_lines.append(f"## File: {relative_path}")
        else:
            processed_lines.append(line)
    return '\n'.join(processed_lines)


def parse_summary(summary: str):
    file_pattern = re.compile(r'# File (.*?)\n(.*?)# EndFile \1', re.DOTALL)
    files = []
    last_end = 0

    for match in file_pattern.finditer(summary):
        # Check if this match is contained within a previous match
        if match.start() < last_end:
            continue  # Skip this match as it's nested

        path = match.group(1).strip()
        content = match.group(2).strip()
        last_end = match.end()

        if path.startswith("DELETED:"):
            files.append({'path': path[8:].strip(), 'content': '', 'should_delete': True})  # Remove "DELETED:" prefix
        else:
            files.append({'path': path, 'content': content, 'should_delete': False})

    return files

def get_safe_path(repo_path: Path, file_path: str) -> Path:
    """Ensure the file path is within the repo directory."""
    normalized_path = os.path.normpath(file_path).lstrip('/')
    full_path = (repo_path / normalized_path).resolve()

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
    for file in files:
        path = file['path']
        content = file['content']
        should_delete = file['should_delete']

        try:
            file_path = get_safe_path(repo_path, path)
            logging.info(f"Processing file: {file_path}")

            if should_delete:
                if file_path.exists():
                    file_path.unlink()
                    logging.info(f"Deleted file: {file_path}")
                else:
                    logging.warning(f"Attempted to delete non-existent file: {file_path}")
            else:
                file_path.parent.mkdir(parents=True, exist_ok=True)
                with open(file_path, 'w') as f:
                    f.write(content.strip())
                logging.info(f"Updated file: {file_path}")
        except Exception as e:
            logging.error(f"Error processing file {path}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error processing file {path}: {str(e)}")


def create_pull_request(repo_path: Path, github_token: str):
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
        branch_name = f"update-{int(time.time())}"
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
        pr_result = subprocess.run(
            ["gh", "pr", "create", "--title", "Update repository", "--body", "Automated update", "--head", branch_name],
            cwd=repo_path, capture_output=True, text=True)
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


def get_cached_repo(git_url: str) -> Path:
    if git_url in repo_cache:
        cache_info = repo_cache[git_url]
        if time.time() - cache_info['timestamp'] < CACHE_EXPIRATION:
            return cache_info['path']
        else:
            shutil.rmtree(cache_info['path'])
            del repo_cache[git_url]

    repo_path = REPO_BASE_DIR / f"repo_{int(time.time())}"
    repo_path.mkdir(parents=True, exist_ok=True)
    clone_repo(git_url, repo_path)
    repo_cache[git_url] = {'path': repo_path, 'timestamp': time.time()}
    return repo_path


def clean_old_repos(background_tasks: BackgroundTasks):
    def cleanup():
        current_time = time.time()
        for git_url, cache_info in list(repo_cache.items()):
            if current_time - cache_info['timestamp'] >= CACHE_EXPIRATION:
                shutil.rmtree(cache_info['path'])
                del repo_cache[git_url]

    background_tasks.add_task(cleanup)


@app.get("/repo")
async def get_repo_summary(repo_request: RepoRequest, background_tasks: BackgroundTasks):
    clean_old_repos(background_tasks)
    repo_path = get_cached_repo(repo_request.git_url)
    summary = await run_code2prompt(repo_path)
    return {"summary": summary}


@app.post("/repo")
async def apply_changes_and_create_pr(pr_request: PullRequestRequest, background_tasks: BackgroundTasks):
    clean_old_repos(background_tasks)
    repo_path = get_cached_repo(pr_request.git_url)

    files = parse_summary(pr_request.summary)
    update_repo(files, repo_path)

    try:
        pr_url = create_pull_request(repo_path, pr_request.github_token)
        return {"pull_request_url": pr_url}
    except HTTPException as e:
        return {"error": e.detail}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    REPO_BASE_DIR.mkdir(parents=True, exist_ok=True)
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)