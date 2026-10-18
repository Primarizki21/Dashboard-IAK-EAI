"""
Endpoint REST API untuk agregasi dan analitik data pertambangan terintegrasi (Data-Level EAI).
"""
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Query
from iak_dashboard.etl.schema import get_connection

router = APIRouter(prefix="/api/mining", tags=["Mining Analytics"])

@router.get("/summary")
def get_summary() -> Dict[str, Any]:
    """
    Ringkasan KPI utama sektor pertambangan Indonesia hasil integrasi 5 dataset.
    """
    conn = get_connection()
    c = conn.cursor()

    total_licenses = c.execute("SELECT COUNT(*) FROM fact_izin_tambang").fetchone()[0]
    total_coal_prod = c.execute("SELECT MAX(produksi_ton) FROM fact_pasokan_batubara_nasional").fetchone()[0] or 0
    total_export_val_latest = c.execute("SELECT SUM(nilai_fob_juta_usd) FROM fact_ekspor_batubara WHERE tahun = (SELECT MAX(tahun) FROM fact_ekspor_batubara)").fetchone()[0] or 0
    total_export_vol_latest = c.execute("SELECT SUM(volume_ribu_ton) FROM fact_ekspor_batubara WHERE tahun = (SELECT MAX(tahun) FROM fact_ekspor_batubara)").fetchone()[0] or 0
    total_auctions = c.execute("SELECT COUNT(*) FROM fact_lelang_wiup").fetchone()[0]
    total_kdi = c.execute("SELECT SUM(kdi_rupiah) FROM fact_lelang_wiup").fetchone()[0] or 0
    total_provinces = c.execute("SELECT COUNT(*) FROM dim_provinsi").fetchone()[0]
    total_commodities = c.execute("SELECT COUNT(*) FROM dim_komoditas").fetchone()[0]

    conn.close()
    return {
        "total_izin_tambang": total_licenses,
        "produksi_batubara_puncak_ton": total_coal_prod,
        "nilai_ekspor_terkini_juta_usd": round(total_export_val_latest, 2),
        "volume_ekspor_terkini_ribu_ton": round(total_export_vol_latest, 2),
        "total_blok_lelang_wiup": total_auctions,
        "total_nilai_kdi_rupiah": total_kdi,
        "jumlah_provinsi_terdata": total_provinces,
        "jumlah_komoditas_terdata": total_commodities,
    }

@router.get("/exports")
def get_exports(country: Optional[str] = None) -> Dict[str, Any]:
    """
    Data ekspor batubara menurut negara tujuan (2012–2024) - BPS CSV.
    """
    conn = get_connection()
    c = conn.cursor()

    countries = [r[0] for r in c.execute("SELECT DISTINCT negara_tujuan FROM fact_ekspor_batubara ORDER BY negara_tujuan").fetchall()]

    query = "SELECT negara_tujuan, tahun, volume_ribu_ton, nilai_fob_juta_usd FROM fact_ekspor_batubara"
    params = []
    if country:
        query += " WHERE negara_tujuan = ?"
        params.append(country)
    query += " ORDER BY tahun ASC, volume_ribu_ton DESC"

    rows = c.execute(query, params).fetchall()

    # Top destination ranking by total volume
    top_rank = c.execute("""
        SELECT negara_tujuan, SUM(volume_ribu_ton) as tot_vol, SUM(nilai_fob_juta_usd) as tot_val
        FROM fact_ekspor_batubara
        GROUP BY negara_tujuan
        ORDER BY tot_vol DESC
    """).fetchall()

    conn.close()
    return {
        "countries": countries,
        "data": [dict(r) for r in rows],
        "top_destinations": [dict(r) for r in top_rank],
    }

@router.get("/kaltim")
def get_kaltim() -> Dict[str, Any]:
    """
    Indikator operasional pertambangan Provinsi Kalimantan Timur (2022–2026) - ESDM Kaltim XLSX.
    """
    conn = get_connection()
    c = conn.cursor()

    rows = c.execute("""
        SELECT indikator, tahun, nilai, satuan 
        FROM fact_operasional_kaltim 
        ORDER BY indikator, tahun
    """).fetchall()

    indicators = [r[0] for r in c.execute("SELECT DISTINCT indikator FROM fact_operasional_kaltim ORDER BY indikator").fetchall()]

    conn.close()
    return {
        "indicators": indicators,
        "data": [dict(r) for r in rows],
    }

