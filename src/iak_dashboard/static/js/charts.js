/**
 * Modul Chart.js: Neraca Batubara (PDF), Ekspor Global (CSV), & Operasional Kaltim (XLSX)
 */

let chartSupplyInst = null;
let chartReservesInst = null;
let chartExportsInst = null;
let chartKaltimCoalInst = null;
let chartKaltimOilGasInst = null;

// 1. Ringkasan KPI Utama (Unified SQLite)
async function loadSummaryData() {
  try {
    const res = await fetch('/api/mining/summary');
    if (!res.ok) throw new Error('Gagal memuat ringkasan KPI');
    const data = await res.json();

    const elIzin = document.getElementById('kpi-total-izin');
    const elEkspor = document.getElementById('kpi-ekspor-nilai');
    const elProd = document.getElementById('kpi-prod-batubara');
    const elWiup = document.getElementById('kpi-lelang-wiup');

    if (elIzin) elIzin.textContent = Number(data.total_izin_tambang).toLocaleString();
    if (elEkspor) elEkspor.textContent = `US$ ${(data.nilai_ekspor_terkini_juta_usd / 1000).toFixed(1)} M`;
    if (elProd) elProd.textContent = `${(data.produksi_batubara_puncak_ton / 1e6).toFixed(1)} Jt Ton`;
    if (elWiup) elWiup.textContent = `${data.total_blok_lelang_wiup} Blok`;
  } catch (e) {
    console.error('Error memuat KPI:', e);
  }
}

