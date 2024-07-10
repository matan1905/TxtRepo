import os
import logging
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

from .routes import router

app = FastAPI()
app.include_router(router)

# Mount the static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def root():
    with open("static/index.html", "r") as f:
        content = f.read()
    return HTMLResponse(content=content)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    REPO_BASE_DIR = Path("/tmp/repos")
    REPO_BASE_DIR.mkdir(parents=True, exist_ok=True)
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)