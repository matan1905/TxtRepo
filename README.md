# TxtRepo

TxtRepo is a powerful tool that allows users to interact with GitHub repositories using a simple API. It provides functionality to retrieve an entire codebase as a single text file and convert a similarly formatted text file into a pull request.

## Features

- Get a summary of a GitHub repository's contents
- Create pull requests by providing a formatted text file with changes
- Filter files based on patterns
- Exclude files based on patterns
- Case-sensitive pattern matching
- Option to suppress comments in code files
- Add line numbers to source code blocks
- Specify branch for fetching and creating pull requests
- Automatic repository caching for improved performance
- Support for file deletion and content injection at specific lines

## How to Use

### Getting a Repository Summary

To get a summary of a repository, send a GET request to the `/repo` endpoint with the repository's Git URL and optional parameters:

```
GET /repo?git_url=https://github.com/username/repo.git&branch=main&filter_patterns=*.py,*.js&exclude_patterns=*.txt,*.md&case_sensitive=false&suppress_comments=false&line_number=false
```

Parameters:
- `git_url`: The URL of the GitHub repository (required)
- `branch`: The branch to fetch (default: "main")
- `filter_patterns`: Comma-separated filter patterns to include files (e.g., '*.py,*.js')
- `exclude_patterns`: Comma-separated patterns to exclude files (e.g., '*.txt,*.md')
- `case_sensitive`: Perform case-sensitive pattern matching (default: false)
- `suppress_comments`: Strip comments from the code files (default: false)
- `line_number`: Add line numbers to source code blocks (default: false)

The response will include a summary of the repository's contents in a formatted text file.

### Creating a Pull Request

To create a pull request, send a POST request to the `/repo` endpoint with the following JSON body:

```json
{
  "git_url": "https://github.com/username/repo.git",
  "github_token": "your_github_personal_access_token",
  "summary": "# File /path/to/file\nYour code or content here\n# EndFile /path/to/file",
  "branch": "main"
}
```

The `summary` field should contain the changes you want to make, formatted as follows:

```
# File /path/to/file
Your code or content here
# EndFile /path/to/file
```

For multiple files, repeat the format. To delete a file, use the "::delete" suffix:

```
# File /path/to/delete::delete
# EndFile /path/to/delete
```

To inject content at a specific line, use the "::injectAtLine:line-number" suffix:

```
# File /path/to/file::injectAtLine:5
Content to be injected
# EndFile /path/to/file
```

Note that when using the "injectAtLine" feature, you need to add spaces at the beginning of each line to match the indentation of the surrounding code.

The response will include the URL of the created pull request.

## Examples

### Getting a Repository Summary

Request:
```
GET /repo?git_url=https://github.com/example/repo.git&filter_patterns=*.py&suppress_comments=true
```

Response:
```json
{
  "summary": "# Code summary\n- /example/repo/main.py\n\n## Files\n\n# File /example/repo/main.py\nprint('Hello, World!')\n# EndFile /example/repo/main.py"
}
```

### Creating a Pull Request

Request:
```json
POST /repo
{
  "git_url": "https://github.com/example/repo.git",
  "github_token": "ghp_your_personal_access_token",
  "summary": "# File /example/repo/README.md\n# Updated Example Repository\n\nThis is an updated example repository.\n# EndFile /example/repo/README.md\n\n# File /example/repo/main.py::injectAtLine:2\n    print('Hello, Updated World!')\n# EndFile /example/repo/main.py",
  "branch": "feature-branch"
}
```

Response:
```json
{
  "pull_request_url": "https://github.com/example/repo/pull/1"
}
```

## Note
## API Keys and Credits

TxtRepo now uses an API key system with credits. Each API key is associated with a certain number of credits. To use the API, you need to provide a valid API key with sufficient credits.

- Retrieving a repository summary costs 1 credit
- Creating a pull request costs 2 credits

To check your credit balance, use the following endpoint:

```
GET /credits?api_key=your_api_key
```

Make sure to include your API key in all requests to the `/repo` endpoints.

## Environment Variables

The application uses the following environment variable:

- `API_KEYS`: A comma-separated list of API keys and their initial credit balance. Format: `key1:balance1,key2:balance2`

Example:
```
API_KEYS=abcdef123456:100,ghijkl789012:50
```

This sets up two API keys: "abcdef123456" with 100 credits and "ghijkl789012" with 50 credits.

Make sure to keep your GitHub personal access token secure and never share it publicly.