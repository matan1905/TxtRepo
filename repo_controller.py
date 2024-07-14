from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel
import subprocess
import logging
import os
from github import Github
from github import Auth
---
class PullRequestRequest(BaseModel):
    git_url: str
    github_token: str
    summary: str
    branch: str = "main"
+++
class PullRequestRequest(BaseModel):
    git_url: str
    summary: str
    branch: str = "main"

def authenticate_github_app():
    app_id = os.environ.get('GITHUB_APP_ID')
    private_key = os.environ.get('GITHUB_PRIVATE_KEY')
    if not app_id or not private_key:
        raise HTTPException(status_code=500, detail="GitHub App credentials not configured")
    
    auth = Auth.AppAuth(app_id, private_key)
    return Github(auth=auth)

def create_pull_request(repo_path: Path, source_branch: str):
    try:
        # Set up Git configuration
        subprocess.run(["git", "config", "user.name", "GitHub App"], cwd=repo_path, check=True, capture_output=True, text=True)
        subprocess.run(["git", "config", "user.email", "github-app@example.com"], cwd=repo_path, check=True, capture_output=True, text=True)

        # Check if there are any changes
        status_output = subprocess.check_output(["git", "status", "--porcelain"], cwd=repo_path, text=True)
        if not status_output.strip():
            logging.info("No changes to commit")
            return "No changes to commit"

        # Create a new branch
        branch_name = f"update-{int(time.time())}"
        subprocess.run(["git", "checkout", "-b", branch_name], cwd=repo_path, check=True, capture_output=True, text=True)

        # Commit changes
        subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True, text=True)
        subprocess.run(["git", "commit", "-m", "Update repository"], cwd=repo_path, check=True, capture_output=True, text=True)

        # Push changes using GitHub App authentication
        g = authenticate_github_app()
        repo = g.get_repo(extract_repo_info(repo_path))
        repo.create_git_ref(f"refs/heads/{branch_name}", repo.get_branch(source_branch).commit.sha)
        repo.update_file(
            path=".",
            message="Update repository",
            content=open(repo_path / ".", "rb").read(),
            branch=branch_name,
            sha=repo.get_contents(".").sha
        )

        # Create pull request
        pr = repo.create_pull(
            title="Update repository",
            body="Automated update",
            head=branch_name,
            base=source_branch
        )

        logging.info("Pull request created successfully")
        return pr.html_url
    except Exception as e:
        error_message = f"Unexpected error: {str(e)}"
        logging.error(error_message)
        raise HTTPException(status_code=500, detail=error_message)

@app.post("/repo")
async def apply_changes_and_create_pr(pr_request: PullRequestRequest, background_tasks: BackgroundTasks):
    clean_old_repos(background_tasks)
    repo_path = get_cached_repo(pr_request.git_url, pr_request.branch)

    files = parse_summary(pr_request.summary, repo_path)
    update_repo(files, repo_path)

    try:
        pr_url = create_pull_request(repo_path, pr_request.branch)
        return {"pull_request_url": pr_url}
    except HTTPException as e:
        return {"error": e.detail}