# main.py
import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware

# Import routers from your new files
from auth import router as auth_router
from users.endpoints import router as users_router
from documents.endpoints import router as documents_router

# --- FastAPI App Initialization ---
app = FastAPI(title="Document Management System API (mysql.connector Version)")

# --- CORS Middleware ---
# Get allowed origins from environment variable, default to localhost
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"], # Or specify ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    allow_headers=["*"], # Or specify specific headers like ["Authorization", "Content-Type"]
)

# --- Include Routers ---
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(documents_router)

# --- Static Files ---
# Ensure the 'static' directory exists
STATIC_DIR = "static"
if not os.path.isdir(STATIC_DIR):
     print(f"Warning: Static directory '{STATIC_DIR}' not found. Skipping static file serving.")
else:
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# --- Root and Dashboard HTML Routes ---
@app.get("/", response_class=HTMLResponse)
async def root():
    index_html_path = os.path.join(STATIC_DIR, "index.html")
    if not os.path.exists(index_html_path):
         raise HTTPException(status_code=404, detail="index.html not found in static directory.")
    with open(index_html_path, "r") as f:
        html_content = f.read()
    return html_content

@app.get("/dashboard.html", response_class=HTMLResponse)
async def dashboard():
    dashboard_html_path = os.path.join(STATIC_DIR, "dashboard.html")
    if not os.path.exists(dashboard_html_path):
        raise HTTPException(status_code=404, detail="dashboard.html not found in static directory.")
    with open(dashboard_html_path, "r") as f:
        dashboard_content = f.read()
    return dashboard_content

# Any other general app-level configurations or events go here
# For example:
# @app.on_event("startup"):
# async def startup_event():
#     print("App starting up...")

# @app.on_event("shutdown"):
# async def shutdown_event():
#     print("App shutting down...")