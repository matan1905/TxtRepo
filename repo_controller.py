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

# ... (previous code remains the same)

def create_pull_request(repo_path: Path, github_token: str):
    try:
        # Set up Git configuration
        subprocess.run(["git", "config", "user.name", "GitHub Actions"], cwd=repo_path, check=True, capture_output=True, text=True)
        subprocess.run(["git", "config", "user.email", "actions@github.com"], cwd=repo_path, check=True, capture_output=True, text=True)

        # Check if there are any changes
        status_output = subprocess.check_output(["git", "status", "--porcelain"], cwd=repo_path, text=True)
        if not status_output.strip():
            return "No changes to commit"

        # Create a new branch
        branch_name = f"update-{int(time.time())}"
        subprocess.run(["git", "checkout", "-b", branch_name], cwd=repo_path, check=True, capture_output=True, text=True)

        # Commit changes
        subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True, text=True)
        subprocess.run(["git", "commit", "-m", "Update repository"], cwd=repo_path, check=True, capture_output=True, text=True)

        # Push changes
        remote_url = subprocess.check_output(["git", "remote", "get-url", "origin"], cwd=repo_path, text=True).strip()
        auth_remote = re.sub(r"https://", f"https://x-access-token:{github_token}@", remote_url)
        push_result = subprocess.run(["git", "push", "-u", auth_remote, branch_name], cwd=repo_path, capture_output=True, text=True)
        if push_result.returncode != 0:
            raise subprocess.CalledProcessError(push_result.returncode, push_result.args, push_result.stdout, push_result.stderr)

        # Create pull request using GitHub CLI
        auth_result = subprocess.run(["gh", "auth", "login", "--with-token"], input=github_token, text=True, capture_output=True)
        if auth_result.returncode != 0:
            raise subprocess.CalledProcessError(auth_result.returncode, auth_result.args, auth_result.stdout, auth_result.stderr)

        pr_result = subprocess.run(["gh", "pr", "create", "--title", "Update repository", "--body", "Automated update"], cwd=repo_path, capture_output=True, text=True)
        if pr_result.returncode != 0:
            raise subprocess.CalledProcessError(pr_result.returncode, pr_result.args, pr_result.stdout, pr_result.stderr)
        
        return pr_result.stdout.strip()
    except subprocess.CalledProcessError as e:
        error_message = f"Command '{e.cmd}' returned non-zero exit status {e.returncode}.\nStdout: {e.stdout}\nStderr: {e.stderr}"
        logging.error(error_message)
        raise HTTPException(status_code=500, detail=error_message)
    except Exception as e:
        error_message = f"Unexpected error: {str(e)}"
        logging.error(error_message)
        raise HTTPException(status_code=500, detail=error_message)

# ... (rest of the code remains the same)

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
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
