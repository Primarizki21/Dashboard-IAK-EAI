"""
Modul ekstraktor dan transformasi data untuk sumber data heterogen (CSV, XLSX, JSON, PDF).
Menerapkan prinsip Data-Level EAI: standarisasi skema, pembersihan nilai cacat, harmonisasi unit.
"""
import json
from pathlib import Path
from typing import Tuple, List, Dict, Any, Optional
import pandas as pd
import pdfplumber

def extract_coal_exports(csv_path: Path) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Ekstraksi data ekspor batubara BPS (Format: CSV).
    Satu berkas berisi dua tabel: berat bersih (ribu ton) dan nilai FOB (juta USD).
    Tanda "─" di sumber berarti data tidak tersedia, jadi disimpan sebagai NULL (bukan 0).
    Mengembalikan (data per negara-tahun, baris Total dari sumber untuk validasi).
    """
    raw = pd.read_csv(csv_path, header=None)
    years = [int(y) for y in raw.iloc[2, 1:14].values]

    def clean_num(series: pd.Series) -> pd.Series:
        s = series.astype(str).str.replace(",", "").str.strip()
        s = s.replace({"─": None, "-": None, "": None, "nan": None})
        return pd.to_numeric(s, errors="coerce")

    def block(start: int, value_name: str) -> pd.DataFrame:
        # 11 baris negara, lalu 1 baris Total
        df = raw.iloc[start:start + 12, 0:14].copy()
        df.columns = ["negara_tujuan"] + years
        df["negara_tujuan"] = df["negara_tujuan"].astype(str).str.strip()
        df = df.melt(id_vars=["negara_tujuan"], var_name="tahun", value_name=value_name)
        df[value_name] = clean_num(df[value_name])
        df["tahun"] = df["tahun"].astype(int)
        return df

    w = block(4, "volume_ribu_ton")
    v = block(18, "nilai_fob_juta_usd")
    merged = pd.merge(w, v, on=["negara_tujuan", "tahun"])

    is_total = merged["negara_tujuan"].str.lower() == "total"
    totals = merged[is_total].drop(columns=["negara_tujuan"]).reset_index(drop=True)
    data = merged[~is_total].reset_index(drop=True)
    data["source_format"] = "CSV"
    return data, totals

def extract_kaltim_operations(xlsx_path: Path) -> pd.DataFrame:
    """
    Ekstraksi indikator operasional pertambangan Kaltim (Format: XLSX).
    Normalisasi kolom tahun menjadi format tabular relational (Tidy Data).
    """
    df = pd.read_excel(xlsx_path)
    year_cols = [c for c in df.columns if isinstance(c, int) or (isinstance(c, str) and c.isdigit())]

    records: List[Dict[str, Any]] = []
    for _, row in df.iterrows():
        indikator = str(row["Daftar Data"]).strip()
        satuan = str(row["Satuan"]).strip()
        for y in year_cols:
            val = row[y]
            if pd.notna(val) and val != "":
                if isinstance(val, str) and val.startswith("="):
                    continue
                try:
                    num_val = float(val)
                    records.append({
                        "indikator": indikator,
                        "tahun": int(y),
                        "nilai": num_val,
                        "satuan": satuan,
                        "source_format": "XLSX"
                    })
                except (ValueError, TypeError):
                    continue

    return pd.DataFrame(records)

def extract_wiup_auctions(json_path: Path) -> pd.DataFrame:
    """
    Ekstraksi data lelang Wilayah Izin Usaha Pertambangan ESDM (Format: JSON).
    Ekstraksi koordinat geografis (lat, long), status lelang, kompensasi informasi (KDI).
    """
    with open(json_path, "r", encoding="utf-8") as f:
        auctions = json.load(f)

    records: List[Dict[str, Any]] = []
    for a in auctions:
        records.append({
            "id_lelang": a.get("id"),
            "nomor": a.get("nomor", ""),
            "nama_blok": a.get("namaBlok", "").strip(),
            "nama_kabupaten": a.get("namaKab", "").strip(),
            "nama_provinsi": a.get("namaProv", "").strip(),
            "pulau": a.get("pulau", "").strip(),
            "komoditas": a.get("komoditas", "").strip(),
            "jenis_izin": a.get("jenisIzin", "").strip(),
            "kegiatan": a.get("kegiatan", "").strip(),
            "kdi_rupiah": float(a.get("kdi", 0) or 0),
            "luas_ha": float(a.get("luasSk", 0) or 0),
            "tahapan": a.get("tahapanSaatIni", "").strip(),
            "latitude": float(a.get("lat", 0.0) or 0.0),
            "longitude": float(a.get("long", 0.0) or 0.0),
            "jumlah_peserta": int(a.get("jumlahPeserta", 0) or 0),
            "source_format": "JSON"
        })
    return pd.DataFrame(records)

def extract_heesi_pdf(pdf_path: Path) -> Tuple[pd.DataFrame, pd.DataFrame, Optional[float]]:
    """
    Ekstraksi statistik batubara nasional dari publikasi HEESI ESDM 2024 (Format: PDF).
    Tabel 1: Neraca Pasokan Batubara Nasional 2014-2024 (Hal. 77, Tabel 6.1.2).
    Tabel 2: Cadangan dan Sumber Daya Batubara per Provinsi Des 2024 (Hal. 76, Tabel 6.1.1).
    Konsumsi domestik tidak ada di tabel ini, jadi dihitung: produksi - ekspor + impor.
    Mengembalikan (neraca, cadangan per provinsi, total cadangan menurut baris TOTAL di PDF).
    """
    supply_records: List[Dict[str, Any]] = []
    reserves_records: List[Dict[str, Any]] = []
    reserves_total: Optional[float] = None

    def num(cell: Any) -> float:
        return float(str(cell).replace(",", "").strip())

    with pdfplumber.open(pdf_path) as pdf:
        # 1. Pasokan Batubara Nasional dari Halaman 77 (Tabel 6.1.2) - Rentang 2014-2024
        for table in pdf.pages[76].extract_tables():
            for row in table:
                if not row or not row[0]:
                    continue
                yr_str = str(row[0]).split()[0]
                if yr_str.isdigit():
                    prod, exp, imp = num(row[1]), num(row[2]), num(row[3])
                    supply_records.append({
                        "tahun": int(yr_str),
                        "produksi_ton": prod,
                        "ekspor_ton": exp,
                        "impor_ton": imp,
                        "konsumsi_domestik_ton": prod - exp + imp,
                        "source_format": "PDF"
                    })

        # 2. Cadangan Batubara per Provinsi dari Halaman 76 (Tabel 6.1.1) - Status Des 2024
        for table in pdf.pages[75].extract_tables():
            for row in table:
                if not row or len(row) < 10 or not row[1]:
                    continue
                prov = str(row[1]).replace("\n", " ").strip()
                try:
                    if prov == "TOTAL":
                        reserves_total = num(row[9])
                        continue
                    if prov in ["Province", "None"] or not prov:
                        continue
                    reserves_records.append({
                        "provinsi": prov,
                        "sumberdaya_juta_ton": num(row[7]),
                        "cadangan_juta_ton": num(row[9]),
                        "source_format": "PDF"
                    })
                except (ValueError, TypeError):
                    continue

    return pd.DataFrame(supply_records), pd.DataFrame(reserves_records), reserves_total


def extract_modi_licenses(csv_path: Path) -> pd.DataFrame:
    """
    Ekstraksi data perizinan pertambangan nasional MoDI ESDM (Format: CSV).
    Pembersihan ribuan izin usaha pertambangan multi-komoditas.
    """
    df = pd.read_csv(csv_path, low_memory=False)
    cleaned = pd.DataFrame({
        "nama_perusahaan": df["nama_usaha"].fillna("-").astype(str).str.strip(),
        "badan_usaha": df["badan_usaha"].fillna("-").astype(str).str.strip(),
        "jenis_izin": df["jenis_izin"].fillna("-").astype(str).str.strip(),
        "sk_iup": df["sk_iup"].fillna("-").astype(str).str.strip(),
        "nama_provinsi": df["nama_prov"].fillna("-").astype(str).str.strip(),
        "nama_kabupaten": df["nama_kab"].fillna("-").astype(str).str.strip(),
        "kegiatan": df["kegiatan"].fillna("-").astype(str).str.strip(),
        "luas_sk_ha": pd.to_numeric(df["luas_sk"], errors="coerce").fillna(0.0),
        "cnc": df["cnc"].fillna("-").astype(str).str.strip(),
        "komoditas": df["komoditas_mapped"].fillna("Other").astype(str).str.strip(),
        "source_format": "CSV"
    })
    return cleaned
