import os
import re
import time
import logging
import shutil
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional
from fastapi import HTTPException
from git import Repo, GitCommandError
from github import Github

REPO_BASE_DIR = Path("/tmp/repos")
CACHE_EXPIRATION = 3600  # 1 hour

repo_cache: Dict[str, Dict[str, Any]] = {}

def extract_repo_info(git_url: str) -> tuple:
    match = re.search(r'github\.com[:/]([^/]+)/([^/]+?)(.git)?$', git_url)
    if match:
        return match.group(1), match.group(2)
    return None, None

def get_cached_repo(git_url: str, branch: str) -> Path:
    if git_url in repo_cache:
        cache_info = repo_cache[git_url]
        if time.time() - cache_info['timestamp'] < CACHE_EXPIRATION:
            repo_path = cache_info['path']
            repo = Repo(repo_path)
            repo.git.checkout(branch)
            repo.remotes.origin.pull()
            return repo_path

    repo_path = REPO_BASE_DIR / f"repo_{int(time.time())}"
    repo_path.mkdir(parents=True, exist_ok=True)
    
    try:
        repo = Repo.clone_from(git_url, repo_path)
        repo.git.checkout(branch)
    except GitCommandError as e:
        raise HTTPException(status_code=400, detail=f"Error cloning repository: {str(e)}")

    repo_cache[git_url] = {'path': repo_path, 'timestamp': time.time()}
    return repo_path

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

def parse_summary(summary: str, repo_path: Path):
    # Implementation remains the same
    pass

def update_repo(files: list, repo_path: Path):
    # Implementation remains the same
    pass

def create_pull_request(repo_path: Path, github_token: str, source_branch: str):
    try:
        repo = Repo(repo_path)
        repo.git.add(A=True)
        repo.git.commit('-m', "Update repository")

        branch_name = f"update-{int(time.time())}"
        repo.git.checkout('-b', branch_name)

        remote_url = repo.remotes.origin.url
        auth_remote = re.sub(r"https://", f"https://x-access-token:{github_token}@", remote_url)
        repo.git.push(auth_remote, branch_name)

        g = Github(github_token)
        repo_user, repo_name = extract_repo_info(remote_url)
        github_repo = g.get_repo(f"{repo_user}/{repo_name}")
        pr = github_repo.create_pull(title="Update repository",
                                     body="Automated update",
                                     head=branch_name,
                                     base=source_branch)

        return pr.html_url
    except Exception as e:
        error_message = f"Error creating pull request: {str(e)}"
        logging.error(error_message)
        raise HTTPException(status_code=500, detail=error_message)

def clean_old_repos(background_tasks: BackgroundTasks):
    def cleanup():
        current_time = time.time()
        for git_url, cache_info in list(repo_cache.items()):
            if current_time - cache_info['timestamp'] >= CACHE_EXPIRATION:
                shutil.rmtree(cache_info['path'])
                del repo_cache[git_url]

    background_tasks.add_task(cleanup)