"""
Aplikasi FastAPI utama untuk Dashboard IAK Pertambangan (Data-Level EAI).
"""
import os
from pathlib import Path
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from iak_dashboard.api.auth import authenticate_user, get_current_user, LoginRequest, LoginResponse
from iak_dashboard.api.mining import router as mining_router

app = FastAPI(
    title="IAK Mining Dashboard API",
    description="Data-Level EAI Platform untuk Integrasi Data Pertambangan Indonesia",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrasi Router
@app.post("/api/auth/login", response_model=LoginResponse, tags=["Authentication"])
def login(req: LoginRequest):
    return authenticate_user(req)

@app.get("/api/auth/me", tags=["Authentication"])
def me(user: dict = Depends(get_current_user)):
    return user

app.include_router(mining_router)

# Mount Static/Frontend files
STATIC_DIR = Path("src/iak_dashboard/static")
os.makedirs(STATIC_DIR, exist_ok=True)

@app.get("/", response_class=HTMLResponse, tags=["Web Interface"])
def index():
    html_file = STATIC_DIR / "index.html"
    if html_file.exists():
        return FileResponse(html_file)
    return HTMLResponse("<h1>IAK Mining Dashboard API is running.</h1><p>Frontend is loading...</p>")
