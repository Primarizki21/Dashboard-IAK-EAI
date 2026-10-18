/**
 * Modul Peta Geospasial Leaflet: Lelang Blok WIUP Pertambangan (ESDM JSON)
 */

let mapInst = null;
let mapMarkers = [];

function initMap() {
  const mapContainer = document.getElementById('map');
  if (!mapContainer || mapInst) return;

  mapInst = L.map('map').setView([-0.7893, 113.9213], 5);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors'
  }).addTo(mapInst);
}

function refreshMapSize() {
  if (mapInst) {
    setTimeout(() => mapInst.invalidateSize(), 200);
  }
}

async function loadAuctionData() {
  const commSelect = document.getElementById('auctionCommFilter');
  const comm = commSelect ? commSelect.value : '';
  const url = comm ? `/api/mining/auctions?komoditas=${encodeURIComponent(comm)}` : '/api/mining/auctions';

  try {
    const res = await fetch(url);
    const data = await res.json();

    // Isi opsi dropdown filter komoditas lelang jika belum ada
    if (commSelect && commSelect.children.length === 1 && data.komoditas_filter) {
      data.komoditas_filter.forEach(c => {
        const opt = document.createElement('option');
        opt.value = c;
        opt.textContent = c;
        commSelect.appendChild(opt);
      });
    }

    // Bersihkan marker lama
    if (mapInst) {
      mapMarkers.forEach(m => mapInst.removeLayer(m));
      mapMarkers = [];
    }

    // Render tabel data lelang
    const tbody = document.getElementById('auctionTableBody');
    if (tbody) {
      tbody.innerHTML = '';
      data.data.forEach(item => {
        const tr = document.createElement('tr');
        tr.className = 'hover:bg-slate-50';
        tr.innerHTML = `
          <td class="py-2 px-3 font-medium text-slate-800">${item.nama_blok}</td>
          <td class="py-2 px-3">${item.nama_kabupaten}, ${item.nama_provinsi}</td>
          <td class="py-2 px-3"><span class="px-2 py-0.5 rounded bg-amber-50 text-amber-800">${item.komoditas}</span></td>
          <td class="py-2 px-3 text-right font-mono">Rp ${Number(item.kdi_rupiah).toLocaleString()}</td>
          <td class="py-2 px-3 text-right">${Number(item.luas_ha).toLocaleString()}</td>
          <td class="py-2 px-3"><span class="text-xs px-2 py-0.5 rounded ${item.tahapan.includes('Selesai') ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-100 text-slate-700'}">${item.tahapan}</span></td>
        `;
        tbody.appendChild(tr);

        // Tambahkan marker ke peta leaflet jika koordinat tersedia
        if (mapInst && item.latitude && item.longitude) {
          const isCompleted = item.tahapan.includes('Selesai');
          const color = isCompleted
            ? '#059669'
            : (item.tahapan.includes('Batal') || item.tahapan.includes('Gagal') ? '#dc2626' : '#d97706');

          const marker = L.circleMarker([item.latitude, item.longitude], {
            radius: 7,
            fillColor: color,
            color: '#fff',
            weight: 1.5,
            opacity: 1,
            fillOpacity: 0.85
          }).addTo(mapInst);

          marker.bindPopup(`
            <div class="text-xs">
              <p class="font-bold text-slate-900">${item.nama_blok}</p>
              <p class="text-slate-600">${item.nama_kabupaten}, ${item.nama_provinsi}</p>
              <p class="mt-1"><b>Komoditas:</b> ${item.komoditas}</p>
              <p><b>Nilai KDI:</b> Rp ${Number(item.kdi_rupiah).toLocaleString()}</p>
              <p><b>Luas:</b> ${Number(item.luas_ha).toLocaleString()} Ha</p>
              <p><b>Tahapan:</b> ${item.tahapan}</p>
            </div>
          `);
          mapMarkers.push(marker);
        }
      });
    }
  } catch (e) {
    console.error('Error memuat data lelang WIUP:', e);
  }
}
