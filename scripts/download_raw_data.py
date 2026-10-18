"""
Script untuk mengunduh 5 dataset mentah (raw data) pertambangan
dengan 4 format berbeda (CSV, XLSX, JSON, PDF).
"""
import os
import requests

DATASETS = [
    {
        "filename": "data/raw/export_coal_by_country.csv",
        "url": "https://raw.githubusercontent.com/supertypeai/coalresearch/main/datasets/export_destination/Exports%20of%20Coal%20by%20Major%20Countries%20of%20Destination%2C%202012-2024.csv",
        "description": "BPS: Ekspor Batubara menurut Negara Tujuan Utama (CSV)",
    },
    {
        "filename": "data/raw/kaltim_mining_operations.xlsx",
        "url": "https://data.kaltimprov.go.id/dataset/74859a22-0526-49a4-9ad5-04e64a2846ee/resource/1eda7b34-cf03-4271-9667-4ea9f22389e0/download/data-pertambangan-tahun-2022-2026.xlsx",
        "description": "ESDM Kaltim: Indikator Operasional Pertambangan (XLSX)",
    },
    {
        "filename": "data/raw/wiup_auctions.json",
        "url": "https://raw.githubusercontent.com/supertypeai/coalresearch/main/datasets/auction_data_sample.json",
        "description": "ESDM Minerba: Data Lelang Wilayah Izin Usaha Pertambangan (JSON)",
    },
    {
        "filename": "data/raw/esdm_heesi_statistics.pdf",
        "url": "https://www.esdm.go.id/assets/media/content/content-handbook-of-energy-and-economic-statistics-of-indonesia-2024.pdf",
        "description": "Kementerian ESDM: Handbook of Energy & Economic Statistics 2024 (PDF)",
    },
    {
        "filename": "data/raw/modi_mining_licenses.csv",
        "url": "https://raw.githubusercontent.com/supertypeai/coalresearch/main/datasets/modi_mining_license_merge_v2.csv",
        "description": "ESDM MoDI: Sebaran Izin Usaha Pertambangan Multi-Komoditas (CSV)",
    },
]

def download_all():
    os.makedirs("data/raw", exist_ok=True)
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    for item in DATASETS:
        target = item["filename"]
        if os.path.exists(target) and os.path.getsize(target) > 0:
            print(f"[OK] {target} sudah ada ({os.path.getsize(target):,} bytes)")
            continue

        print(f"[DOWNLOADING] {item['description']}...")
        r = requests.get(item["url"], headers=headers, stream=True, timeout=30)
        r.raise_for_status()

        with open(target, "wb") as f:
            for chunk in r.iter_content(chunk_size=128 * 1024):
                if chunk:
                    f.write(chunk)

        size = os.path.getsize(target)
        print(f"[SUCCESS] {target} tersimpan ({size:,} bytes)")

if __name__ == "__main__":
    download_all()
