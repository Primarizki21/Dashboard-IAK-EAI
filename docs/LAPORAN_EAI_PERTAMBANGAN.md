# LAPORAN TUGAS BESAR INTEGRASI APLIKASI KORPORAT (IAK)
## "Penerapan Prinsip Data-Level EAI dalam Pengembangan Dashboard Analitik Terintegrasi Sektor Pertambangan Indonesia"

* **Mata Kuliah:** Integrasi Aplikasi Korporat (IAK)
* **Program Studi:** Teknologi Informasi / Rekayasa Komputasi / Sains Data
* **Institusi:** Fakultas Teknologi Maju dan Multidisiplin (FTMM), Universitas Airlangga
* **Kelompok:** Kelompok 6
* **Topik/Sektor:** 06 - Pertambangan (Mining)
* **Tahun Akademik:** 2026

---

## DAFTAR ISI
1. Pendahuluan & Latar Belakang
2. Konsep & Landasan Teori Data-Level EAI
3. Karakteristik & Heterogenitas 5 Dataset Sumber
4. Perancangan Arsitektur Integrasi & Skema Data Warehouse
5. Implementasi Pipeline ETL (Extract, Transform, Load)
6. Analisis Insight & Temuan Kunci dari Visualisasi Data
7. Fitur Aplikasi Dashboard & Panduan Penggunaan
8. Kesimpulan & Rekomendasi

---

## 1. PENDAHULUAN & LATAR BELAKANG

Sektor pertambangan merupakan salah satu pilar penopang perekonomian Indonesia yang menyumbang lebih dari 10% Produk Domestik Bruto (PDB) nasional serta devisa ekspor bernilai miliaran dolar AS setiap tahunnya. Namun, tata kelola informasi sektor ini menghadapi tantangan klasik arsitektur korporat, yaitu **Fragmentasi Data (Data Silos)**. 

Informasi pertambangan tersebar di berbagai instansi pemerintah dan entitas bisnis dengan platform teknologi, format berkas, serta struktur skema yang tidak homogen:
* **Badan Pusat Statistik (BPS)** mempublikasikan data statistik perdagangan luar negeri (ekspor) dalam bentuk tabel dinamis CSV dengan format data un-pivoted dan multi-header.
* **Dinas Energi dan Sumber Daya Mineral (ESDM) Tingkat Provinsi (misal: Prov. Kaltim)** menyediakan indikator operasional lokal dalam berkas spreadsheet Microsoft Excel (XLSX).
* **Direktorat Jenderal Mineral dan Batubara (Ditjen Minerba)** mengelola data lelang Wilayah Izin Usaha Pertambangan (WIUP) dengan atribut spasial dan finansial dalam format JSON / Web API.
* **Kementerian ESDM Pusat** mempublikasikan buku laporan tahunan (*Handbook of Energy and Economic Statistics of Indonesia* - HEESI) yang memuat neraca energi dan cadangan batubara dalam format dokumen publikasi resmi PDF.
* **Minerba One Data Indonesia (MoDI)** mencatat ribuan izin konsesi usaha pertambangan multi-komoditas dalam format tabular CSV.

Ketiadaan integrasi menyebabkan pengambil kebijakan, analis industri, maupun pelaku usaha kesulitan mendapatkan pandangan komprehensif (*single source of truth*) mengenai korelasi antara produksi di daerah, perizinan, lelang blok eksplorasi baru, cadangan nasional, dan realisasi ekspor ke pasar global. Proyek ini menyelesaikan permasalahan tersebut melalui pendekatan **Data-Level Enterprise Application Integration (EAI)**.

---

## 2. KONSEP & LANDASAN TEORI DATA-LEVEL EAI

### 2.1 Posisi Data-Level dalam Taksonomi EAI
Enterprise Application Integration (EAI) secara umum dikelompokkan ke dalam empat tingkatan abstraksi:
1. **User Interface-Level EAI:** Integrasi pada lapisan antarmuka visual (screen scraping / portal agregator).
2. **Method/Process-Level EAI:** Integrasi pada logika bisnis melalui RPC, Enterprise Service Bus (ESB), atau orkestrasi workflow BPMN.
3. **Application Interface-Level EAI:** Integrasi antar-aplikasi menggunakan API gateway (RESTful / GraphQL / gRPC).
4. **Data-Level EAI:** Integrasi data dari berbagai sumber sistem penyimpanan yang independen ke dalam skema terpadu (*Unified Schema*) tanpa memodifikasi sistem sumber aslinya.

