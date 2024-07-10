from pydantic import BaseModel

class RepoRequest(BaseModel):
    git_url: str

class PullRequestRequest(BaseModel):
    git_url: str
    github_token: str
    summary: str
    branch: str = "main"