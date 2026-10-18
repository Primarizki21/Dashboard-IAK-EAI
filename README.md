# MINERBA EAI - Dashboard Integrasi Sektor Pertambangan Indonesia

Dashboard analitik terintegrasi berbasis web untuk tugas besar mata kuliah **Integrasi Aplikasi Korporat (IAK)** — Fakultas Teknologi Maju dan Multidisiplin (FTMM), Universitas Airlangga.

* **Kelompok:** Kelompok 6
* **Topik:** 06 - Pertambangan (Mining)
* **Prinsip Utama:** **Data-Level EAI** (Enterprise Application Integration)
* **Format Sumber Data:** **4 Format Berbeda** (CSV, XLSX, JSON, PDF)

---

## 1. Fitur Utama Aplikasi

1. **Arsitektur Multi-Page & Proteksi Sesi**:
   - **Landing Page Publik (`/`)**: Menampilkan teaser ringkasan eksekutif, status integrasi sistem, 5 kartu dataset interaktif dengan animasi hover lift dan direct outbound link ke portal resmi, serta modal login terautentikasi.
   - **Dashboard Analitik Terproteksi (`/dashboard`)**: Ruang kerja *Exploratory Visual Dashboard* (EVD) multi-tab yang diproteksi route guard berbasis token sesi (`admin` / `admin123`).
2. **Ringkasan Eksekutif & Neraca Energi (PDF HEESI 2024)**: Visualisasi tren pasokan batubara nasional 2014-2024 (produksi, ekspor, konsumsi DMO) dan estimasi cadangan terbukti per provinsi yang diekstraksi dari publikasi resmi PDF Kementerian ESDM.
3. **Analitik Ekspor Global (BPS CSV)**: Visualisasi tren ekspor batubara 2012-2024 (Volume & FOB Value) dengan filter dinamis 11 negara tujuan utama.
4. **Indikator Operasional Kaltim (ESDM XLSX)**: Analisis komparasi produksi batubara PKP2B vs IUP, lifting migas, serta komitmen reklamasi lingkungan vs penertiban penambangan liar.
5. **Peta Sebaran Lelang WIUP (ESDM JSON)**: Peta geospasial interaktif (Leaflet.js) untuk 40 blok lelang tambang di Indonesia dengan detail koordinat, filter status, dan nilai Kompensasi Data Informasi (KDI).
6. **Master Direktori 4,152 Izin Usaha Pertambangan (MoDI CSV)**: Tabel data multi-komoditas nasional dengan pencarian real-time, filter provinsi/komoditas, dan pagination dinamis.
7. **Audit Trail Data-Level EAI**: Log eksekusi pipeline ETL real-time dari basis data SQLite untuk pembuktian lineage data, status transaksi, dan jumlah baris terintegrasi.
---

## 2. Matriks 5 Dataset Heterogen (4 Format)

| No | Dataset | Format | Sumber Resmi & Metode Ekstraksi | Tabel Target Database | Jumlah Baris |
|:--:|---|:---:|---|---|:---:|
| 1 | Ekspor Batubara per Negara 2012-2024 | **CSV** | BPS (Statistik Perdagangan Luar Negeri - Ekspor Bulanan/Tahunan) | `fact_ekspor_batubara` | 143 |
| 2 | Operasional Pertambangan Prov. Kaltim | **XLSX** | Dinas ESDM Prov. Kaltim (Portal Open Data CKAN Kaltim) | `fact_operasional_kaltim` | 42 |
| 3 | Lelang Wilayah Izin Usaha Pertambangan | **JSON** | Ditjen Minerba ESDM (Web Scraping API Portal Lelang WIUP) | `fact_lelang_wiup` | 40 |
| 4 | Neraca Pasokan & Cadangan Batubara | **PDF** | Kementerian ESDM (Buku Statistik HEESI 2024 - Hal. 76 & 77) | `fact_pasokan_batubara_nasional` & `fact_cadangan_batubara_provinsi` | 34 |
| 5 | Direktori Izin Usaha Pertambangan | **CSV** | MoDI ESDM (Web Scraping Direktori Perizinan Tambang Nasional) | `fact_izin_tambang` | 4,152 |
---

## 3. Cara Menjalankan Aplikasi (Menggunakan Astral `uv`)

Pastikan Astral `uv` telah terpasang di sistem.

```bash
# 1. Masuk ke direktori proyek
cd /home/primarizki/project/iak-dashboard

# 2. Sinkronisasi dependensi virtualenv
uv sync

# 3. (Opsional) Jalankan kembali pipeline ETL jika ingin reload data
uv run python3 src/iak_dashboard/etl/pipeline.py

# 4. Jalankan aplikasi web dashboard
uv run iak-dashboard
```

Buka peramban di: **`http://127.0.0.1:8000`**

### Kredensial Login Pengujian
* **Administrator:** `admin` / `admin123`

---

## 4. Struktur Proyek

```
iak-dashboard/
├── README.md                  # Dokumentasi ringkas proyek
├── pyproject.toml             # Konfigurasi proyek Python Astral uv
├── data/
│   ├── raw/                   # 5 Dataset mentah (CSV, XLSX, JSON, PDF)
│   └── processed/             # Unified SQLite database (unified_mining.db)
├── docs/
│   └── LAPORAN_EAI_PERTAMBANGAN.md  # Laporan teknis lengkap (Bobot 40%)
├── scripts/
│   └── download_raw_data.py   # Skrip pengunduh otomatis data mentah
└── src/
    └── iak_dashboard/
        ├── __init__.py        # Entrypoint CLI
        ├── api/               # Backend FastAPI & Auth
        │   ├── app.py
        │   ├── auth.py
        │   └── mining.py
        ├── etl/               # Modul ETL per format
        │   ├── extractors.py
        │   ├── pipeline.py
        │   └── schema.py
        └── static/            # Frontend Web Dashboard Modular
            ├── landing.html   # Halaman depan publik & form login
            ├── dashboard.html # Dashboard analitik terproteksi (EVD)
            ├── css/
            │   └── dashboard.css
            └── js/
                ├── auth.js    # Sesi & route guard
                ├── landing.js # Teaser KPI publik & handler login
                ├── charts.js  # Visualisasi Chart.js (PDF, CSV, XLSX)
                ├── map.js     # Peta spasial Leaflet.js (JSON)
                ├── licenses.js# Master direktori 4,152 IUP (CSV)
                ├── audit.js   # Audit trail pipeline ETL
                └── dashboard.js # Bootstrapper dashboard & tab nav
```