```
+-------------------------------------------------------------+
| Lapisan Presentasi: Web Dashboard Analitik & Login User      |
+-------------------------------------------------------------+
                               ^
                               | (Unified SQL Interface)
+-------------------------------------------------------------+
| Unified Storage (Data Warehouse): unified_mining.db (SQLite) |
+-------------------------------------------------------------+
                               ^
                               | (Load Phase)
+-------------------------------------------------------------+
| Data-Level EAI Engine: Pipeline ETL Python (Astral uv)      |
| - Standardisasi Satuan & Harmonisasi Dimensi                |
| - Data Cleansing, Imputasi & Validasi Tipe Data             |
| - Pencatatan Audit Log & Lineage Metadata                   |
+-------------------------------------------------------------+
                               ^
                               | (Extract Phase)
+--------------+--------------+--------------+---------------+
| CSV Parser   | XLSX Parser  | JSON Parser  | PDF Parser    |
| (BPS & MoDI) | (OpenPyXL)   | (Ditjen)     | (PDFPlumber)  |
+--------------+--------------+--------------+---------------+
| Sumber 1, 5  | Sumber 2     | Sumber 3     | Sumber 4      |
+--------------+--------------+--------------+---------------+
```

### 2.2 Keunggulan Pendekatan Data-Level EAI pada Proyek Ini
* **Non-Invasive:** Sistem sumber (portal BPS, ESDM, Satu Data) tidak memerlukan perubahan backend atau konfigurasi khusus.
* **Batch Consistency:** Menerapkan transformasi analitik berkala sehingga performa dashboard tidak membebani sistem sumber.
* **Harmonisasi Semantik:** Mengatasi ambiguitas istilah komoditas (misal: "Coal" pada sumber BPS dipetakan secara terpadu dengan "BATUBARA" pada sumber Ditjen Minerba).

---

## 3. KARAKTERISTIK & HETEROGENITAS 5 DATASET SUMBER

Proyek ini menggunakan **5 dataset resmi** dengan **4 format data yang berbeda** (melampaui syarat minimal 3 format pada panduan tugas):

| No | Nama Dataset | Format Berkas | Lembaga Penerbit | Cakupan Data & Indikator Kunci | Jumlah Baris Hasil Ekstraksi |
|:--:|---|:---:|---|---|:---:|
| 1 | **Ekspor Batubara menurut Negara Tujuan Utama (2012-2024)** | `CSV` | Badan Pusat Statistik (BPS) | Negara mitra dagang (11 negara utama), volume ekspor (ribu ton), nilai FOB (juta USD), periode 13 tahun tahunan. | 143 baris |
| 2 | **Indikator Operasional Pertambangan Kaltim (2022-2026)** | `XLSX` | Dinas ESDM Prov. Kalimantan Timur | Produksi batubara PKP2B vs IUP, lifting minyak (Barel), lifting gas (MMBTU), luas reklamasi (Ha), penertiban tambang liar. | 42 baris |
| 3 | **Lelang Wilayah Izin Usaha Pertambangan (WIUP)** | `JSON` | Ditjen Minerba Kementerian ESDM | Daftar 40 blok lelang tambang dengan atribut spasial & finansial, diperoleh melalui scraping data API portal `minerba.esdm.go.id/lelang/`. | 40 baris |
| 4 | **Neraca Pasokan & Cadangan Batubara Nasional** | `PDF` | Kementerian ESDM (Buku Statistik HEESI 2024) | Neraca energi batubara (Tabel 6.1.2: Produksi, Ekspor, Impor, Konsumsi Domestik 2014-2024 Hal. 77) dan cadangan batubara per provinsi (Tabel 6.1.1 Hal. 76). | 34 baris |
| 5 | **Direktori Izin Usaha Pertambangan Multi-Komoditas** | `CSV` | MoDI (Minerba One Data Indonesia) ESDM | 4,152 IUP aktif nasional, diperoleh melalui scraping data direktori web MoDI ESDM karena portal resmi tidak menyediakan unduh massal. | 4,152 baris |

---

## 4. PERANCANGAN ARSITEKTUR INTEGRASI & SKEMA DATA WAREHOUSE

