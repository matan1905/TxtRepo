@injectAtLine:7
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

@injectAtLine:15
# Mount the static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# Serve index.html as the root route
@app.get("/")
async def read_index():
    return FileResponse("static/index.html")