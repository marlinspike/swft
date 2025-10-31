from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

@app.get("/")
async def root(request: Request):
    background_color = os.getenv("BACKGROUND_COLOR", "white")
    custom_message = os.getenv("CUSTOM_MESSAGE", "SWFT Demo")
    container_id = os.getenv("HOSTNAME", "local")
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "background_color": background_color,
            "custom_message": custom_message,
            "container_id": container_id
        }
    )

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/time")
async def get_time():
    return {"time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=80, reload=True)
