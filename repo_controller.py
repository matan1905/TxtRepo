#Import
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
    
    # Process the output to use relative paths
    output = stdout.decode()
    return process_relative_paths(output, clone_dir)

def process_relative_paths(output: str, base_path: Path) -> str:
    lines = output.split('\n')
    processed_lines = []
    for line in lines:
        if line.startswith("- ") and base_path.as_posix() in line:
            relative_path = Path(line.split(base_path.as_posix())[-1].strip()).as_posix()
            processed_lines.append(f"- {relative_path}")
        elif "## File: " in line and base_path.as_posix() in line:
            relative_path = Path(line.split(base_path.as_posix())[-1].strip()).as_posix()
            processed_lines.append(f"## File: {relative_path}")
        else:
            processed_lines.append(line)
    return '\n'.join(processed_lines)

def parse_summary(summary: str):
    file_pattern = re.compile(r"##\s+File:\s+([\w./-]+)\n\n.*?###\s+Code\n\n