"""
Aplikasi FastAPI: halaman masuk, dashboard, dan API data hasil integrasi.
"""
from contextlib import closing
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, Header
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from iak_dashboard.api.auth import (
    LoginRequest,
    LoginResponse,
    authenticate_user,
    get_current_user,
    logout,
)
from iak_dashboard.api.mining import router as mining_router
from iak_dashboard.etl.schema import get_connection, init_db

app = FastAPI(title="Neraca Tambang API", version="2.0.0")

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
NO_CACHE = {"Cache-Control": "no-cache, no-store, must-revalidate"}


@app.on_event("startup")
def ensure_schema() -> None:
    init_db()


@app.post("/api/auth/login", response_model=LoginResponse, tags=["Auth"])
def login(req: LoginRequest):
    return authenticate_user(req)


@app.post("/api/auth/logout", tags=["Auth"])
def do_logout(authorization: Optional[str] = Header(None)):
    logout(authorization)
    return {"ok": True}


@app.get("/api/auth/me", tags=["Auth"])
def me(user: dict = Depends(get_current_user)):
    return user


@app.get("/api/public/sekilas", tags=["Publik"])
def sekilas():
    """Angka agregat untuk halaman masuk. Hanya ringkasan; data rinci tetap wajib login."""
    with closing(get_connection()) as conn:
        neraca = [dict(r) for r in conn.execute(
            "SELECT tahun, produksi_ton, ekspor_ton FROM fact_pasokan_batubara_nasional ORDER BY tahun")]
        izin = conn.execute("SELECT COUNT(*) FROM fact_izin_tambang").fetchone()[0]
        komoditas = conn.execute("SELECT COUNT(DISTINCT komoditas_id) FROM fact_izin_tambang").fetchone()[0]
        blok = conn.execute("SELECT COUNT(*) FROM fact_lelang_wiup").fetchone()[0]
    return {"neraca": neraca, "izin": izin, "komoditas": komoditas, "blok_lelang": blok}


app.include_router(mining_router)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", include_in_schema=False)
def login_page():
    return FileResponse(STATIC_DIR / "login.html", headers=NO_CACHE)


@app.get("/dashboard", include_in_schema=False)
def dashboard_page():
    return FileResponse(STATIC_DIR / "dashboard.html", headers=NO_CACHE)
