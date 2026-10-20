"""
Skema basis data terpadu (unified_mining.db) untuk integrasi data pertambangan.

Tabel dimensi dan fakta dibangun ulang setiap kali pipeline dijalankan.
Tabel audit, kualitas data, pengguna, dan sesi bersifat permanen (riwayat tidak dihapus).
"""
import os
import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DB_PATH = PROJECT_ROOT / "data" / "processed" / "unified_mining.db"

REBUILD_TABLES = [
    "fact_ekspor_batubara", "fact_operasional_kaltim", "fact_lelang_wiup",
    "fact_pasokan_batubara_nasional", "fact_cadangan_batubara_provinsi", "fact_izin_tambang",
    "dim_provinsi", "dim_komoditas",
]

DDL_ANALYTIC = """
CREATE TABLE dim_provinsi (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nama_provinsi TEXT UNIQUE NOT NULL,
    pulau TEXT NOT NULL
);

CREATE TABLE dim_komoditas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nama_komoditas TEXT UNIQUE NOT NULL,
    kategori TEXT NOT NULL
);

-- BPS (CSV): ekspor batubara per negara tujuan. NULL = data tidak tersedia ("─" di sumber).
CREATE TABLE fact_ekspor_batubara (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    negara_tujuan TEXT NOT NULL,
    tahun INTEGER NOT NULL,
    volume_ribu_ton REAL,
    nilai_fob_juta_usd REAL,
    source_format TEXT DEFAULT 'CSV',
    UNIQUE(negara_tujuan, tahun)
);

-- ESDM Kaltim (XLSX): indikator operasional. status_periode 'berjalan' = tahun belum selesai.
CREATE TABLE fact_operasional_kaltim (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provinsi_id INTEGER REFERENCES dim_provinsi(id),
    indikator TEXT NOT NULL,
    tahun INTEGER NOT NULL,
    nilai REAL NOT NULL,
    satuan TEXT NOT NULL,
    status_periode TEXT NOT NULL DEFAULT 'final',
    source_format TEXT DEFAULT 'XLSX',
    UNIQUE(indikator, tahun)
);

-- Ditjen Minerba (JSON): blok lelang WIUP
CREATE TABLE fact_lelang_wiup (
    id_lelang TEXT PRIMARY KEY,
    nomor TEXT,
    nama_blok TEXT NOT NULL,
    provinsi_id INTEGER REFERENCES dim_provinsi(id),
    komoditas_id INTEGER REFERENCES dim_komoditas(id),
    nama_provinsi TEXT,
    nama_kabupaten TEXT,
    komoditas TEXT,
    komoditas_sumber TEXT,
    jenis_izin TEXT,
    kdi_rupiah REAL,
    luas_ha REAL,
    tahapan TEXT,
    latitude REAL,
    longitude REAL,
    jumlah_peserta INTEGER,
    source_format TEXT DEFAULT 'JSON'
);

-- HEESI 2024 (PDF) Tabel 6.1.2: neraca batubara nasional (ton)
CREATE TABLE fact_pasokan_batubara_nasional (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tahun INTEGER UNIQUE NOT NULL,
    produksi_ton REAL NOT NULL,
    ekspor_ton REAL NOT NULL,
    impor_ton REAL NOT NULL,
    konsumsi_domestik_ton REAL NOT NULL,
    source_format TEXT DEFAULT 'PDF'
);

-- HEESI 2024 (PDF) Tabel 6.1.1: cadangan & sumber daya batubara per provinsi (juta ton)
CREATE TABLE fact_cadangan_batubara_provinsi (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provinsi_id INTEGER UNIQUE NOT NULL REFERENCES dim_provinsi(id),
    provinsi_sumber TEXT NOT NULL,
    sumberdaya_juta_ton REAL NOT NULL,
    cadangan_juta_ton REAL NOT NULL,
    source_format TEXT DEFAULT 'PDF'
);

-- MoDI ESDM (CSV): izin usaha pertambangan
CREATE TABLE fact_izin_tambang (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provinsi_id INTEGER REFERENCES dim_provinsi(id),
    komoditas_id INTEGER REFERENCES dim_komoditas(id),
    nama_perusahaan TEXT NOT NULL,
    badan_usaha TEXT,
    jenis_izin TEXT,
    sk_iup TEXT,
    nama_provinsi TEXT,
    provinsi_sumber TEXT,
    nama_kabupaten TEXT,
    kegiatan TEXT,
    luas_sk_ha REAL,
    cnc TEXT,
    komoditas TEXT,
    komoditas_sumber TEXT,
    source_format TEXT DEFAULT 'CSV'
);

CREATE INDEX idx_izin_prov ON fact_izin_tambang(provinsi_id);
CREATE INDEX idx_izin_kom ON fact_izin_tambang(komoditas_id);
"""

DDL_PERSISTENT = """
CREATE TABLE IF NOT EXISTS etl_run (
    run_id TEXT PRIMARY KEY,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    status TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS etl_audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL REFERENCES etl_run(run_id),
    source_name TEXT NOT NULL,
    source_file TEXT NOT NULL,
    source_format TEXT NOT NULL,
    target_table TEXT NOT NULL,
    records_extracted INTEGER NOT NULL,
    records_loaded INTEGER NOT NULL,
    records_rejected INTEGER NOT NULL,
    status TEXT NOT NULL,
    message TEXT,
    duration_ms INTEGER NOT NULL,
    executed_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS etl_quality_check (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL REFERENCES etl_run(run_id),
    target_table TEXT NOT NULL,
    rule TEXT NOT NULL,
    result TEXT NOT NULL,
    affected_rows INTEGER NOT NULL DEFAULT 0,
    detail TEXT
);

CREATE TABLE IF NOT EXISTS auth_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'admin',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS auth_sessions (
    token TEXT PRIMARY KEY,
    username TEXT NOT NULL,
    expires_at TEXT NOT NULL
);
"""


def get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    os.makedirs(db_path.parent, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def _drop_outdated_persistent(conn: sqlite3.Connection) -> None:
    """Basis data dari versi lama punya etl_audit_log tanpa run_id; tabel itu dibuat ulang."""
    cols = [r[1] for r in conn.execute("PRAGMA table_info(etl_audit_log)")]
    if cols and "run_id" not in cols:
        conn.execute("DROP TABLE etl_audit_log")
    user_cols = [r[1] for r in conn.execute("PRAGMA table_info(auth_users)")]
    if user_cols:
        row = conn.execute("SELECT password_hash FROM auth_users LIMIT 1").fetchone()
        if row and not str(row[0]).startswith("pbkdf2$"):
            conn.execute("DELETE FROM auth_users")


def init_db(db_path: Path = DB_PATH) -> None:
    """Buat tabel permanen bila belum ada (dipakai juga oleh server saat start)."""
    conn = get_connection(db_path)
    with conn:
        _drop_outdated_persistent(conn)
        conn.executescript(DDL_PERSISTENT)
    conn.close()


def rebuild_analytic_tables(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA foreign_keys = OFF;")
    for t in REBUILD_TABLES:
        conn.execute(f"DROP TABLE IF EXISTS {t}")
    conn.executescript(DDL_ANALYTIC)
    conn.execute("PRAGMA foreign_keys = ON;")


if __name__ == "__main__":
    init_db()
    print(f"Skema permanen siap di {DB_PATH}")
