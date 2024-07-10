def parse_dsl(dsl_string: str) -> Dict[str, Any]:
    instructions = {}

    if dsl_string == "delete-file":
        instructions['delete_file'] = True
    elif dsl_string.startswith("delete-lines-inclusive:"):
        start, end = map(int, dsl_string.split(':')[1].split('-'))
        instructions['delete_lines'] = {'start': start, 'end': end}
    elif dsl_string.startswith("injectAtLine:"):
        _, line_number = dsl_string.split(':')
        instructions['inject_at_line'] = int(line_number)

    return instructions

def update_repo(files: list, repo_path: Path):
    for file in files:
        path = file['path']
        content = file['content']
        dsl = file['dsl']

        try:
            file_path = get_safe_path(repo_path, path)
            logging.info(f"Processing file: {file_path}")

            if dsl.get('delete_file', False):
                if file_path.exists():
                    file_path.unlink()
                    logging.info(f"Deleted file: {file_path}")
                else:
                    logging.warning(f"Attempted to delete non-existent file: {file_path}")
            elif 'delete_lines' in dsl:
                start, end = dsl['delete_lines']['start'], dsl['delete_lines']['end']
                with open(file_path, 'r') as f:
                    lines = f.readlines()
                del lines[start-1:end]
                with open(file_path, 'w') as f:
                    f.writelines(lines)
                logging.info(f"Deleted lines {start} to {end} in file: {file_path}")
            elif 'inject_at_line' in dsl:
                line_number = dsl['inject_at_line']
                with open(file_path, 'r') as f:
                    lines = f.readlines()
                lines.insert(line_number - 1, content + '\n')
                with open(file_path, 'w') as f:
                    f.writelines(lines)
                logging.info(f"Injected content at line {line_number} in file: {file_path}")
            else:
                file_path.parent.mkdir(parents=True, exist_ok=True)
                with open(file_path, 'w') as f:
                    f.write(content.strip())
                logging.info(f"Updated file: {file_path}")
        except Exception as e:
            logging.error(f"Error processing file {path}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error processing file {path}: {str(e)}")