# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies, pipx, and GitHub CLI
RUN apt-get update && apt-get install -y \
    git \
    curl \
    gnupg \
    && rm -rf /var/lib/apt/lists/* \
    && python -m pip install --user pipx \
    && python -m pipx ensurepath \
    && curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | gpg --dearmor -o /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
    && apt-get update \
    && apt-get install -y gh \
    && rm -rf /var/lib/apt/lists/*

# Set PATH to include pipx installed binaries
ENV PATH="/root/.local/bin:${PATH}"

# Install code2prompt using pipx
RUN pipx install code2prompt

# Copy the current directory contents into the container at /app
COPY . /app

# Install Python dependencies
RUN pip install --no-cache-dir fastapi uvicorn gitpython

# Make port 8000 available to the world outside this container
EXPOSE 8000

# Run the application when the container launches
CMD ["uvicorn", "repo_controller:app", "--host", "0.0.0.0", "--port", "8000"]
