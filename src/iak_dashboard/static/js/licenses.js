/**
 * Modul Master Direktori IUP Pertambangan (MoDI CSV - 4,152 Izin)
 */

let licenseCurrentOffset = 0;
const licenseLimit = 50;
let chartIupCommInst = null;
let chartIupProvInst = null;

async function loadLicenseFilterOptions() {
  try {
    const res = await fetch('/api/mining/licenses?limit=1');
    const data = await res.json();

    const provSelect = document.getElementById('licenseProvFilter');
    if (provSelect && provSelect.children.length === 1 && data.top_provinsi) {
      data.top_provinsi.forEach(p => {
        const opt = document.createElement('option');
        opt.value = p.nama_provinsi;
        opt.textContent = `${p.nama_provinsi} (${p.count})`;
        provSelect.appendChild(opt);
      });
    }

    const commSelect = document.getElementById('licenseCommFilter');
    if (commSelect && commSelect.children.length === 1 && data.top_komoditas) {
      data.top_komoditas.forEach(c => {
        const opt = document.createElement('option');
        opt.value = c.komoditas;
        opt.textContent = `${c.komoditas} (${c.count})`;
        commSelect.appendChild(opt);
      });
    }
  } catch (e) {
    console.error('Error memuat filter perizinan:', e);
  }
}

async function loadLicensesData(offset = 0) {
  licenseCurrentOffset = offset;
  const provEl = document.getElementById('licenseProvFilter');
  const commEl = document.getElementById('licenseCommFilter');
  const prov = provEl ? provEl.value : '';
  const comm = commEl ? commEl.value : '';

  let url = `/api/mining/licenses?limit=${licenseLimit}&offset=${offset}`;
  if (prov) url += `&provinsi=${encodeURIComponent(prov)}`;
  if (comm) url += `&komoditas=${encodeURIComponent(comm)}`;

  try {
    const res = await fetch(url);
    const data = await res.json();

    // Render tabel data IUP
    const tbody = document.getElementById('licenseTableBody');
    if (tbody) {
      tbody.innerHTML = '';
      data.data.forEach(item => {
        const tr = document.createElement('tr');
        tr.className = 'hover:bg-slate-50';
        tr.innerHTML = `
          <td class="py-2.5 px-3 font-medium text-slate-800">${item.nama_perusahaan}</td>
          <td class="py-2.5 px-2 text-slate-500 font-mono">${item.badan_usaha}</td>
          <td class="py-2.5 px-3">${item.nama_provinsi}</td>
          <td class="py-2.5 px-3">${item.nama_kabupaten}</td>
          <td class="py-2.5 px-3"><span class="px-2 py-0.5 rounded bg-slate-100 text-slate-800">${item.komoditas}</span></td>
          <td class="py-2.5 px-2 text-slate-600">${item.kegiatan}</td>
          <td class="py-2.5 px-3 text-right font-mono">${Number(item.luas_sk_ha).toLocaleString()}</td>
          <td class="py-2.5 px-2"><span class="text-xs px-1.5 py-0.5 rounded ${item.cnc.includes('CNC') ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-600'}">${item.cnc}</span></td>
        `;
        tbody.appendChild(tr);
      });
    }

    // Informasi & Tombol Navigasi Pagination
    const start = offset + 1;
    const end = Math.min(offset + licenseLimit, data.total);
    const pageInfo = document.getElementById('licensePageInfo');
    const prevBtn = document.getElementById('licensePrevBtn');
    const nextBtn = document.getElementById('licenseNextBtn');

    if (pageInfo) {
      pageInfo.textContent = `Menampilkan ${start} - ${end} dari ${data.total.toLocaleString()} izin tambang`;
    }
    if (prevBtn) prevBtn.disabled = offset <= 0;
    if (nextBtn) nextBtn.disabled = end >= data.total;

    // Inisialisasi Chart Agregasi Komoditas & Provinsi pada pemuatan awal
    if (!chartIupCommInst && data.top_komoditas) {
      const canvasComm = document.getElementById('chartIupCommodity');
      if (canvasComm) {
        const ctxComm = canvasComm.getContext('2d');
        chartIupCommInst = new Chart(ctxComm, {
          type: 'doughnut',
          data: {
            labels: data.top_komoditas.map(c => c.komoditas),
            datasets: [{
              data: data.top_komoditas.map(c => c.count),
              backgroundColor: ['#d97706', '#0284c7', '#059669', '#7c3aed', '#dc2626', '#475569', '#ea580c', '#0891b2', '#65a30d', '#db2777']
            }]
          },
          options: { responsive: true, maintainAspectRatio: false }
        });
      }

      const canvasProv = document.getElementById('chartIupProvince');
      if (canvasProv) {
        const ctxProv = canvasProv.getContext('2d');
        chartIupProvInst = new Chart(ctxProv, {
          type: 'bar',
          data: {
            labels: data.top_provinsi.map(p => p.nama_provinsi),
            datasets: [{
              label: 'Jumlah Izin (IUP)',
              data: data.top_provinsi.map(p => p.count),
              backgroundColor: '#0284c7'
            }]
          },
          options: { responsive: true, maintainAspectRatio: false, indexAxis: 'y' }
        });
      }
    }
  } catch (e) {
    console.error('Error memuat data izin tambang:', e);
  }
}

function prevLicensePage() {
  if (licenseCurrentOffset >= licenseLimit) {
    loadLicensesData(licenseCurrentOffset - licenseLimit);
  }
}

function nextLicensePage() {
  loadLicensesData(licenseCurrentOffset + licenseLimit);
}

function resetLicenseFilters() {
  const provEl = document.getElementById('licenseProvFilter');
  const commEl = document.getElementById('licenseCommFilter');
  if (provEl) provEl.value = '';
  if (commEl) commEl.value = '';
  loadLicensesData(0);
}
