# Neraca Tambang

Dashboard data batubara Indonesia untuk tugas Integrasi Aplikasi Korporat (IAK), Kelompok 6, FTMM Universitas Airlangga.

Lima berkas sumber dalam empat format (CSV, XLSX, JSON, PDF) diekstrak, diseragamkan, divalidasi, lalu dimuat ke satu basis data SQLite (`data/processed/unified_mining.db`). Dashboard membaca basis data itu lewat API FastAPI yang wajib login.

## Sumber data

| Berkas | Format | Penerbit | Diperoleh dari | Tabel tujuan |
|---|---|---|---|---|
| `export_coal_by_country.csv` | CSV | BPS | Salinan tabel BPS di repositori `supertypeai/coalresearch` | `fact_ekspor_batubara` |
| `kaltim_mining_operations.xlsx` | XLSX | Dinas ESDM Kaltim | Portal Satu Data Kaltim | `fact_operasional_kaltim` |
| `wiup_auctions.json` | JSON | Ditjen Minerba | Salinan data lelang WIUP di `supertypeai/coalresearch` | `fact_lelang_wiup` |
| `esdm_heesi_statistics.pdf` | PDF | Kementerian ESDM | HEESI 2024, esdm.go.id (Tabel 6.1.1 dan 6.1.2) | `fact_pasokan_batubara_nasional`, `fact_cadangan_batubara_provinsi` |
| `modi_mining_licenses.csv` | CSV | MoDI ESDM | Salinan data MoDI di `supertypeai/coalresearch` | `fact_izin_tambang` |

`scripts/download_raw_data.py` mengunduh ulang semua berkas.

## Apa yang dilakukan ETL

- **Harmonisasi dimensi.** Nama provinsi (termasuk nama berbahasa Inggris di HEESI) dan komoditas (`COAL`/`BATUBARA`, `NICKEL`/`NIKEL`/`NIKEL DMP`, dst.) dipetakan ke `dim_provinsi` dan `dim_komoditas`. Tabel fakta menyimpan `provinsi_id`/`komoditas_id`, jadi data cadangan (PDF), izin (CSV), dan lelang (JSON) bisa digabung per provinsi. Kamusnya ada di `src/iak_dashboard/etl/harmonize.py`.
- **Nilai kosong tetap kosong.** Tanda `─` di data BPS disimpan sebagai NULL, bukan 0.
- **Validasi.** Jumlah per negara dicocokkan dengan baris Total BPS. Jumlah cadangan dicocokkan dengan baris TOTAL di PDF. Koordinat WIUP harus berada di wilayah Indonesia. Tahun yang belum selesai di data Kaltim ditandai `berjalan`, dan indikator yang nilainya sama setiap tahun ditandai.
- **Audit.** Setiap eksekusi mendapat `run_id`. Jumlah baris diekstrak/dimuat/ditolak, durasi, dan status per sumber dicatat di `etl_audit_log`; hasil tiap aturan validasi dicatat di `etl_quality_check`. Satu sumber yang gagal tidak menghentikan sumber lain.

## Menjalankan

Butuh Python 3.12 atau lebih baru.

Dengan `uv`:

```bash
uv sync
uv run python src/iak_dashboard/etl/pipeline.py
uv run iak-dashboard
```

Tanpa `uv` (Windows):

```bash
python -m venv .venv
.venv\Scripts\pip install -e .
.venv\Scripts\python src\iak_dashboard\etl\pipeline.py
.venv\Scripts\iak-dashboard
```

Buka http://127.0.0.1:8000. Akun demo: `admin` / `admin123`.

Server akan menjalankan ETL otomatis bila basis data belum ada. Jalankan `pipeline.py` lagi kapan saja untuk memuat ulang data; riwayat eksekusi tetap tersimpan.

## Halaman dashboard

Setiap halaman mencantumkan sumber datanya di bawah judul.

| Menu | Isi | Sumber |
|---|---|---|
| Ringkasan | Satu angka utama dari tiap sumber, neraca produksi–ekspor, izin per komoditas | semua |
| Produksi & Ekspor Batubara | Tren dan peringkat negara tujuan (volume/nilai), harga per ton, ekspor BPS vs HEESI | CSV BPS, PDF HEESI |
| Izin Tambang per Provinsi | Izin dan cadangan per provinsi; klik provinsi untuk menyaring daftar izin; unduh CSV | CSV MoDI, PDF HEESI |
| Lelang Lahan Tambang Baru | Peta blok WIUP yang dilelang, KDI per komoditas, daftar blok | JSON Ditjen Minerba |
| Operasional Tambang Kaltim | Produksi per jenis izin, porsi dari produksi nasional, lifting migas, indikator lingkungan | XLSX ESDM Kaltim, PDF HEESI |
| Sumber Data & ETL | Hasil load per sumber, hasil validasi, hubungan tabel, riwayat ETL | `etl_*` |

Halaman masuk menampilkan angka ringkas dari endpoint publik `/api/public/sekilas`; semua data rinci tetap wajib login.

## Struktur

```
data/raw/                      berkas sumber
data/processed/                unified_mining.db (dibuat oleh ETL)
src/iak_dashboard/
  etl/extractors.py            pembaca per format
  etl/harmonize.py             kamus provinsi & komoditas
  etl/schema.py                skema SQLite
  etl/pipeline.py              alur ETL, validasi, audit
  api/auth.py                  login, sesi, hash kata sandi (PBKDF2)
  api/mining.py                endpoint data (wajib login)
  api/app.py                   aplikasi FastAPI
  static/login.html            halaman masuk
  static/dashboard.html        kerangka dashboard
  static/css/app.css           gaya
  static/js/                   api.js, viz.js (grafik), app.js (navigasi), pages/*.js
docs/                          laporan
```
