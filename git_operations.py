import subprocess
import logging
from pathlib import Path
from fastapi import HTTPException

def clone_repo(git_url: str, clone_dir: Path):
    try:
        subprocess.run(["git", "clone", git_url, str(clone_dir)], check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=400, detail=f"Error cloning repository: {e.stderr}")

def create_pull_request(repo_path: Path, github_token: str, source_branch: str):
    try:
        subprocess.run(["git", "config", "user.name", "GitHub Actions"], cwd=repo_path, check=True, capture_output=True, text=True)
        subprocess.run(["git", "config", "user.email", "actions@github.com"], cwd=repo_path, check=True, capture_output=True, text=True)

        status_output = subprocess.check_output(["git", "status", "--porcelain"], cwd=repo_path, text=True)
        if not status_output.strip():
            logging.info("No changes to commit")
            return "No changes to commit"

        branch_name = f"update-{int(time.time())}"
        subprocess.run(["git", "checkout", "-b", branch_name], cwd=repo_path, check=True, capture_output=True, text=True)

        subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True, text=True)
        subprocess.run(["git", "commit", "-m", "Update repository"], cwd=repo_path, check=True, capture_output=True, text=True)

        remote_url = subprocess.check_output(["git", "remote", "get-url", "origin"], cwd=repo_path, text=True).strip()
        auth_remote = re.sub(r"https://", f"https://x-access-token:{github_token}@", remote_url)

        logging.info(f"Pushing changes to branch: {branch_name}")
        push_result = subprocess.run(["git", "push", "-u", auth_remote, branch_name], cwd=repo_path, capture_output=True, text=True)
        if push_result.returncode != 0:
            raise subprocess.CalledProcessError(push_result.returncode, push_result.args, push_result.stdout, push_result.stderr)

        logging.info("Authenticating with GitHub CLI")
        auth_result = subprocess.run(["gh", "auth", "login", "--with-token"], input=github_token, text=True, capture_output=True)
        if auth_result.returncode != 0:
            raise subprocess.CalledProcessError(auth_result.returncode, auth_result.args, auth_result.stdout, auth_result.stderr)

        logging.info("Creating pull request")
        pr_result = subprocess.run(
            ["gh", "pr", "create", "--title", "Update repository", "--body", "Automated update", "--head", branch_name, "--base", source_branch],
            cwd=repo_path, capture_output=True, text=True)
        if pr_result.returncode != 0:
            raise subprocess.CalledProcessError(pr_result.returncode, pr_result.args, pr_result.stdout, pr_result.stderr)

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