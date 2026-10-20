"""
Membuat satu berkas HTML statis (dist/neraca-tambang.html) untuk dibagikan tanpa server.

Data diambil dari unified_mining.db saat skrip dijalankan lalu disisipkan ke HTML.
Login di versi ini hanya dummy di browser (admin / admin123); tidak ada API.
Jalankan setelah ETL:  python scripts/build_static.py
"""
import json
import re
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from iak_dashboard.api import mining  # noqa: E402
from iak_dashboard.api.app import sekilas  # noqa: E402

STATIC = ROOT / "src" / "iak_dashboard" / "static"
OUT = ROOT / "dist" / "neraca-tambang.html"
PAGES = ["ringkasan", "produksi", "izin", "lelang", "kaltim", "data"]


def collect() -> dict:
    izin_all = mining.rows("""SELECT nama_perusahaan, badan_usaha, sk_iup, nama_provinsi, nama_kabupaten,
                                     komoditas, kegiatan, luas_sk_ha, cnc FROM fact_izin_tambang""")
    return {
        "summary": mining.summary(), "neraca": mining.neraca(), "ekspor": mining.ekspor(),
        "rekonsiliasi": mining.rekonsiliasi(), "wilayah": mining.wilayah(), "kaltim": mining.kaltim(),
        "lelang": mining.lelang(), "dimensi": mining.dimensi(), "pipeline": mining.pipeline(),
        "sekilas": sekilas(), "izin_all": izin_all,
    }


# Pengganti api.js: data dari variabel DATA, penyaringan dilakukan di browser
MOCK_API = r"""
const Auth = {
  token() { try { return sessionStorage.getItem('nt'); } catch { return 'x'; } },
  user() { return 'admin'; },
  async login(u, p) {
    if (u === 'admin' && p === 'admin123') { try { sessionStorage.setItem('nt', 'demo'); } catch {} return; }
    throw new Error('Nama pengguna atau kata sandi salah');
  },
  clear() { try { sessionStorage.removeItem('nt'); } catch {} },
  async logout() { this.clear(); location.hash = ''; location.reload(); },
};

function izinFilter(p, skipKom) {
  const q = (p.q || '').toLowerCase();
  return DATA.izin_all.filter((r) => (!p.provinsi || r.nama_provinsi === p.provinsi)
    && (skipKom || !p.komoditas || r.komoditas === p.komoditas)
    && (!p.kegiatan || r.kegiatan === p.kegiatan)
    && (!q || [r.nama_perusahaan, r.nama_kabupaten, r.sk_iup].some((v) => String(v).toLowerCase().includes(q))));
}
function countBy(arr, key) {
  const m = {}; arr.forEach((r) => { m[r[key]] = (m[r[key]] || 0) + 1; });
  return Object.entries(m).map(([k, n]) => ({ [key]: k, n })).sort((a, b) => b.n - a.n);
}

const Api = {
  async get(path) {
    const [name, qs] = path.split('?');
    const p = Object.fromEntries(new URLSearchParams(qs || ''));
    if (name === 'izin') {
      const rows = izinFilter(p, false);
      const sort = { nama: (a, b) => a.nama_perusahaan.localeCompare(b.nama_perusahaan),
        provinsi: (a, b) => a.nama_provinsi.localeCompare(b.nama_provinsi) }[p.sort] || ((a, b) => b.luas_sk_ha - a.luas_sk_ha);
      const off = +p.offset || 0, lim = +p.limit || 25;
      return { total: rows.length, data: [...rows].sort(sort).slice(off, off + lim), per_komoditas: countBy(izinFilter(p, true), 'komoditas') };
    }
    if (name === 'lelang') {
      const data = DATA.lelang.data.filter((r) => (!p.komoditas || r.komoditas === p.komoditas) && (!p.tahapan || r.tahapan === p.tahapan));
      const m = {};
      data.forEach((r) => { const x = (m[r.komoditas] ||= { komoditas: r.komoditas, blok: 0, kdi: 0, luas: 0 }); x.blok++; x.kdi += r.kdi_rupiah; x.luas += r.luas_ha; });
      return { ...DATA.lelang, data, per_komoditas: Object.values(m).sort((a, b) => b.kdi - a.kdi) };
    }
    return DATA[name];
  },
  async download(path) {
    const p = Object.fromEntries(new URLSearchParams(path.split('?')[1] || ''));
    const rows = izinFilter(p, false), cols = Object.keys(DATA.izin_all[0]);
    const csv = [cols.join(','), ...rows.map((r) => cols.map((c) => `"${String(r[c]).replace(/"/g, '""')}"`).join(','))].join('\n');
    const a = Object.assign(document.createElement('a'), { href: URL.createObjectURL(new Blob([csv], { type: 'text/csv' })), download: 'izin_tambang.csv' });
    document.body.appendChild(a); a.click(); a.remove();
  },
};
"""


def read(rel: str) -> str:
    return (STATIC / rel).read_text(encoding="utf-8")


def main() -> None:
    data = collect()
    login_html = read("login.html")
    dash_html = read("dashboard.html")

    login_markup = re.search(r'(<div class="login">.*?</div>\s*)\n<script', login_html, re.S).group(1)
    login_js = re.findall(r"<script>(.*?)</script>", login_html, re.S)[0]
    login_js = (login_js.replace("if (Auth.token()) location.replace('/dashboard');", "")
                .replace("location.replace('/dashboard');", "location.reload();")
                .replace("fetch('/api/public/sekilas').then((r) => r.json())", "Promise.resolve(DATA.sekilas)"))
    shell = re.search(r'(<header class="topbar">.*?</main>)', dash_html, re.S).group(1)

    app_js = read("js/app.js").replace("if (!Auth.token()) { location.replace('/'); return; }", "if (!Auth.token()) return;")
    scripts = "\n".join([read("js/viz.js")] + [read(f"js/pages/{p}.js") for p in PAGES] + [app_js])
    data_json = json.dumps(data, ensure_ascii=False, default=str).replace("</", "<\\/")

    html = f"""<!doctype html>
<html lang="id">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Neraca Tambang</title>
<script>try {{ if (sessionStorage.getItem('nt')) document.documentElement.classList.add('authed'); }} catch (e) {{}}</script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&family=Source+Serif+4:opsz,wght@8..60,600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<style>
{read("css/app.css")}
html.authed .login {{ display: none; }}
html:not(.authed) .topbar, html:not(.authed) #view {{ display: none; }}
</style>
</head>
<body>
{login_markup}
{shell}
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>const DATA = {data_json};</script>
<script>{MOCK_API}</script>
<script>{login_js}</script>
<script>{scripts}</script>
</body>
</html>
"""
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(html, encoding="utf-8")
    print(f"Tersimpan: {OUT} ({OUT.stat().st_size / 1024:,.0f} KB)")


if __name__ == "__main__":
    main()