// 2. Neraca Pasokan & Cadangan Batubara (ESDM HEESI PDF)
async function loadSupplyAndReserves() {
  try {
    // Pasokan Nasional
    const res1 = await fetch('/api/mining/supply');
    const sData = await res1.json();
    const years = sData.data.map(d => d.tahun);
    const prod = sData.data.map(d => d.produksi_ton / 1e6);
    const exp = sData.data.map(d => d.ekspor_ton / 1e6);
    const dom = sData.data.map(d => d.konsumsi_domestik_ton / 1e6);

    const canvasSupply = document.getElementById('chartSupply');
    if (canvasSupply) {
      const ctx1 = canvasSupply.getContext('2d');
      if (chartSupplyInst) chartSupplyInst.destroy();
      chartSupplyInst = new Chart(ctx1, {
        type: 'bar',
        data: {
          labels: years,
          datasets: [
            { label: 'Produksi (Juta Ton)', data: prod, backgroundColor: '#d97706' },
            { label: 'Ekspor (Juta Ton)', data: exp, backgroundColor: '#0284c7' },
            { label: 'Domestik (Juta Ton)', data: dom, backgroundColor: '#059669' }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: { y: { beginAtZero: true } }
        }
      });
    }

    // Cadangan per Provinsi
    const res2 = await fetch('/api/mining/reserves');
    const rData = await res2.json();
    const provs = rData.data.map(d => d.provinsi);
    const reserves = rData.data.map(d => d.cadangan_juta_ton);

    const canvasReserves = document.getElementById('chartReserves');
    if (canvasReserves) {
      const ctx2 = canvasReserves.getContext('2d');
      if (chartReservesInst) chartReservesInst.destroy();
      chartReservesInst = new Chart(ctx2, {
        type: 'bar',
        data: {
          labels: provs,
          datasets: [{ label: 'Cadangan Batubara (Juta Ton)', data: reserves, backgroundColor: '#7c3aed' }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          indexAxis: 'y',
          scales: { x: { beginAtZero: true } }
        }
      });
    }
  } catch (e) {
    console.error('Error memuat neraca pasokan & cadangan:', e);
  }
}

// 3. Ekspor Batubara menurut Negara Tujuan (BPS CSV)
async function loadExportFilterOptions() {
  try {
    const res = await fetch('/api/mining/exports');
    const data = await res.json();
    const select = document.getElementById('exportCountryFilter');
    if (!select || select.children.length > 1) return;

    data.countries.forEach(c => {
      const opt = document.createElement('option');
      opt.value = c;
      opt.textContent = c;
      select.appendChild(opt);
    });
  } catch (e) {
    console.error('Error memuat opsi filter ekspor:', e);
  }
}

async function loadExportData() {
  const filterEl = document.getElementById('exportCountryFilter');
  const country = filterEl ? filterEl.value : '';
  const url = country ? `/api/mining/exports?country=${encodeURIComponent(country)}` : '/api/mining/exports';

  try {
    const res = await fetch(url);
    const d = await res.json();

    // Render tabel destinasi utama
    const tbody = document.getElementById('topDestinationsBody');
    if (tbody) {
      tbody.innerHTML = '';
      d.top_destinations.forEach(row => {
        const tr = document.createElement('tr');
        tr.className = 'hover:bg-slate-50';
        tr.innerHTML = `
          <td class="py-2 px-2 font-medium text-slate-800">${row.negara_tujuan}</td>
          <td class="py-2 px-2 text-right">${Number(row.tot_vol.toFixed(1)).toLocaleString()}</td>
          <td class="py-2 px-2 text-right">${Number(row.tot_val.toFixed(1)).toLocaleString()}</td>
        `;
        tbody.appendChild(tr);
      });
    }

    // Kelompokkan data tahunan untuk line chart
    const yearMap = {};
    d.data.forEach(r => {
      if (!yearMap[r.tahun]) yearMap[r.tahun] = { vol: 0, val: 0 };
      yearMap[r.tahun].vol += r.volume_ribu_ton;
      yearMap[r.tahun].val += r.nilai_fob_juta_usd;
    });

    const years = Object.keys(yearMap).sort();
    const volArr = years.map(y => yearMap[y].vol / 1000); // Konversi ke juta ton
    const valArr = years.map(y => yearMap[y].val);

    const canvas = document.getElementById('chartExports');
    if (canvas) {
      const ctx = canvas.getContext('2d');
      if (chartExportsInst) chartExportsInst.destroy();
      chartExportsInst = new Chart(ctx, {
        type: 'line',
        data: {
          labels: years,
          datasets: [
            { label: 'Volume (Juta Ton)', data: volArr, borderColor: '#0284c7', yAxisID: 'y' },
            { label: 'Nilai FOB (Juta US$)', data: valArr, borderColor: '#059669', yAxisID: 'y1' }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            y: { type: 'linear', display: true, position: 'left', title: { display: true, text: 'Juta Ton' } },
            y1: { type: 'linear', display: true, position: 'right', grid: { drawOnChartArea: false }, title: { display: true, text: 'Juta US$' } }
          }
        }
      });
    }
  } catch (e) {
    console.error('Error memuat data ekspor batubara:', e);
  }
}

// 4. Indikator Operasional Kaltim (ESDM Kaltim XLSX)
async function loadKaltimData() {
  try {
    const res = await fetch('/api/mining/kaltim');
    const data = await res.json();

    const years = [2022, 2023, 2024, 2025, 2026];
    const pkp2b = years.map(y => {
      const item = data.data.find(d => d.indikator.includes('PKP2B') && d.tahun === y);
      return item ? item.nilai / 1e6 : 0;
    });
    const iup = years.map(y => {
      const item = data.data.find(d => d.indikator.includes('KP/IUP') && d.tahun === y);
      return item ? item.nilai / 1e6 : 0;
    });

    const canvasCoal = document.getElementById('chartKaltimCoal');
    if (canvasCoal) {
      const ctxCoal = canvasCoal.getContext('2d');
      if (chartKaltimCoalInst) chartKaltimCoalInst.destroy();
      chartKaltimCoalInst = new Chart(ctxCoal, {
        type: 'bar',
        data: {
          labels: years,
          datasets: [
            { label: 'Produksi PKP2B (Juta Ton)', data: pkp2b, backgroundColor: '#b45309' },
            { label: 'Produksi KP/IUP (Juta Ton)', data: iup, backgroundColor: '#f59e0b' }
          ]
        },
        options: { responsive: true, maintainAspectRatio: false }
      });
    }

    const oil = years.map(y => {
      const item = data.data.find(d => d.indikator.includes('Minyak') && d.tahun === y);
      return item ? item.nilai / 1e6 : 0;
    });
    const gas = years.map(y => {
      const item = data.data.find(d => d.indikator.includes('Gas') && d.tahun === y);
      return item ? item.nilai / 1e6 : 0;
    });

    const canvasOilGas = document.getElementById('chartKaltimOilGas');
    if (canvasOilGas) {
      const ctxOilGas = canvasOilGas.getContext('2d');
      if (chartKaltimOilGasInst) chartKaltimOilGasInst.destroy();
      chartKaltimOilGasInst = new Chart(ctxOilGas, {
        type: 'line',
        data: {
          labels: years,
          datasets: [
            { label: 'Lifting Minyak (Juta Barel)', data: oil, borderColor: '#dc2626' },
            { label: 'Lifting Gas (Juta MMBTU)', data: gas, borderColor: '#2563eb' }
          ]
        },
        options: { responsive: true, maintainAspectRatio: false }
      });
    }
  } catch (e) {
    console.error('Error memuat data operasional Kaltim:', e);
  }
}
