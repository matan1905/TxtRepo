import os
import subprocess
import tempfile
import sys
import re
from pathlib import Path
from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import shutil
import time
import asyncio
from typing import Dict, Any
import logging

app = FastAPI()

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

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
    branch: str = "main"


# ... (rest of the existing code remains unchanged)

@app.get("/", response_class=HTMLResponse)
async def root():
    with open("index.html", "r") as f:
        content = f.read()
    return HTMLResponse(content=content)

# ... (rest of the existing code remains unchanged)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    REPO_BASE_DIR.mkdir(parents=True, exist_ok=True)
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)