Struktur basis data relasional terpadu dirancang menggunakan model bintang (*star-like schema*) di dalam SQLite (`data/processed/unified_mining.db`):

### 4.1 Tabel Dimensi
1. **`dim_provinsi`**: Master referensi wilayah administratif provinsi di Indonesia (38 provinsi).
2. **`dim_komoditas`**: Master klasifikasi jenis bahan galian dan tambang (21 jenis komoditas: Batubara, Nikel, Emas, Tembaga, Bauksit, dll.).

### 4.2 Tabel Fakta
1. **`fact_ekspor_batubara`**: Menyimpan metrik ekspor tahunan per negara mitra dagang dengan atribut `volume_ribu_ton` dan `nilai_fob_juta_usd`.
2. **`fact_operasional_kaltim`**: Menyimpan metrik operasional daerah dengan standarisasi atribut `indikator`, `tahun`, `nilai`, dan `satuan`.
3. **`fact_lelang_wiup`**: Menyimpan data spasial dan finansial lelang blok tambang (`kdi_rupiah`, `luas_ha`, `latitude`, `longitude`, `tahapan`).
4. **`fact_pasokan_batubara_nasional`**: Menyimpan neraca energi primer batubara Indonesia (`produksi_ton`, `ekspor_ton`, `impor_ton`, `konsumsi_domestik_ton`).
5. **`fact_cadangan_batubara_provinsi`**: Menyimpan data geologi cadangan terbukti dan sumber daya per provinsi (`sumberdaya_juta_ton`, `cadangan_juta_ton`).
6. **`fact_izin_tambang`**: Menyimpan data granular konsesi pertambangan nasional (`nama_perusahaan`, `sk_iup`, `luas_sk_ha`, `cnc`, `komoditas`).

### 4.3 Tabel Audit & Keamanan
1. **`etl_audit_log`**: Mencatat metadata eksekusi pipeline ETL (waktu eksekusi, format sumber, nama tabel target, jumlah record yang diekstrak dan dimuat, status eksekusi).
2. **`auth_users`**: Menyimpan kredensial pengguna terenkripsi SHA-256 untuk mekanisme otentikasi login dashboard.

---

## 5. IMPLEMENTASI PIPELINE ETL (EXTRACT, TRANSFORM, LOAD)

Pipeline ETL diimplementasikan dalam Python menggunakan toolchain Astral `uv`:

### 5.1 Tahap Ekstraksi (Extract)
* **Ekstraktor CSV BPS (`extract_coal_exports`):** Menangani struktur berkas laporan BPS yang memiliki dua tabel independen dalam satu sheet (Tabel Volume baris 4-14 dan Tabel Nilai FOB baris 18-28).
* **Ekstraktor XLSX Kaltim (`extract_kaltim_operations`):** Menggunakan `openpyxl` untuk mengekstrak data operasional serta mengabaikan sel berformula mentah (seperti `=SUM(G4:G5)`).
* **Ekstraktor JSON Minerba (`extract_wiup_auctions`):** Melakukan parsing terhadap hierarki objek lelang hasil scraping API portal `minerba.esdm.go.id/lelang/`, menangkap koordinat geospasial `lat` dan `long` untuk kebutuhan visualisasi pemetaan.
* **Ekstraktor PDF HEESI (`extract_heesi_pdf`):** Menggunakan pustaka `pdfplumber` untuk mendeteksi batas koordinat tabel di halaman 76 (Tabel 6.1.1 Cadangan Batubara) dan halaman 77 (Tabel 6.1.2 Pasokan Batubara 2014-2024) dari buku resmi HEESI 2024.
* **Ekstraktor CSV MoDI (`extract_modi_licenses`):** Melakukan streaming dan parsing terhadap 4,152 baris perizinan tambang hasil scraping direktori web MoDI ESDM.

### 5.2 Tahap Transformasi & Pembersihan (Transform & Cleansing)
1. **Penanganan Nilai Hilang dan Karakter Khusus:** Data BPS sering kali menggunakan karakter strip panjang (`─`) atau tanda minus (`-`) untuk merepresentasikan ketiadaan data/ekspor nol. Modul ETL mengubah karakter tersebut menjadi angka numerik `0.0` melalui fungsi `clean_num`.
2. **Unpivoting / Melting:** Mengubah struktur data dari format matriks lebar (*wide format*, tahun sebagai kolom) menjadi format relasional panjang (*long/tidy format*, kolom `tahun` dan `nilai`).
3. **Standarisasi Satuan:** Menyelaraskan konversi satuan ke dalam metrik standar (Ribu Ton, Juta USD, Ton, Ha, MMBTU, dan Barel).
4. **Harmonisasi Nilai Dimensi:** Melakukan pembersihan string (*trimming*, *uppercase*) pada nama provinsi dan kategori komoditas.

