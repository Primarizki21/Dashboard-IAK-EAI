"""
Pipeline ETL integrasi data pertambangan (Data-Level EAI).

Urutan: bangun ulang tabel analitik -> isi dimensi baku -> per sumber: extract, harmonisasi,
validasi, load -> catat hasil di etl_audit_log dan etl_quality_check.
Satu sumber yang gagal tidak menghentikan sumber lain; statusnya dicatat FAILED.
"""
import hashlib
import secrets
import sqlite3
import time
import uuid
from datetime import datetime
from typing import Callable, Dict, List, Optional

import pandas as pd

from iak_dashboard.etl.extractors import (
    extract_coal_exports,
    extract_heesi_pdf,
    extract_kaltim_operations,
    extract_modi_licenses,
    extract_wiup_auctions,
)
from iak_dashboard.etl.harmonize import (
    KOMODITAS,
    PROVINSI,
    normalize_komoditas,
    normalize_provinsi,
)
from iak_dashboard.api.auth import hash_password
from iak_dashboard.etl.schema import PROJECT_ROOT, get_connection, init_db, rebuild_analytic_tables, seed_auth_user

RAW_DIR = PROJECT_ROOT / "data" / "raw"

# Batas wilayah Indonesia untuk validasi koordinat WIUP
LAT_RANGE = (-11.5, 6.5)
LON_RANGE = (94.5, 141.5)


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


class Run:
    """Mencatat audit dan hasil cek kualitas untuk satu eksekusi pipeline."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.run_id = datetime.now().strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:4]
        self.failed = 0
        self.warned = 0
        conn.execute(
            "INSERT INTO etl_run (run_id, started_at, status) VALUES (?, ?, 'RUNNING')",
            (self.run_id, now()),
        )

    def check(self, table: str, rule: str, passed: bool, affected: int = 0, detail: str = "",
              severity: str = "WARN") -> None:
        result = "PASS" if passed else severity
        if not passed and severity == "WARN":
            self.warned += 1
        self.conn.execute(
            "INSERT INTO etl_quality_check (run_id, target_table, rule, result, affected_rows, detail) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (self.run_id, table, rule, result, affected, detail),
        )

    def source(self, name: str, filename: str, fmt: str, table: str,
               step: Callable[[], Dict[str, int]]) -> None:
        print(f"[*] {fmt:<4} {filename} -> {table}")
        start = time.perf_counter()
        status, message = "SUCCESS", None
        counts = {"extracted": 0, "loaded": 0, "rejected": 0}
        try:
            counts.update(step())
            if counts["rejected"]:
                status = "WARNING"
                message = f"{counts['rejected']} baris ditolak saat validasi"
        except Exception as exc:  # satu sumber gagal tidak menghentikan sumber lain
            status, message = "FAILED", f"{type(exc).__name__}: {exc}"
            self.failed += 1
            print(f"    GAGAL: {message}")
        duration = int((time.perf_counter() - start) * 1000)
        self.conn.execute(
            """INSERT INTO etl_audit_log
               (run_id, source_name, source_file, source_format, target_table, records_extracted,
                records_loaded, records_rejected, status, message, duration_ms, executed_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (self.run_id, name, filename, fmt, table, counts["extracted"], counts["loaded"],
             counts["rejected"], status, message, duration, now()),
        )

    def finish(self) -> str:
        status = "FAILED" if self.failed else ("WARNING" if self.warned else "SUCCESS")
        self.conn.execute(
            "UPDATE etl_run SET finished_at = ?, status = ? WHERE run_id = ?",
            (now(), status, self.run_id),
        )
        return status


def load_dimensions(conn: sqlite3.Connection) -> Dict[str, Dict[str, int]]:
    conn.executemany("INSERT INTO dim_provinsi (nama_provinsi, pulau) VALUES (?, ?)", PROVINSI)
    conn.executemany("INSERT INTO dim_komoditas (nama_komoditas, kategori) VALUES (?, ?)", KOMODITAS)
    prov = {r[1]: r[0] for r in conn.execute("SELECT id, nama_provinsi FROM dim_provinsi")}
    kom = {r[1]: r[0] for r in conn.execute("SELECT id, nama_komoditas FROM dim_komoditas")}
    return {"provinsi": prov, "komoditas": kom}


