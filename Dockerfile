# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Install pipx
RUN python -m pip install --user pipx
RUN python -m pipx ensurepath
ENV PATH="/root/.local/bin:${PATH}"

# Install code2prompt using pipx
RUN pipx install code2prompt

# Install GitHub CLI
RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | gpg --dearmor -o /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
    && apt-get update \
    && apt-get install -y gh \
    && rm -rf /var/lib/apt/lists/*

# Copy the current directory contents into the container at /app
COPY static /app/static
COPY . /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create a directory for repositories and set permissions
RUN mkdir -p /tmp/repos && chmod 777 /tmp/repos

# Make port 8000 available to the world outside this container
EXPOSE 8000

# Run the application when the container launches
CMD ["python", "main.py"]
