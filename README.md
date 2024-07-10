This file was generated using TxtRepo + n8n workflow that listened to issues!

# TxtRepo

TxtRepo is a tool that allows users to interact with GitHub repositories using a simple API. It provides functionality to retrieve an entire codebase as a single text file and convert a similarly formatted text file into a pull request.

## Features

- Get a summary of a GitHub repository's contents
- Create pull requests by providing a formatted text file with changes

## How to Use

### Getting a Repository Summary

To get a summary of a repository, send a GET request to the `/repo` endpoint with the repository's Git URL:

```
GET /repo?git_url=https://github.com/username/repo.git
```

The response will include a summary of the repository's contents in a formatted text file.

### Creating a Pull Request

To create a pull request, send a POST request to the `/repo` endpoint with the following JSON body:

```json
{
  "git_url": "https://github.com/username/repo.git",
  "github_token": "your_github_personal_access_token",
  "summary": "# File /path/to/file\nYour code or content here\n# EndFile /path/to/file"
}
```

The `summary` field should contain the changes you want to make, formatted as follows:

```
# File /path/to/file
Your code or content here
# EndFile /path/to/file
```

For multiple files, repeat the format. To delete a file, use the "DELETED:" prefix:

```
# File DELETED:/path/to/delete
# EndFile DELETED:/path/to/delete
```

The response will include the URL of the created pull request.

## Examples

### Getting a Repository Summary

Request:
```
GET /repo?git_url=https://github.com/example/repo.git
```

Response:
```json
{
  "summary": "# Code summary\n- /example/repo/README.md\n- /example/repo/main.py\n\n## Files\n\n# File /example/repo/README.md\n# Example Repository\n\nThis is an example repository.\n# EndFile /example/repo/README.md\n\n# File /example/repo/main.py\nprint('Hello, World!')\n# EndFile /example/repo/main.py"
}
```

### Creating a Pull Request

Request:
```json
POST /repo
{
  "git_url": "https://github.com/example/repo.git",
  "github_token": "ghp_your_personal_access_token",
  "summary": "# File /example/repo/README.md\n# Updated Example Repository\n\nThis is an updated example repository.\n# EndFile /example/repo/README.md\n\n# File /example/repo/main.py\nprint('Hello, Updated World!')\n# EndFile /example/repo/main.py"
}
```

Response:
```json
{
  "pull_request_url": "https://github.com/example/repo/pull/1"
}
```

## Note

Make sure to keep your GitHub personal access token secure and never share it publicly.
