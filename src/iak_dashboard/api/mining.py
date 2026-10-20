"""
Endpoint data dashboard. Semua endpoint membaca unified_mining.db dan wajib login.
"""
import csv
import io
from contextlib import closing
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from iak_dashboard.api.auth import get_current_user
from iak_dashboard.etl.schema import get_connection

router = APIRouter(prefix="/api/mining", tags=["Data"], dependencies=[Depends(get_current_user)])


def rows(sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
    with closing(get_connection()) as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def one(sql: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
    r = rows(sql, params)
    return r[0] if r else None


@router.get("/summary")
def summary() -> Dict[str, Any]:
    neraca = rows("SELECT tahun, produksi_ton, ekspor_ton FROM fact_pasokan_batubara_nasional ORDER BY tahun")
    fob = rows("""SELECT tahun, SUM(nilai_fob_juta_usd) AS fob, SUM(volume_ribu_ton) AS vol
                  FROM fact_ekspor_batubara GROUP BY tahun ORDER BY tahun""")
    izin = one("""SELECT COUNT(*) AS total,
                         SUM(k.nama_komoditas = 'Batubara') AS batubara,
                         COUNT(DISTINCT CASE WHEN k.nama_komoditas = 'Batubara' THEN i.provinsi_id END) AS prov_batubara
                  FROM fact_izin_tambang i JOIN dim_komoditas k ON k.id = i.komoditas_id""")
    izin["komoditas"] = one("SELECT COUNT(DISTINCT komoditas_id) AS n FROM fact_izin_tambang")["n"]
    lelang = one("""SELECT COUNT(*) AS blok, SUM(kdi_rupiah) AS kdi,
                           SUM(tahapan LIKE '%Selesai%') AS selesai FROM fact_lelang_wiup""")
    per_komoditas = rows("""SELECT k.nama_komoditas AS komoditas, k.kategori, COUNT(*) AS n
                            FROM fact_izin_tambang i JOIN dim_komoditas k ON k.id = i.komoditas_id
                            GROUP BY k.id ORDER BY n DESC""")
    kaltim = one("""
        SELECT k.tahun, k.nilai / 1e6 AS kaltim_juta_ton, p.produksi_ton / 1e6 AS nasional_juta_ton
        FROM fact_operasional_kaltim k JOIN fact_pasokan_batubara_nasional p ON p.tahun = k.tahun
        WHERE k.indikator LIKE 'Total Produksi Batubara%' AND k.status_periode = 'final'
        ORDER BY k.tahun DESC LIMIT 1""")
    return {"neraca": neraca, "fob": fob, "izin": izin, "lelang": lelang, "per_komoditas": per_komoditas,
            "kaltim": kaltim, "etl": last_run()}


@router.get("/neraca")
def neraca() -> Dict[str, Any]:
    return {"data": rows("""SELECT tahun, produksi_ton, ekspor_ton, impor_ton, konsumsi_domestik_ton
                            FROM fact_pasokan_batubara_nasional ORDER BY tahun""")}


@router.get("/ekspor")
def ekspor() -> Dict[str, Any]:
    tahunan = rows("""SELECT tahun, SUM(volume_ribu_ton) AS volume_ribu_ton,
                             SUM(nilai_fob_juta_usd) AS nilai_fob_juta_usd
                      FROM fact_ekspor_batubara GROUP BY tahun ORDER BY tahun""")
    for r in tahunan:
        r["harga_usd_per_ton"] = r["nilai_fob_juta_usd"] * 1e6 / (r["volume_ribu_ton"] * 1e3)
    negara = rows("""SELECT negara_tujuan, tahun, volume_ribu_ton, nilai_fob_juta_usd
                     FROM fact_ekspor_batubara ORDER BY negara_tujuan, tahun""")
    urutan = [r["negara_tujuan"] for r in rows(
        """SELECT negara_tujuan FROM fact_ekspor_batubara
           WHERE tahun = (SELECT MAX(tahun) FROM fact_ekspor_batubara)
           ORDER BY COALESCE(volume_ribu_ton, 0) DESC""")]
    return {"tahunan": tahunan, "negara": negara, "urutan_negara": urutan}


@router.get("/rekonsiliasi")
def rekonsiliasi() -> Dict[str, Any]:
    """Ekspor menurut HEESI (PDF) dan BPS (CSV) pada tahun yang sama."""
    return {"data": rows("""
        SELECT p.tahun, p.ekspor_ton / 1e6 AS heesi_juta_ton, SUM(e.volume_ribu_ton) / 1e3 AS bps_juta_ton
        FROM fact_pasokan_batubara_nasional p
        JOIN fact_ekspor_batubara e ON e.tahun = p.tahun
        GROUP BY p.tahun ORDER BY p.tahun""")}


@router.get("/wilayah")
def wilayah() -> Dict[str, Any]:
    """Satu baris per provinsi: cadangan (PDF), izin (CSV), lelang (JSON) digabung lewat dim_provinsi."""
    return {"data": rows("""
        SELECT d.nama_provinsi, d.pulau,
               c.cadangan_juta_ton, c.sumberdaya_juta_ton,
               COALESCE(i.total, 0) AS izin_total, COALESCE(i.batubara, 0) AS izin_batubara,
               COALESCE(i.luas_ha, 0) AS luas_izin_ha,
               COALESCE(l.blok, 0) AS blok_lelang, COALESCE(l.kdi, 0) AS kdi_rupiah
        FROM dim_provinsi d
        LEFT JOIN fact_cadangan_batubara_provinsi c ON c.provinsi_id = d.id
        LEFT JOIN (SELECT provinsi_id, COUNT(*) AS total, SUM(luas_sk_ha) AS luas_ha,
                          SUM(k.nama_komoditas = 'Batubara') AS batubara
                   FROM fact_izin_tambang f JOIN dim_komoditas k ON k.id = f.komoditas_id
                   GROUP BY provinsi_id) i ON i.provinsi_id = d.id
        LEFT JOIN (SELECT provinsi_id, COUNT(*) AS blok, SUM(kdi_rupiah) AS kdi
                   FROM fact_lelang_wiup GROUP BY provinsi_id) l ON l.provinsi_id = d.id
        WHERE c.id IS NOT NULL OR i.total IS NOT NULL OR l.blok IS NOT NULL
        ORDER BY COALESCE(c.cadangan_juta_ton, 0) DESC, izin_total DESC""")}


@router.get("/kaltim")
def kaltim() -> Dict[str, Any]:
    data = rows("""SELECT indikator, tahun, nilai, satuan, status_periode
                   FROM fact_operasional_kaltim ORDER BY indikator, tahun""")
    porsi = rows("""
        SELECT k.tahun, k.nilai / 1e6 AS kaltim_juta_ton, p.produksi_ton / 1e6 AS nasional_juta_ton
        FROM fact_operasional_kaltim k
        JOIN fact_pasokan_batubara_nasional p ON p.tahun = k.tahun
        WHERE k.indikator LIKE 'Total Produksi Batubara%' AND k.status_periode = 'final'
        ORDER BY k.tahun""")
    return {"data": data, "porsi_nasional": porsi}


@router.get("/lelang")
def lelang(komoditas: Optional[str] = None, tahapan: Optional[str] = None) -> Dict[str, Any]:
    where, params = ["1=1"], []
    if komoditas:
        where.append("komoditas = ?"); params.append(komoditas)
    if tahapan:
        where.append("tahapan = ?"); params.append(tahapan)
    w = " AND ".join(where)
    return {
        "data": rows(f"""SELECT id_lelang, nama_blok, nama_provinsi, nama_kabupaten, komoditas, komoditas_sumber,
                                kdi_rupiah, luas_ha, tahapan, latitude, longitude, jumlah_peserta
                         FROM fact_lelang_wiup WHERE {w} ORDER BY kdi_rupiah DESC""", tuple(params)),
        "per_komoditas": rows(f"""SELECT komoditas, COUNT(*) AS blok, SUM(kdi_rupiah) AS kdi, SUM(luas_ha) AS luas
                                  FROM fact_lelang_wiup WHERE {w} GROUP BY komoditas ORDER BY kdi DESC""",
                              tuple(params)),
        "opsi_komoditas": [r["komoditas"] for r in rows(
            "SELECT DISTINCT komoditas FROM fact_lelang_wiup ORDER BY komoditas")],
        "opsi_tahapan": [r["tahapan"] for r in rows(
            "SELECT DISTINCT tahapan FROM fact_lelang_wiup ORDER BY tahapan")],
    }


def _izin_filter(provinsi, komoditas, kegiatan, q):
    where, params = ["1=1"], []
    if provinsi:
        where.append("nama_provinsi = ?"); params.append(provinsi)
    if komoditas:
        where.append("komoditas = ?"); params.append(komoditas)
    if kegiatan:
        where.append("kegiatan = ?"); params.append(kegiatan)
    if q:
        where.append("(nama_perusahaan LIKE ? OR nama_kabupaten LIKE ? OR sk_iup LIKE ?)")
        params += [f"%{q}%"] * 3
    return " AND ".join(where), tuple(params)


IZIN_SORT = {"luas": "luas_sk_ha DESC", "nama": "nama_perusahaan ASC", "provinsi": "nama_provinsi, nama_perusahaan"}


@router.get("/izin")
def izin(provinsi: Optional[str] = None, komoditas: Optional[str] = None, kegiatan: Optional[str] = None,
         q: Optional[str] = None, sort: str = "luas",
         limit: int = Query(25, ge=1, le=200), offset: int = Query(0, ge=0)) -> Dict[str, Any]:
    w, p = _izin_filter(provinsi, komoditas, kegiatan, q)
    # Grafik komoditas tidak ikut disaring komoditas, supaya pilihan lain tetap terlihat
    w_kom, p_kom = _izin_filter(provinsi, None, kegiatan, q)
    order = IZIN_SORT.get(sort, IZIN_SORT["luas"])
    return {
        "total": one(f"SELECT COUNT(*) AS n FROM fact_izin_tambang WHERE {w}", p)["n"],
        "data": rows(f"""SELECT nama_perusahaan, badan_usaha, sk_iup, nama_provinsi, nama_kabupaten,
                                komoditas, kegiatan, luas_sk_ha, cnc
                         FROM fact_izin_tambang WHERE {w} ORDER BY {order} LIMIT ? OFFSET ?""",
                     p + (limit, offset)),
        "per_komoditas": rows(f"""SELECT komoditas, COUNT(*) AS n FROM fact_izin_tambang WHERE {w_kom}
                                  GROUP BY komoditas ORDER BY n DESC""", p_kom),
    }


@router.get("/izin.csv")
def izin_csv(provinsi: Optional[str] = None, komoditas: Optional[str] = None,
             kegiatan: Optional[str] = None, q: Optional[str] = None):
    w, p = _izin_filter(provinsi, komoditas, kegiatan, q)
    data = rows(f"""SELECT nama_perusahaan, badan_usaha, sk_iup, nama_provinsi, nama_kabupaten, komoditas,
                           kegiatan, luas_sk_ha, cnc FROM fact_izin_tambang WHERE {w}
                    ORDER BY nama_provinsi, nama_perusahaan""", p)
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(data[0].keys()) if data else ["nama_perusahaan"])
    writer.writeheader()
    writer.writerows(data)
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=izin_tambang.csv"})


@router.get("/dimensi")
def dimensi() -> Dict[str, Any]:
    return {
        "provinsi": rows("""SELECT DISTINCT d.nama_provinsi, d.pulau FROM dim_provinsi d
                            JOIN fact_izin_tambang i ON i.provinsi_id = d.id ORDER BY d.nama_provinsi"""),
        "komoditas": rows("""SELECT DISTINCT k.nama_komoditas, k.kategori FROM dim_komoditas k
                             JOIN fact_izin_tambang i ON i.komoditas_id = k.id ORDER BY k.nama_komoditas"""),
        "kegiatan": [r["kegiatan"] for r in rows("SELECT DISTINCT kegiatan FROM fact_izin_tambang ORDER BY 1")],
    }


def last_run() -> Optional[Dict[str, Any]]:
    run = one("SELECT * FROM etl_run WHERE finished_at IS NOT NULL ORDER BY started_at DESC LIMIT 1")
    if run:
        run["sumber"] = one("""SELECT COUNT(*) AS n, SUM(status = 'FAILED') AS gagal,
                                      SUM(records_rejected) AS ditolak
                               FROM etl_audit_log WHERE run_id = ?""", (run["run_id"],))
    return run


@router.get("/pipeline")
def pipeline() -> Dict[str, Any]:
    run = last_run()
    rid = run["run_id"] if run else ""
    return {
        "run": run,
        "audit": rows("SELECT * FROM etl_audit_log WHERE run_id = ? ORDER BY id", (rid,)),
        "cek": rows("SELECT target_table, rule, result, affected_rows, detail FROM etl_quality_check "
                    "WHERE run_id = ? ORDER BY id", (rid,)),
        "riwayat": rows("""SELECT r.run_id, r.started_at, r.status,
                                  (SELECT SUM(records_loaded) FROM etl_audit_log a WHERE a.run_id = r.run_id) AS baris
                           FROM etl_run r ORDER BY r.started_at DESC LIMIT 8"""),
    }