def run_pipeline() -> Dict[str, object]:
    init_db()
    conn = get_connection()
    rebuild_analytic_tables(conn)
    dims = load_dimensions(conn)
    prov_id, kom_id = dims["provinsi"], dims["komoditas"]
    run = Run(conn)
    print(f"=== ETL {run.run_id} ===")

    # ---- 1. BPS ekspor (CSV) ----
    def step_bps() -> Dict[str, int]:
        df, totals = extract_coal_exports(RAW_DIR / "export_coal_by_country.csv")
        missing = int(df["volume_ribu_ton"].isna().sum())
        run.check("fact_ekspor_batubara", "Tanda '─' disimpan sebagai NULL, bukan 0", True, missing,
                  f"{missing} sel tidak tersedia di sumber")
        # Jumlah per negara harus sama dengan baris Total di berkas BPS
        sums = df.groupby("tahun")[["volume_ribu_ton", "nilai_fob_juta_usd"]].sum().reset_index()
        cmp = sums.merge(totals, on="tahun", suffixes=("", "_total"))
        off = cmp[((cmp["volume_ribu_ton"] - cmp["volume_ribu_ton_total"]).abs() > 1)
                  | ((cmp["nilai_fob_juta_usd"] - cmp["nilai_fob_juta_usd_total"]).abs() > 1)]
        run.check("fact_ekspor_batubara", "Jumlah per negara = baris Total BPS (toleransi 1)",
                  off.empty, len(off), f"dicek {len(cmp)} tahun")
        df.to_sql("fact_ekspor_batubara", conn, if_exists="append", index=False)
        return {"extracted": len(df), "loaded": len(df)}

    run.source("BPS — Ekspor batubara per negara tujuan", "export_coal_by_country.csv", "CSV",
               "fact_ekspor_batubara", step_bps)

    # ---- 2. ESDM Kaltim (XLSX) ----
    def step_kaltim() -> Dict[str, int]:
        df = extract_kaltim_operations(RAW_DIR / "kaltim_mining_operations.xlsx")
        tahun_berjalan = datetime.now().year
        df["status_periode"] = df["tahun"].apply(lambda t: "berjalan" if t >= tahun_berjalan else "final")
        df["provinsi_id"] = prov_id["Kalimantan Timur"]
        berjalan = int((df["status_periode"] == "berjalan").sum())
        run.check("fact_operasional_kaltim", f"Tahun {tahun_berjalan} ditandai 'berjalan' (belum lengkap)",
                  True, berjalan, "tidak dibandingkan langsung dengan tahun penuh")
        konstan = [ind for ind, g in df[df["status_periode"] == "final"].groupby("indikator")
                   if len(g) >= 3 and g["nilai"].nunique() == 1]
        run.check("fact_operasional_kaltim", "Indikator tidak bernilai sama setiap tahun",
                  not konstan, len(konstan), "; ".join(konstan))
        df.to_sql("fact_operasional_kaltim", conn, if_exists="append", index=False)
        return {"extracted": len(df), "loaded": len(df)}

    run.source("ESDM Kaltim — Indikator operasional", "kaltim_mining_operations.xlsx", "XLSX",
               "fact_operasional_kaltim", step_kaltim)

    # ---- 3. Lelang WIUP (JSON) ----
    def step_wiup() -> Dict[str, int]:
        df = extract_wiup_auctions(RAW_DIR / "wiup_auctions.json")
        n = len(df)
        df["komoditas_sumber"] = df["komoditas"]
        df["komoditas"] = df["komoditas_sumber"].map(normalize_komoditas)
        df["nama_provinsi"] = df["nama_provinsi"].map(lambda p: normalize_provinsi(p)[0])
        df["provinsi_id"] = df["nama_provinsi"].map(prov_id)
        df["komoditas_id"] = df["komoditas"].map(kom_id)
        df["nama_kabupaten"] = df["nama_kabupaten"].str.title()
        df["nama_blok"] = df["nama_blok"].str.title()

        bad_geo = ~(df["latitude"].between(*LAT_RANGE) & df["longitude"].between(*LON_RANGE))
        run.check("fact_lelang_wiup", "Koordinat berada di wilayah Indonesia", not bad_geo.any(),
                  int(bad_geo.sum()), "baris di luar batas ditolak", severity="REJECT")
        unmapped = df["provinsi_id"].isna() | df["komoditas_id"].isna()
        run.check("fact_lelang_wiup", "Provinsi & komoditas terpetakan ke dimensi", not unmapped.any(),
                  int(unmapped.sum()), "", severity="REJECT")
        merged = sorted({f"{a}→{b}" for a, b in zip(df["komoditas_sumber"], df["komoditas"]) if a != b and b})
        run.check("fact_lelang_wiup", "Harmonisasi nama komoditas", True, len(merged), ", ".join(merged))

        ok = df[~bad_geo & ~unmapped]
        cols = ["id_lelang", "nomor", "nama_blok", "provinsi_id", "komoditas_id", "nama_provinsi",
                "nama_kabupaten", "komoditas", "komoditas_sumber", "jenis_izin", "kdi_rupiah", "luas_ha",
                "tahapan", "latitude", "longitude", "jumlah_peserta", "source_format"]
        ok[cols].to_sql("fact_lelang_wiup", conn, if_exists="append", index=False)
        return {"extracted": n, "loaded": len(ok), "rejected": n - len(ok)}

    run.source("Ditjen Minerba — Lelang WIUP", "wiup_auctions.json", "JSON", "fact_lelang_wiup", step_wiup)

    # ---- 4. HEESI (PDF) ----
    heesi: Dict[str, object] = {}

    def heesi_extract():
        if not heesi:
            supply, reserves, total = extract_heesi_pdf(RAW_DIR / "esdm_heesi_statistics.pdf")
            heesi.update(supply=supply, reserves=reserves, total=total)
        return heesi["supply"], heesi["reserves"], heesi["total"]

    def step_supply() -> Dict[str, int]:
        supply, _, _ = heesi_extract()
        years = sorted(supply["tahun"])
        contiguous = years == list(range(years[0], years[-1] + 1))
        run.check("fact_pasokan_batubara_nasional", "Deret tahun lengkap tanpa celah", contiguous,
                  0, f"{years[0]}–{years[-1]}")
        neg = int((supply[["produksi_ton", "ekspor_ton", "impor_ton"]] < 0).any(axis=1).sum())
        run.check("fact_pasokan_batubara_nasional", "Produksi, ekspor, impor tidak negatif", neg == 0, neg)
        supply.to_sql("fact_pasokan_batubara_nasional", conn, if_exists="append", index=False)
        return {"extracted": len(supply), "loaded": len(supply)}

    run.source("Kementerian ESDM — HEESI 2024, Tabel 6.1.2", "esdm_heesi_statistics.pdf", "PDF",
               "fact_pasokan_batubara_nasional", step_supply)

    def step_reserves() -> Dict[str, int]:
        _, reserves, total = heesi_extract()
        n = len(reserves)
        reserves = reserves.rename(columns={"provinsi": "provinsi_sumber"})
        reserves["provinsi_id"] = reserves["provinsi_sumber"].map(lambda p: prov_id.get(normalize_provinsi(p)[0]))
        unmapped = reserves["provinsi_id"].isna()
        run.check("fact_cadangan_batubara_provinsi", "Nama provinsi (Inggris) terpetakan ke dim_provinsi",
                  not unmapped.any(), int(unmapped.sum()),
                  ", ".join(reserves.loc[unmapped, "provinsi_sumber"]), severity="REJECT")
        ok = reserves[~unmapped]
        s = float(ok["cadangan_juta_ton"].sum())
        run.check("fact_cadangan_batubara_provinsi", "Jumlah cadangan = baris TOTAL di PDF (toleransi 0,5)",
                  total is not None and abs(s - total) <= 0.5, 0, f"jumlah {s:,.2f} vs TOTAL {total:,.2f}")
        ok.to_sql("fact_cadangan_batubara_provinsi", conn, if_exists="append", index=False)
        return {"extracted": n, "loaded": len(ok), "rejected": n - len(ok)}

    run.source("Kementerian ESDM — HEESI 2024, Tabel 6.1.1", "esdm_heesi_statistics.pdf", "PDF",
               "fact_cadangan_batubara_provinsi", step_reserves)

    # ---- 5. MoDI izin (CSV) ----
    def step_modi() -> Dict[str, int]:
        df = extract_modi_licenses(RAW_DIR / "modi_mining_licenses.csv")
        n = len(df)
        norm = df["nama_provinsi"].map(normalize_provinsi)
        df["provinsi_sumber"] = df["nama_provinsi"]
        df["nama_provinsi"] = norm.map(lambda x: x[0])
        lintas = int(norm.map(lambda x: x[1]).sum())
        run.check("fact_izin_tambang", "Izin lintas provinsi dicatat di provinsi pertama", True, lintas,
                  "sel sumber berisi lebih dari satu provinsi")
        beda_ejaan = int((df["provinsi_sumber"] != df["nama_provinsi"]).sum())
        run.check("fact_izin_tambang", "Penyeragaman ejaan provinsi (kapital, alias)", True, beda_ejaan)
        df["komoditas_sumber"] = df["komoditas"]
        df["komoditas"] = df["komoditas_sumber"].map(normalize_komoditas)
        df["provinsi_id"] = df["nama_provinsi"].map(prov_id)
        df["komoditas_id"] = df["komoditas"].map(kom_id)
        unmapped = df["provinsi_id"].isna() | df["komoditas_id"].isna()
        reasons = sorted({f"{r.nama_perusahaan} (provinsi '{r.provinsi_sumber}')"
                          for r in df[unmapped].itertuples()})
        run.check("fact_izin_tambang", "Provinsi & komoditas terpetakan ke dimensi", not unmapped.any(),
                  int(unmapped.sum()), "; ".join(reasons), severity="REJECT")
        dup = int(df["sk_iup"].duplicated(keep=False).sum())
        run.check("fact_izin_tambang", "Nomor SK IUP unik", dup == 0, dup,
                  "baris tetap dimuat; satu SK bisa mencakup beberapa wilayah")
        df["kegiatan"] = df["kegiatan"].str.title()
        df["nama_kabupaten"] = df["nama_kabupaten"].str.title()
        ok = df[~unmapped]
        ok.to_sql("fact_izin_tambang", conn, if_exists="append", index=False)
        return {"extracted": n, "loaded": len(ok), "rejected": n - len(ok)}

    run.source("MoDI ESDM — Direktori izin usaha pertambangan", "modi_mining_licenses.csv", "CSV",
               "fact_izin_tambang", step_modi)

    # ---- Cek lintas sumber ----
    try:
        row = conn.execute("""
            SELECT p.ekspor_ton / 1e6, SUM(e.volume_ribu_ton) / 1e3
            FROM fact_pasokan_batubara_nasional p JOIN fact_ekspor_batubara e ON e.tahun = p.tahun
            WHERE p.tahun = (SELECT MAX(tahun) FROM fact_pasokan_batubara_nasional)
        """).fetchone()
        if row and row[0]:
            run.check("lintas sumber", "Ekspor BPS vs HEESI pada tahun terakhir", True, 0,
                      f"HEESI {row[0]:,.1f} jt ton, BPS {row[1]:,.1f} jt ton (selisih dijelaskan di dashboard)")
    except sqlite3.Error:
        pass

    seed_auth_user(conn)
    status = run.finish()
    conn.commit()

    summary = {
        t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        for t in ["fact_ekspor_batubara", "fact_operasional_kaltim", "fact_lelang_wiup",
                  "fact_pasokan_batubara_nasional", "fact_cadangan_batubara_provinsi",
                  "fact_izin_tambang", "dim_provinsi", "dim_komoditas"]
    }
    conn.close()
    print(f"=== ETL selesai: {status} ===")
    return {"run_id": run.run_id, "status": status, "tables": summary}



if __name__ == "__main__":
    res = run_pipeline()
    for k, v in res["tables"].items():
        print(f"  {k:<34} {v:>6,} baris")
