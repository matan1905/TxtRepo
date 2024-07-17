from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional
from .repo_controller import (
    get_repo_summary,
    apply_changes_and_create_pr,
    PullRequestRequest,
    clean_old_repos
)

app = FastAPI()

@app.get("/", response_class=HTMLResponse)
async def root():
    with open("static/index.html", "r") as f:
        content = f.read()
    return HTMLResponse(content=content)

@app.get("/repo")
async def get_repo_summary_route(
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
    return await get_repo_summary(
        background_tasks,
        git_url,
        branch,
        filter_patterns,
        exclude_patterns,
        case_sensitive,
        suppress_comments,
        line_number
    )

@app.post("/repo")
async def apply_changes_and_create_pr_route(pr_request: PullRequestRequest, background_tasks: BackgroundTasks):
    return await apply_changes_and_create_pr(pr_request, background_tasks)