### 5.3 Tahap Pemuatan (Load)
Data yang telah divalidasi dimuat ke dalam `unified_mining.db` melalui transaksi basis data SQLite. Setiap tahapan dicatat secara atomik ke dalam tabel `etl_audit_log`.

---

## 6. ANALISIS INSIGHT & TEMUAN KUNCI DARI VISUALISASI DATA

Melalui dashboard EVD (*Exploratory Visual Dashboard*), diperoleh temuan-temuan strategis sebagai berikut:

### Insight 1: Dinamika dan Konsentrasi Ekspor Batubara Indonesia
* **Dominasi Mitra Dagang Utama:** India dan Tiongkok (China) secara konsisten menjadi tujuan utama ekspor batubara Indonesia. Pada tahun 2024, volume ekspor ke India mencapai **108,068 ribu ton** dan Tiongkok mencapai **93,164 ribu ton**. Kedua negara ini menyerap lebih dari 55% total volume ekspor batubara nasional.
* **Fluktuasi Nilai Devisa (Windfall Profit 2022):** Meskipun volume ekspor pada tahun 2022 (110.1 juta ton ke India) relatif mirip dengan tahun 2023-2024, nilai devisa ekspor (FOB Value) melonjak signifikan hingga puncaknya pada tahun 2022 akibat krisis energi global dan disrupsi rantai pasok geopolitik.

### Insight 2: Rasio Pasokan Nasional vs Ekspor Batubara
* Berdasarkan ekstraksi tabel HEESI 2024 PDF, produksi batubara nasional melonjak dari **458.1 juta ton (2014)** menjadi rekor puncak **836.1 juta ton (2024)**, atau meningkat sebesar **82.5%** dalam satu dekade terakhir.
* Porsi ekspor terus mendominasi alokasi batubara nasional (rata-rata 65-75% dari total produksi, mencapai rekor **555.3 juta ton pada 2024**), sementara konsumsi domestik (*Domestic Market Obligation* / DMO) untuk pembangkit listrik PLN dan smelter domestik mencapai **301.7 juta ton pada 2024**.

### Insight 3: Peran Vital Kalimantan Timur dan Komitmen Lingkungan
* Data ESDM Kaltim menunjukkan Kaltim memproduksi lebih dari **287 juta ton batubara pada 2025**, dengan porsi konsesi PKP2B (161 juta ton) dan IUP Daerah (126 juta ton).
* Di sisi keberlanjutan lingkungan, rata-rata realisasi reklamasi lahan bekas tambang di Kaltim mencapai **10,869.5 Ha**, dengan tingkat rehabilitasi mencapai **39% dari total lahan terganggu**. Pemerintah daerah juga secara aktif menertibkan area penambangan liar (PETI) seluas **75.5 Ha**.

### Insight 4: Sebaran Geospasial Blok Lelang Strategis (WIUP)
* Hasil pemetaan geospasial 40 blok lelang WIUP menunjukkan pergeseran fokus eksplorasi ke kawasan Indonesia Timur, khususnya **Sulawesi Selatan, Sulawesi Tengah, Maluku, dan Maluku Utara**.
* Komoditas strategis nikel dan emas mendominasi nilai Kompensasi Data Informasi (KDI), seperti Blok Pumlanga (Maluku Utara - Nikel, KDI Rp 13.3 Miliar) dan Blok Gunung Botak (Maluku - Emas, KDI Rp 37.2 Miliar).

### Insight 5: Lanskap Perizinan Tambang Multi-Komoditas Nasional
* Dari 4,152 izin usaha pertambangan (IUP) yang tercatat di MoDI ESDM, sektor mineral bukan logam / batuan menempati urutan izin terbanyak, disusul batubara dan nikel.
* Provinsi dengan konsentrasi izin konsesi terbesar meliputi **Kalimantan Tengah, Kalimantan Timur, Sulawesi Tengah, dan Jawa Timur**.

---

