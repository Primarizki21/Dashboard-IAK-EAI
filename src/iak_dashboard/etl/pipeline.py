"""
Pipeline integrasi Data-Level EAI untuk sektor pertambangan Indonesia.
Menjalankan ekstraksi multi-format (CSV, XLSX, JSON, PDF), transformasi,
loading ke SQLite database terpadu, dan pencatatan audit log.
"""
import hashlib
import sqlite3
from pathlib import Path
from typing import Dict, Any
import pandas as pd

from iak_dashboard.etl.schema import DB_PATH, init_db, get_connection
from iak_dashboard.etl.extractors import (
    extract_coal_exports,
    extract_kaltim_operations,
    extract_wiup_auctions,
    extract_heesi_pdf,
    extract_modi_licenses,
)

RAW_DIR = Path("data/raw")

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def log_audit(
    conn: sqlite3.Connection,
    source_name: str,
    source_format: str,
    target_table: str,
    extracted: int,
    loaded: int,
    status: str = "SUCCESS",
) -> None:
    conn.execute(
        """
        INSERT INTO etl_audit_log 
        (source_name, source_format, target_table, records_extracted, records_loaded, status)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (source_name, source_format, target_table, extracted, loaded, status),
    )

def seed_auth_user(conn: sqlite3.Connection) -> None:
    default_users = [
        ("admin", hash_password("admin123"), "admin"),
        ("analyst", hash_password("analyst123"), "analyst"),
    ]
    for username, pwd_hash, role in default_users:
        conn.execute(
            """
            INSERT OR IGNORE INTO auth_users (username, password_hash, role)
            VALUES (?, ?, ?)
            """,
            (username, pwd_hash, role),
        )

def run_pipeline() -> Dict[str, Any]:
    """
    Eksekusi pipeline Data-Level EAI lengkap.
    """
    init_db()
    conn = get_connection()
    summary: Dict[str, int] = {}

    print("=== MEMULAI PIPELINE DATA-LEVEL EAI PERTAMBANGAN ===")

    # 1. BPS Coal Exports (CSV)
    f_export = RAW_DIR / "export_coal_by_country.csv"
    print(f"[*] Mengekstrak Dataset 1 (CSV): {f_export.name}...")
    df_export = extract_coal_exports(f_export)
    extracted_exp = len(df_export)
    # Clear & Insert
    conn.execute("DELETE FROM fact_ekspor_batubara;")
    df_export.to_sql("fact_ekspor_batubara", conn, if_exists="append", index=False)
    log_audit(conn, "BPS Ekspor Batubara", "CSV", "fact_ekspor_batubara", extracted_exp, extracted_exp)
    summary["fact_ekspor_batubara"] = extracted_exp

    # 2. Kaltim Operations (XLSX)
    f_kaltim = RAW_DIR / "kaltim_mining_operations.xlsx"
    print(f"[*] Mengekstrak Dataset 2 (XLSX): {f_kaltim.name}...")
    df_kaltim = extract_kaltim_operations(f_kaltim)
    extracted_kaltim = len(df_kaltim)
    conn.execute("DELETE FROM fact_operasional_kaltim;")
    df_kaltim.to_sql("fact_operasional_kaltim", conn, if_exists="append", index=False)
    log_audit(conn, "ESDM Kaltim Operasional", "XLSX", "fact_operasional_kaltim", extracted_kaltim, extracted_kaltim)
    summary["fact_operasional_kaltim"] = extracted_kaltim

    # 3. WIUP Auctions (JSON)
    f_wiup = RAW_DIR / "wiup_auctions.json"
    print(f"[*] Mengekstrak Dataset 3 (JSON): {f_wiup.name}...")
    df_wiup = extract_wiup_auctions(f_wiup)
    extracted_wiup = len(df_wiup)
    conn.execute("DELETE FROM fact_lelang_wiup;")
    df_wiup.to_sql("fact_lelang_wiup", conn, if_exists="append", index=False)
    log_audit(conn, "Ditjen Minerba Lelang WIUP", "JSON", "fact_lelang_wiup", extracted_wiup, extracted_wiup)
    summary["fact_lelang_wiup"] = extracted_wiup

    # 4. ESDM HEESI Statistics (PDF)
    f_heesi = RAW_DIR / "esdm_heesi_statistics.pdf"
    print(f"[*] Mengekstrak Dataset 4 (PDF): {f_heesi.name}...")
    df_supply, df_reserves = extract_heesi_pdf(f_heesi)
    extracted_supply = len(df_supply)
    extracted_reserves = len(df_reserves)

    conn.execute("DELETE FROM fact_pasokan_batubara_nasional;")
    df_supply.to_sql("fact_pasokan_batubara_nasional", conn, if_exists="append", index=False)
    log_audit(conn, "ESDM HEESI Pasokan Batubara", "PDF", "fact_pasokan_batubara_nasional", extracted_supply, extracted_supply)
    summary["fact_pasokan_batubara_nasional"] = extracted_supply

    conn.execute("DELETE FROM fact_cadangan_batubara_provinsi;")
    df_reserves.to_sql("fact_cadangan_batubara_provinsi", conn, if_exists="append", index=False)
    log_audit(conn, "ESDM HEESI Cadangan Batubara", "PDF", "fact_cadangan_batubara_provinsi", extracted_reserves, extracted_reserves)
    summary["fact_cadangan_batubara_provinsi"] = extracted_reserves

    # 5. MoDI Mining Licenses (CSV)
    f_modi = RAW_DIR / "modi_mining_licenses.csv"
    print(f"[*] Mengekstrak Dataset 5 (CSV): {f_modi.name}...")
    df_modi = extract_modi_licenses(f_modi)
    extracted_modi = len(df_modi)
    conn.execute("DELETE FROM fact_izin_tambang;")
    df_modi.to_sql("fact_izin_tambang", conn, if_exists="append", index=False)
    log_audit(conn, "MoDI ESDM Izin Tambang", "CSV", "fact_izin_tambang", extracted_modi, extracted_modi)
    summary["fact_izin_tambang"] = extracted_modi

    # 6. Populate Dimensions (Provinsi & Komoditas)
    print("[*] Harmonisasi Dimensi Data (Provinsi & Komoditas)...")
    provinces = set()
    for prov in df_wiup["nama_provinsi"].dropna().unique():
        if prov:
            provinces.add(prov.upper().strip())
    for prov in df_modi["nama_provinsi"].dropna().unique():
        if prov and prov != "-":
            provinces.add(prov.upper().strip())

    conn.execute("DELETE FROM dim_provinsi;")
    for p in sorted(provinces):
        conn.execute("INSERT OR IGNORE INTO dim_provinsi (nama_provinsi) VALUES (?)", (p,))
    summary["dim_provinsi"] = len(provinces)

    commodities = set()
    for c in df_wiup["komoditas"].dropna().unique():
        if c:
            commodities.add(c.upper().strip())
    for c in df_modi["komoditas"].dropna().unique():
        if c and c != "-":
            commodities.add(c.upper().strip())

    conn.execute("DELETE FROM dim_komoditas;")
    for c in sorted(commodities):
        conn.execute("INSERT OR IGNORE INTO dim_komoditas (nama_komoditas) VALUES (?)", (c,))
    summary["dim_komoditas"] = len(commodities)

    # 7. Seed Auth
    seed_auth_user(conn)

    conn.commit()
    conn.close()

    print("=== PIPELINE DATA-LEVEL EAI SELESAI DENGAN SUKSES ===")
    return summary

if __name__ == "__main__":
    res = run_pipeline()
    print("Ringkasan Data Dimuat:")
    for k, v in res.items():
        print(f"  - {k}: {v:,} baris")
