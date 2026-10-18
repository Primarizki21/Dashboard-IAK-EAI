"""
Database schema definition and connection utility for Unified Mining Data Warehouse (Data-Level EAI).
"""
import sqlite3
import os
from pathlib import Path

DB_PATH = Path("data/processed/unified_mining.db")

DDL_STATEMENTS = """
-- Dimension: Wilayah / Provinsi
CREATE TABLE IF NOT EXISTS dim_provinsi (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nama_provinsi TEXT UNIQUE NOT NULL,
    pulau TEXT
);

-- Dimension: Komoditas Tambang
CREATE TABLE IF NOT EXISTS dim_komoditas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nama_komoditas TEXT UNIQUE NOT NULL,
    kategori TEXT
);

-- Fact: Ekspor Batubara menurut Negara Tujuan (BPS - CSV)
CREATE TABLE IF NOT EXISTS fact_ekspor_batubara (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    negara_tujuan TEXT NOT NULL,
    tahun INTEGER NOT NULL,
    volume_ribu_ton REAL NOT NULL,
    nilai_fob_juta_usd REAL NOT NULL,
    source_format TEXT DEFAULT 'CSV',
    UNIQUE(negara_tujuan, tahun)
);

-- Fact: Indikator Operasional Tambang Kaltim (ESDM Kaltim - XLSX)
CREATE TABLE IF NOT EXISTS fact_operasional_kaltim (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    indikator TEXT NOT NULL,
    tahun INTEGER NOT NULL,
    nilai REAL NOT NULL,
    satuan TEXT NOT NULL,
    source_format TEXT DEFAULT 'XLSX',
    UNIQUE(indikator, tahun)
);

-- Fact: Lelang WIUP Indonesia (ESDM Minerba - JSON)
CREATE TABLE IF NOT EXISTS fact_lelang_wiup (
    id_lelang TEXT PRIMARY KEY,
    nomor TEXT,
    nama_blok TEXT NOT NULL,
    nama_provinsi TEXT,
    nama_kabupaten TEXT,
    pulau TEXT,
    komoditas TEXT,
    jenis_izin TEXT,
    kegiatan TEXT,
    kdi_rupiah REAL DEFAULT 0,
    luas_ha REAL DEFAULT 0,
    tahapan TEXT,
    latitude REAL,
    longitude REAL,
    jumlah_peserta INTEGER DEFAULT 0,
    source_format TEXT DEFAULT 'JSON'
);

-- Fact: Pasokan Batubara Nasional (HEESI ESDM - PDF Table 6.1.2)
CREATE TABLE IF NOT EXISTS fact_pasokan_batubara_nasional (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tahun INTEGER UNIQUE NOT NULL,
    produksi_ton REAL NOT NULL,
    ekspor_ton REAL NOT NULL,
    impor_ton REAL NOT NULL,
    konsumsi_domestik_ton REAL NOT NULL,
    source_format TEXT DEFAULT 'PDF'
);

-- Fact: Cadangan & Sumber Daya Batubara per Provinsi (HEESI ESDM - PDF Table 6.1.1)
CREATE TABLE IF NOT EXISTS fact_cadangan_batubara_provinsi (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provinsi TEXT UNIQUE NOT NULL,
    sumberdaya_juta_ton REAL NOT NULL,
    cadangan_juta_ton REAL NOT NULL,
    source_format TEXT DEFAULT 'PDF'
);

-- Fact: Izin Usaha Pertambangan Multi-Komoditas (MoDI ESDM - CSV)
CREATE TABLE IF NOT EXISTS fact_izin_tambang (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nama_perusahaan TEXT NOT NULL,
    badan_usaha TEXT,
    jenis_izin TEXT,
    sk_iup TEXT,
    nama_provinsi TEXT,
    nama_kabupaten TEXT,
    kegiatan TEXT,
    luas_sk_ha REAL DEFAULT 0,
    cnc TEXT,
    komoditas TEXT,
    source_format TEXT DEFAULT 'CSV'
);

-- Audit Trail: Log Pelaksanaan ETL (Data-Level EAI Tracking)
CREATE TABLE IF NOT EXISTS etl_audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_name TEXT NOT NULL,
    source_format TEXT NOT NULL,
    target_table TEXT NOT NULL,
    records_extracted INTEGER NOT NULL,
    records_loaded INTEGER NOT NULL,
    status TEXT NOT NULL,
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User Credentials for Dashboard Authentication
CREATE TABLE IF NOT EXISTS auth_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'analyst',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

def get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    os.makedirs(db_path.parent, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db(db_path: Path = DB_PATH) -> None:
    conn = get_connection(db_path)
    with conn:
        conn.executescript(DDL_STATEMENTS)
    conn.close()

if __name__ == "__main__":
    init_db()
    print(f"Database schema initialized at {DB_PATH}")
