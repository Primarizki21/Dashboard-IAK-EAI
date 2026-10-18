"""
Otentikasi sederhana berbasis token untuk Dashboard IAK (Memenuhi requirement Login).
"""
import hashlib
import secrets
from typing import Dict, Optional
from fastapi import HTTPException, Header
from pydantic import BaseModel
from iak_dashboard.etl.schema import get_connection

# In-memory session store: token -> user dict
ACTIVE_SESSIONS: Dict[str, Dict[str, str]] = {}

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    token: str
    username: str
    role: str
    message: str

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def authenticate_user(req: LoginRequest) -> LoginResponse:
    conn = get_connection()
    cursor = conn.cursor()
    pwd_hash = hash_password(req.password)
    row = cursor.execute(
        "SELECT id, username, role FROM auth_users WHERE username = ? AND password_hash = ?",
        (req.username, pwd_hash),
    ).fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=401, detail="Username atau password salah")

    token = secrets.token_hex(24)
    user_info = {"username": row["username"], "role": row["role"]}
    ACTIVE_SESSIONS[token] = user_info

    return LoginResponse(
        token=token,
        username=row["username"],
        role=row["role"],
        message="Login berhasil",
    )

def get_current_user(authorization: Optional[str] = Header(None)) -> Dict[str, str]:
    if not authorization:
        raise HTTPException(status_code=401, detail="Header Authorization diperlukan")
    
    token = authorization.replace("Bearer ", "").strip()
    if token not in ACTIVE_SESSIONS:
        raise HTTPException(status_code=401, detail="Sesi telah kedaluwarsa atau token tidak valid")
    
    return ACTIVE_SESSIONS[token]
