import re
import logging
from pathlib import Path
from fastapi import HTTPException

def extract_repo_info(git_url: str) -> tuple:
    match = re.search(r'github\.com[:/]([^/]+)/([^/]+?)(.git)?$', git_url)
    if match:
        return match.group(1), match.group(2)
    return None, None

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

def get_safe_path(repo_path: Path, file_path: str) -> Path:
    normalized_path = os.path.normpath(file_path).lstrip('/')

    if not normalized_path.startswith(str(repo_path)):
        full_path = (repo_path / normalized_path).resolve()
    else:
        full_path = Path(normalized_path).resolve()

    repo_parents = [repo_path] + list(repo_path.parents)
    if not any(str(full_path).startswith(str(parent)) for parent in repo_parents):
        logging.warning(f"Attempted to access path outside repo: {full_path}")
        raise HTTPException(status_code=400, detail=f"Invalid file path: {file_path}")

    return full_path

def parse_summary(summary: str, repo_path: Path):
    file_pattern = re.compile(r'# File (.*?)(::.*?)?\n(.*?)# EndFile \1', re.DOTALL)
    files = []
    last_end = 0

    for match in file_pattern.finditer(summary):
        if match.start() < last_end:
            continue

        path = match.group(1).strip()
        command = match.group(2) and match.group(2).strip()
        content = match.group(3).strip()
        last_end = match.end()

        path_parts = path.split('/')
        if len(path_parts) > 2 and path_parts[0] == '':
            path = '/'.join(path_parts[3:])

        dsl_instructions = parse_dsl(command[2:] if command else "")

        files.append({'path': path, 'content': content, 'dsl': dsl_instructions})

    return files

def parse_dsl(dsl_string: str) -> DslInstruction:
    return DslInstructionFactory.create(dsl_string)