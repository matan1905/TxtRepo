from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
from repo_controller import get_cached_repo, run_code2prompt, parse_summary, update_repo, create_pull_request, clean_old_repos

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

class RepoRequest(BaseModel):
    git_url: str

class PullRequestRequest(BaseModel):
    git_url: str
    github_token: str
    summary: str
    branch: str = "main"

@app.get("/", response_class=HTMLResponse)
async def root():
    with open("static/index.html", "r") as f:
        content = f.read()
    return HTMLResponse(content=content)

@app.get("/repo")
async def get_repo_summary(
    repo_request: RepoRequest,
    background_tasks: BackgroundTasks,
    branch: str = Query("main", description="Branch to fetch"),
    filter_patterns: Optional[str] = Query(None, description="Comma-separated filter patterns to include files (e.g., '*.py,*.js')"),
    exclude_patterns: Optional[str] = Query(None, description="Comma-separated patterns to exclude files (e.g., '*.txt,*.md')"),
    case_sensitive: bool = Query(False, description="Perform case-sensitive pattern matching"),
    suppress_comments: bool = Query(False, description="Strip comments from the code files"),
    line_number: bool = Query(False, description="Add line numbers to source code blocks")
):
    clean_old_repos(background_tasks)
    repo_path = get_cached_repo(repo_request.git_url, branch)
    summary = await run_code2prompt(
        repo_path,
        repo_request.git_url,
        filter_patterns,
        exclude_patterns,
        case_sensitive,
        suppress_comments,
        line_number
    )
    return {"summary": summary}

@app.post("/repo")
async def apply_changes_and_create_pr(pr_request: PullRequestRequest, background_tasks: BackgroundTasks):
    clean_old_repos(background_tasks)
    repo_path = get_cached_repo(pr_request.git_url, pr_request.branch)

    files = parse_summary(pr_request.summary, repo_path)
    update_repo(files, repo_path)

    try:
        pr_url = create_pull_request(repo_path, pr_request.github_token, pr_request.branch)
        return {"pull_request_url": pr_url}
    except HTTPException as e:
        return {"error": e.detail}