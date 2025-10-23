from fastapi import FastAPI, Request, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from datetime import datetime
import os
import subprocess
import sqlite3
import pickle
import base64
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = FastAPI()

# Hardcoded secrets (vulnerability)
SECRET_KEY = "hardcoded-secret-key-123"
API_TOKEN = "sk-1234567890abcdef"

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

@app.get("/exec/{command}")
async def execute_command(command: str):
    """Vulnerable endpoint - command injection"""
    try:
        # CWE-78: OS Command Injection vulnerability
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return {"output": result.stdout, "error": result.stderr}
    except Exception as e:
        # CWE-209: Information exposure through error messages
        return {"error": str(e), "locals": str(locals())}

@app.get("/file/{filename}")
async def read_file(filename: str):
    """Vulnerable endpoint - path traversal"""
    try:
        # CWE-22: Path Traversal vulnerability
        file_path = f"./files/{filename}"
        with open(file_path, 'r') as f:
            content = f.read()
        return {"filename": filename, "content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/deserialize")
async def deserialize_data(data: str):
    """Vulnerable endpoint - insecure deserialization"""
    try:
        # CWE-502: Deserialization of untrusted data
        decoded_data = base64.b64decode(data)
        obj = pickle.loads(decoded_data)
        return {"result": str(obj)}
    except Exception as e:
        return {"error": str(e)}

@app.get("/sql/{user_id}")
async def get_user(user_id: str):
    """Vulnerable endpoint - SQL injection"""
    try:
        # CWE-89: SQL Injection vulnerability
        conn = sqlite3.connect(':memory:')
        cursor = conn.cursor()
        
        # Create a test table
        cursor.execute("CREATE TABLE users (id TEXT, name TEXT)")
        cursor.execute("INSERT INTO users VALUES ('1', 'admin')")
        cursor.execute("INSERT INTO users VALUES ('2', 'user')")
        
        # Vulnerable query
        query = f"SELECT * FROM users WHERE id = '{user_id}'"
        cursor.execute(query)
        result = cursor.fetchall()
        
        conn.close()
        return {"users": result}
    except Exception as e:
        return {"error": str(e)}

@app.get("/debug")
async def debug_info():
    """Vulnerable endpoint - debug information exposure"""
    # CWE-209: Information exposure
    import sys
    return {
        "python_version": sys.version,
        "environment": dict(os.environ),
        "secret_key": SECRET_KEY,
        "api_token": API_TOKEN,
        "current_directory": os.getcwd(),
        "system_info": os.uname() if hasattr(os, 'uname') else "Windows"
    }

if __name__ == "__main__":
    import uvicorn
    # Insecure configuration
    uvicorn.run("main:app", host="0.0.0.0", port=80, reload=True, debug=True)
