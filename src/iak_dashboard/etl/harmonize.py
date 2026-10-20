"""
Kamus harmonisasi dimensi lintas sumber.

Setiap sumber menulis provinsi dan komoditas dengan cara berbeda:
HEESI (PDF) memakai bahasa Inggris ("East Kalimantan"), MoDI (CSV) campuran huruf besar/kecil
dan kadang menggabungkan beberapa provinsi dalam satu sel, Lelang WIUP (JSON) memakai
"NIKEL DMP" dan "BATUBARA", sedangkan MoDI memakai "Nickel" dan "Coal".
Semua nilai dipetakan ke satu nama baku sebelum dimuat agar tabel fakta bisa digabung.
"""
from typing import Optional, Tuple

# (nama baku, pulau)
PROVINSI = [
    ("Aceh", "Sumatera"), ("Sumatera Utara", "Sumatera"), ("Sumatera Barat", "Sumatera"),
    ("Riau", "Sumatera"), ("Kepulauan Riau", "Sumatera"), ("Jambi", "Sumatera"),
    ("Sumatera Selatan", "Sumatera"), ("Kepulauan Bangka Belitung", "Sumatera"),
    ("Bengkulu", "Sumatera"), ("Lampung", "Sumatera"),
    ("DKI Jakarta", "Jawa"), ("Jawa Barat", "Jawa"), ("Banten", "Jawa"), ("Jawa Tengah", "Jawa"),
    ("DI Yogyakarta", "Jawa"), ("Jawa Timur", "Jawa"),
    ("Bali", "Bali & Nusa Tenggara"), ("Nusa Tenggara Barat", "Bali & Nusa Tenggara"),
    ("Nusa Tenggara Timur", "Bali & Nusa Tenggara"),
    ("Kalimantan Barat", "Kalimantan"), ("Kalimantan Tengah", "Kalimantan"),
    ("Kalimantan Selatan", "Kalimantan"), ("Kalimantan Timur", "Kalimantan"),
    ("Kalimantan Utara", "Kalimantan"),
    ("Sulawesi Utara", "Sulawesi"), ("Gorontalo", "Sulawesi"), ("Sulawesi Tengah", "Sulawesi"),
    ("Sulawesi Barat", "Sulawesi"), ("Sulawesi Selatan", "Sulawesi"), ("Sulawesi Tenggara", "Sulawesi"),
    ("Maluku", "Maluku"), ("Maluku Utara", "Maluku"),
    ("Papua", "Papua"), ("Papua Barat", "Papua"), ("Papua Barat Daya", "Papua"),
    ("Papua Tengah", "Papua"), ("Papua Pegunungan", "Papua"), ("Papua Selatan", "Papua"),
]

_PROV_BY_KEY = {nama.upper(): nama for nama, _ in PROVINSI}

PROVINSI_ALIAS = {
    # Ejaan lain di MoDI / WIUP
    "BANGKA BELITUNG": "Kepulauan Bangka Belitung",
    "DAERAH ISTIMEWA YOGYAKARTA": "DI Yogyakarta",
    # Nama berbahasa Inggris di HEESI 2024 (Tabel 6.1.1)
    "NORTH SUMATERA": "Sumatera Utara", "WEST SUMATERA": "Sumatera Barat",
    "SOUTH SUMATERA": "Sumatera Selatan", "CENTRAL JAVA": "Jawa Tengah", "EAST JAVA": "Jawa Timur",
    "WEST JAVA": "Jawa Barat", "WEST KALIMANTAN": "Kalimantan Barat",
    "CENTRAL KALIMANTAN": "Kalimantan Tengah", "SOUTH KALIMANTAN": "Kalimantan Selatan",
    "EAST KALIMANTAN": "Kalimantan Timur", "NORTH KALIMANTAN": "Kalimantan Utara",
    "CENTRAL SULAWESI": "Sulawesi Tengah", "SOUTH SULAWESI": "Sulawesi Selatan",
    "SOUTHEAST SULAWESI": "Sulawesi Tenggara", "WEST SULAWESI": "Sulawesi Barat",
    "NORTH SULAWESI": "Sulawesi Utara", "NORTH MALUKU": "Maluku Utara", "WEST PAPUA": "Papua Barat",
}

# (nama baku, kategori)
KOMODITAS = [
    ("Batubara", "Batubara"),
    ("Nikel", "Mineral logam"), ("Emas", "Mineral logam"), ("Tembaga", "Mineral logam"),
    ("Bijih besi", "Mineral logam"), ("Timah", "Mineral logam"), ("Bauksit", "Mineral logam"),
    ("Galena", "Mineral logam"),
    ("Mineral bukan logam", "Mineral bukan logam"), ("Batu gamping", "Mineral bukan logam"),
    ("Lempung", "Mineral bukan logam"),
    ("Granit", "Batuan"), ("Pasir", "Batuan"), ("Sirtu", "Batuan"),
    ("Lainnya", "Lainnya"),
]

KOMODITAS_ALIAS = {
    "COAL": "Batubara", "BATUBARA": "Batubara", "BATU BARA": "Batubara",
    "NICKEL": "Nikel", "NIKEL": "Nikel", "NIKEL DMP": "Nikel",
    "GOLD": "Emas", "EMAS": "Emas",
    "COPPER": "Tembaga", "TEMBAGA": "Tembaga",
    "IRON": "Bijih besi", "BIJIH BESI": "Bijih besi",
    "TIN": "Timah", "TIMAH": "Timah",
    "BAUXITE": "Bauksit", "BAUKSIT": "Bauksit",
    "GALENA": "Galena",
    "NON-METALLIC MINERAL": "Mineral bukan logam",
    "LIMESTONE": "Batu gamping", "CLAY": "Lempung",
    "GRANITE": "Granit", "SAND": "Pasir", "SAND, STONE, GRAVEL": "Sirtu",
    "OTHERS": "Lainnya",
}


def normalize_provinsi(raw: Optional[str]) -> Tuple[Optional[str], bool]:
    """
    Kembalikan (nama baku, lintas_provinsi).
    Sel berisi beberapa provinsi ("Kalimantan Tengah, Kalimantan Timur") dipetakan ke provinsi pertama.
    Nilai yang tidak dikenal dikembalikan None.
    """
    if raw is None:
        return None, False
    text = str(raw).strip()
    if not text or text in ("-", "nan"):
        return None, False
    parts = [p.strip() for p in text.split(",") if p.strip()]
    key = parts[0].upper()
    nama = _PROV_BY_KEY.get(key) or PROVINSI_ALIAS.get(key)
    return nama, len(parts) > 1


def normalize_komoditas(raw: Optional[str]) -> Optional[str]:
    if raw is None:
        return None
    key = str(raw).strip().upper()
    return KOMODITAS_ALIAS.get(key)
