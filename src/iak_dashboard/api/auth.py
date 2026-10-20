"""
Autentikasi berbasis token. Sesi disimpan di SQLite agar tetap berlaku setelah server restart.
Semua endpoint data memakai dependency `get_current_user`.
"""
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta
from typing import Dict, Optional

from fastapi import Header, HTTPException
from pydantic import BaseModel

from iak_dashboard.etl.schema import get_connection

SESSION_HOURS = 8


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    username: str
    role: str

def hash_password(password: str, salt: Optional[str] = None, iterations: int = 200_000) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), iterations)
    return f"pbkdf2${iterations}${salt}${digest.hex()}"



def verify_password(password: str, stored: str) -> bool:
    try:
        _, iterations, salt, digest = stored.split("$")
    except ValueError:
        return False
    calc = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), int(iterations))
    return hmac.compare_digest(calc.hex(), digest)


def authenticate_user(req: LoginRequest) -> LoginResponse:
    conn = get_connection()
    row = conn.execute(
        "SELECT username, password_hash, role FROM auth_users WHERE username = ?", (req.username,)
    ).fetchone()
    if not row or not verify_password(req.password, row["password_hash"]):
        conn.close()
        raise HTTPException(status_code=401, detail="Nama pengguna atau kata sandi salah")

    token = secrets.token_urlsafe(32)
    expires = (datetime.now() + timedelta(hours=SESSION_HOURS)).isoformat(timespec="seconds")
    with conn:
        conn.execute("DELETE FROM auth_sessions WHERE expires_at < ?", (datetime.now().isoformat(),))
        conn.execute("INSERT INTO auth_sessions (token, username, expires_at) VALUES (?, ?, ?)",
                     (token, row["username"], expires))
    conn.close()
    return LoginResponse(token=token, username=row["username"], role=row["role"])


def _token(authorization: Optional[str]) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Perlu login")
    return authorization[len("Bearer "):].strip()


def get_current_user(authorization: Optional[str] = Header(None)) -> Dict[str, str]:
    token = _token(authorization)
    conn = get_connection()
    row = conn.execute(
        "SELECT s.username, u.role, s.expires_at FROM auth_sessions s "
        "JOIN auth_users u ON u.username = s.username WHERE s.token = ?", (token,)
    ).fetchone()
    conn.close()
    if not row or row["expires_at"] < datetime.now().isoformat():
        raise HTTPException(status_code=401, detail="Sesi berakhir, silakan masuk lagi")
    return {"username": row["username"], "role": row["role"]}


def logout(authorization: Optional[str]) -> None:
    token = _token(authorization)
    conn = get_connection()
    with conn:
        conn.execute("DELETE FROM auth_sessions WHERE token = ?", (token,))
    conn.close()