## 7. FITUR APLIKASI DASHBOARD & PANDUAN PENGGUNAAN

### 7.1 Arsitektur Antarmuka Web & Fitur Utama

Aplikasi web dirancang dengan arsitektur **Multi-Page Routing** yang memisahkan akses publik dan ruang kerja analitik terproteksi:

1. **Portal Publik / Landing Page (`/`):**
   * **Executive Teaser & Status Integrasi:** Menampilkan ringkasan metrik makro (produksi nasional 836.1 juta ton, ekspor 555.3 juta ton, 4,152 IUP, dan 40 blok lelang) serta status kesiapan basis data SQLite.
   * **Kartu Interaktif 5 Dataset Sumber:** Dilengkapi animasi interaktif hover-lift dan tautan langsung (*direct outbound links*) ke portal data resmi penerbit (BPS, Dinas ESDM Kaltim CKAN, Ditjen Minerba Lelang, HEESI ESDM, dan MoDI ESDM) untuk transparansi lineage data.
   * **Modal Login Terautentikasi:** Form otentikasi akun Administrator (`admin` / `admin123`) berbasis modal popup yang mengamankan rute internal.

2. **Exploratory Visual Dashboard (EVD) Terproteksi (`/dashboard`):**
   * **Route Guard & Manajemen Sesi:** Memvalidasi keberadaan token sesi aktif sebelum merender antarmuka dashboard. Akses tanpa login secara otomatis dialihkan kembali ke landing page.
   * **Executive Overview (Ringkasan KPI):** Kartu ringkasan metrik instan, grafik neraca pasokan batubara (PDF), dan grafik cadangan batubara per provinsi (PDF).
   * **Global Trade Analytics:** Visualisasi time-series interaktif volume dan nilai FOB ekspor 2012-2024 dengan filter dinamis negara tujuan (BPS CSV).
   * **Regional Mining Operations:** Analisis komparasi produksi batubara PKP2B vs IUP serta metrik reklamasi lingkungan Kaltim (ESDM XLSX).
   * **Interactive Geospatial Map (Leaflet.js):** Peta sebaran blok lelang WIUP di seluruh nusantara dengan visualisasi marker titik koordinat, klasifikasi warna status lelang, dan popup informasi KDI (Minerba JSON).
   * **Master Directory IUP:** Tabel interaktif data 4,152 IUP dengan pencarian real-time, filter komoditas/provinsi, serta pagination dinamis (MoDI CSV).
   * **EAI Lineage & Audit Viewer:** Tabel pembuktian integrasi data yang menampilkan riwayat dan status setiap proses ETL secara transparan dari tabel `etl_audit_log`.

### 7.2 Panduan Menjalankan Aplikasi
Aplikasi dikembangkan menggunakan Python 3.12 dengan Astral `uv`.

```bash
# 1. Masuk ke direktori proyek
cd /home/primarizki/project/iak-dashboard

# 2. Sinkronisasi dependensi virtualenv
uv sync

# 3. Jalankan pipeline ETL (jika basis data belum dimuat)
uv run python3 src/iak_dashboard/etl/pipeline.py

# 4. Jalankan server aplikasi dashboard
uv run iak-dashboard
```

Aplikasi dapat diakses langsung melalui peramban web pada alamat:
`http://127.0.0.1:8000`

**Kredensial Login Pengujian:**
* Administrator: `admin` / `admin123`

---

## 8. KESIMPULAN & REKOMENDASI

1. **Efektivitas Data-Level EAI:** Pendekatan Data-Level EAI terbukti mampu menjembatani heterogenitas format (CSV, XLSX, JSON, PDF) dari berbagai instansi tanpa memerlukan modifikasi pada sistem sumber.
2. **Keandalan Arsitektur:** Pembuatan skema terpadu (*Unified Storage*) di SQLite dengan dimensi terharmonisasi mempermudah agregasi lintas-analitik (misalnya membandingkan cadangan geologi PDF dengan realisasi ekspor CSV dan perizinan MoDI).
3. **Rekomendasi Pengembangan:** Untuk implementasi produksi korporat skala penuh di masa mendatang, pipeline ETL dapat diintegrasikan dengan orkestrator workflow otomatis (seperti Apache Airflow atau Prefect) dengan koneksi CDC (*Change Data Capture*) langsung ke sistem basis data ESDM dan BPS.