@router.get("/auctions")
def get_auctions(komoditas: Optional[str] = None, tahapan: Optional[str] = None) -> Dict[str, Any]:
    """
    Data blok lelang WIUP Indonesia dengan koordinat geografis (lat, long) - ESDM JSON.
    """
    conn = get_connection()
    c = conn.cursor()

    query = """
        SELECT id_lelang, nomor, nama_blok, nama_provinsi, nama_kabupaten, pulau, 
               komoditas, jenis_izin, kegiatan, kdi_rupiah, luas_ha, tahapan, 
               latitude, longitude, jumlah_peserta
        FROM fact_lelang_wiup
        WHERE 1=1
    """
    params = []
    if komoditas:
        query += " AND komoditas = ?"
        params.append(komoditas)
    if tahapan:
        query += " AND tahapan = ?"
        params.append(tahapan)

    query += " ORDER BY kdi_rupiah DESC"
    rows = c.execute(query, params).fetchall()

    komoditas_list = [r[0] for r in c.execute("SELECT DISTINCT komoditas FROM fact_lelang_wiup WHERE komoditas IS NOT NULL AND komoditas != ''").fetchall()]
    tahapan_list = [r[0] for r in c.execute("SELECT DISTINCT tahapan FROM fact_lelang_wiup WHERE tahapan IS NOT NULL AND tahapan != ''").fetchall()]

    conn.close()
    return {
        "komoditas_filter": komoditas_list,
        "tahapan_filter": tahapan_list,
        "total": len(rows),
        "data": [dict(r) for r in rows],
    }

@router.get("/supply")
def get_supply() -> Dict[str, Any]:
    """
    Neraca pasokan batubara nasional 2011–2021 (Produksi, Ekspor, Impor, Konsumsi Domestik) - HEESI PDF.
    """
    conn = get_connection()
    c = conn.cursor()
    rows = c.execute("SELECT tahun, produksi_ton, ekspor_ton, impor_ton, konsumsi_domestik_ton FROM fact_pasokan_batubara_nasional ORDER BY tahun ASC").fetchall()
    conn.close()
    return {"data": [dict(r) for r in rows]}

@router.get("/reserves")
def get_reserves() -> Dict[str, Any]:
    """
    Cadangan dan sumber daya batubara per provinsi - HEESI PDF.
    """
    conn = get_connection()
    c = conn.cursor()
    rows = c.execute("SELECT provinsi, sumberdaya_juta_ton, cadangan_juta_ton FROM fact_cadangan_batubara_provinsi ORDER BY cadangan_juta_ton DESC").fetchall()
    conn.close()
    return {"data": [dict(r) for r in rows]}

@router.get("/licenses")
def get_licenses(
    provinsi: Optional[str] = None,
    komoditas: Optional[str] = None,
    kegiatan: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> Dict[str, Any]:
    """
    Data izin usaha pertambangan multi-komoditas nasional (4,152 izin) - MoDI CSV.
    """
    conn = get_connection()
    c = conn.cursor()

    where_clauses = ["1=1"]
    params = []
    if provinsi:
        where_clauses.append("nama_provinsi = ?")
        params.append(provinsi)
    if komoditas:
        where_clauses.append("komoditas = ?")
        params.append(komoditas)
    if kegiatan:
        where_clauses.append("kegiatan = ?")
        params.append(kegiatan)

    where_str = " AND ".join(where_clauses)

    count_q = f"SELECT COUNT(*) FROM fact_izin_tambang WHERE {where_str}"
    total = c.execute(count_q, params).fetchone()[0]

    data_q = f"""
        SELECT id, nama_perusahaan, badan_usaha, jenis_izin, sk_iup, 
               nama_provinsi, nama_kabupaten, kegiatan, luas_sk_ha, cnc, komoditas
        FROM fact_izin_tambang
        WHERE {where_str}
        ORDER BY luas_sk_ha DESC
        LIMIT ? OFFSET ?
    """
    data_params = params + [limit, offset]
    rows = c.execute(data_q, data_params).fetchall()

    # Commodity aggregation for chart
    comm_agg = c.execute("""
        SELECT komoditas, COUNT(*) as count, SUM(luas_sk_ha) as total_luas_ha
        FROM fact_izin_tambang
        GROUP BY komoditas
        ORDER BY count DESC
        LIMIT 10
    """).fetchall()

    # Province aggregation
    prov_agg = c.execute("""
        SELECT nama_provinsi, COUNT(*) as count, SUM(luas_sk_ha) as total_luas_ha
        FROM fact_izin_tambang
        WHERE nama_provinsi != '-'
        GROUP BY nama_provinsi
        ORDER BY count DESC
        LIMIT 10
    """).fetchall()

    conn.close()
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "data": [dict(r) for r in rows],
        "top_komoditas": [dict(r) for r in comm_agg],
        "top_provinsi": [dict(r) for r in prov_agg],
    }

@router.get("/audit")
def get_audit_trail() -> Dict[str, Any]:
    """
    Log audit ETL untuk pembuktian lineage data dan integrasi Data-Level EAI.
    """
    conn = get_connection()
    c = conn.cursor()
    rows = c.execute("SELECT id, source_name, source_format, target_table, records_extracted, records_loaded, status, executed_at FROM etl_audit_log ORDER BY id ASC").fetchall()
    conn.close()
    return {"audit_log": [dict(r) for r in rows]}
