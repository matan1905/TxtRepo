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

app = FastAPI()

# Cache to store cloned repositories
repo_cache: Dict[str, Dict[str, Any]] = {}
CACHE_EXPIRATION = 3600  # 1 hour

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
        "code2prompt", "--path", str(clone_dir),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    if process.returncode != 0:
        raise HTTPException(status_code=500, detail=f"Error running code2prompt: {stderr.decode()}")
    return stdout.decode()

def parse_summary(summary: str):
    file_pattern = re.compile(r"##\s+File:\s+([\w./-]+)\n\n.*?###\s+Code\n\n```(\w+)\n(.*?)```", re.DOTALL)
    files = file_pattern.findall(summary)
    return [{'path': f[0], 'language': f[1], 'content': f[2]} for f in files]

def update_repo(files: list, repo_path: Path):
    for file in files:
        path = file['path']
        content = file['content']
        language = file['language']

        file_path = repo_path / path
        if language.strip().startswith("deleted"):
            if file_path.exists():
                file_path.unlink()
        else:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, 'w') as f:
                f.write(content.strip())

def create_pull_request(repo_path: Path, github_token: str):
    try:
        # Set up Git configuration
        subprocess.run(["git", "config", "user.name", "GitHub Actions"], cwd=repo_path, check=True)
        subprocess.run(["git", "config", "user.email", "actions@github.com"], cwd=repo_path, check=True)

        # Create a new branch
        branch_name = f"update-{int(time.time())}"
        subprocess.run(["git", "checkout", "-b", branch_name], cwd=repo_path, check=True)

        # Commit changes
        subprocess.run(["git", "add", "."], cwd=repo_path, check=True)
        subprocess.run(["git", "commit", "-m", "Update repository"], cwd=repo_path, check=True)

        # Push changes
        remote_url = subprocess.check_output(["git", "remote", "get-url", "origin"], cwd=repo_path, text=True).strip()
        auth_remote = re.sub(r"https://", f"https://x-access-token:{github_token}@", remote_url)
        subprocess.run(["git", "push", "-u", auth_remote, branch_name], cwd=repo_path, check=True)

        # Create pull request using GitHub CLI
        subprocess.run(["gh", "auth", "login", "--with-token"], input=github_token, text=True, check=True)
        pr_output = subprocess.check_output(["gh", "pr", "create", "--title", "Update repository", "--body", "Automated update"], cwd=repo_path, text=True)
        
        return pr_output.strip()
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Error creating pull request: {e.stderr}")

def get_cached_repo(git_url: str) -> Path:
    if git_url in repo_cache:
        cache_info = repo_cache[git_url]
        if time.time() - cache_info['timestamp'] < CACHE_EXPIRATION:
            return cache_info['path']
        else:
            shutil.rmtree(cache_info['path'])
            del repo_cache[git_url]
    
    repo_path = Path(tempfile.mkdtemp()) / "repo"
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
    
    pr_url = create_pull_request(repo_path, pr_request.github_token)
    return {"pull_request_url": pr_url}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
