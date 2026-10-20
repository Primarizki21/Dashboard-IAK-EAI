(window.Pages ||= {}).lelang = {
  title: 'Lelang Lahan Tambang Baru',

  async render(view, params) {
    const base = await Api.get('lelang');
    const state = { komoditas: params.komoditas || '', tahapan: params.tahapan || '' };
    const status = (t) => (t.includes('Selesai') ? ['good', 'Selesai'] : t.includes('Batal') ? ['bad', 'Batal'] : ['retry', 'Gagal/diulang']);

    view.innerHTML = `
      ${H.head('Lelang Lahan Tambang Baru', `Sebelum boleh ditambang, sebuah ${H.term('WIUP', 'wilayah')} dilelang dulu oleh pemerintah. Pemenangnya membayar ${H.term('KDI')} untuk data geologinya.`, '', ['wiup'])}
      <div class="filters">
        ${H.select('fKom', 'Komoditas', base.opsi_komoditas, state.komoditas)}
        ${H.select('fTah', 'Tahap lelang', base.opsi_tahapan, state.tahapan)}
      </div>
      <div class="grid">
        ${H.panel({ w: 8, id: 'pPeta', title: '&nbsp;',
          body: `${H.legend([['Selesai', css('--good'), 'dot'], ['Gagal atau diulang', css('--warn'), 'dot'], ['Batal', css('--bad'), 'dot']])}
                 <div id="map" class="map" role="region" aria-label="Peta blok lelang"></div>`, })}
        ${H.panel({ w: 4, id: 'pKdi', title: `Nilai ${H.term('KDI')} per komoditas`, sub: 'miliar rupiah',
          body: '<div class="chart tall"><canvas id="cKdi" role="img" aria-label="Total KDI per komoditas"></canvas></div>' })}
        ${H.panel({ w: 12, id: 'pTabel', title: 'Daftar blok', body: `<div class="table-wrap"><table><thead><tr>
            <th>Blok</th><th>Lokasi</th><th>Komoditas</th><th class="n">Luas<span class="unit">ha</span></th>
            <th class="n">KDI</th><th class="n">Peserta</th><th>Tahap</th></tr></thead><tbody id="tBlok"></tbody></table></div>`, })}
      </div>`;

    const map = L.map('map', { scrollWheelZoom: true }).setView([-2.2, 118], 5);
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap', maxZoom: 12, className: 'tiles-muted',
    }).addTo(map);
    const layer = L.layerGroup().addTo(map);
    const colors = { good: css('--good'), bad: css('--bad'), retry: css('--warn') };

    const draw = async () => {
      const q = new URLSearchParams(Object.entries(state).filter(([, v]) => v)).toString();
      const d = q ? await Api.get(`lelang?${q}`) : base;
      layer.clearLayers();
      const bounds = [];
      d.data.forEach((b) => {
        const [s, sl] = status(b.tahapan);
        const m = L.circleMarker([b.latitude, b.longitude], {
          radius: 4 + Math.min(10, Math.sqrt(b.luas_ha) / 30), color: css('--surface'), weight: 1.5,
          fillColor: colors[s], fillOpacity: 0.85,
        }).bindPopup(`<b>${esc(b.nama_blok)}</b>${esc(b.nama_kabupaten)}, ${esc(b.nama_provinsi)}<br>
          ${esc(b.komoditas)}, ${Fmt.int(b.luas_ha)} ha<br>KDI ${Fmt.rp(b.kdi_rupiah)}, ${b.jumlah_peserta} peserta<br>
          <span class="st ${s}">${sl}</span>`);
        layer.addLayer(m); bounds.push([b.latitude, b.longitude]);
      });
      if (bounds.length) map.fitBounds(bounds, { padding: [30, 30], maxZoom: 7 });
      const done = d.data.filter((b) => b.tahapan.includes('Selesai')).length;
      $('#pPeta h2').textContent = d.data.length
        ? `${d.data.length} blok, ${done} lelang selesai (${Fmt.pct(done / d.data.length, 0)})`
        : 'Tidak ada blok untuk pilihan ini';

      Charts.destroyAll();
      const pk = d.per_komoditas;
      const totalKdi = pk.reduce((s, r) => s + r.kdi, 0);
      barChart($('#cKdi'), {
        horizontal: true, unit: 'miliar Rp', decimals: 1,
        labels: pk.map((r) => `${r.komoditas} (${r.blok})`),
        series: [{ label: 'KDI', data: pk.map((r) => r.kdi / 1e9),
          backgroundColor: pk.map((r) => (!state.komoditas || r.komoditas === state.komoditas ? css('--bar') : css('--bar-muted'))) }],
        onClick: (i) => { state.komoditas = state.komoditas === pk[i].komoditas ? '' : pk[i].komoditas; $('#fKom').value = state.komoditas; draw(); },
      });

      $('#tBlok').innerHTML = d.data.map((b) => {
        const [s, sl] = status(b.tahapan);
        return `<tr><td>${esc(b.nama_blok)}</td><td>${esc(b.nama_kabupaten)}, ${esc(b.nama_provinsi)}</td>
          <td>${esc(b.komoditas)}</td><td class="n">${Fmt.int(b.luas_ha)}</td><td class="n">${Fmt.rp(b.kdi_rupiah)}</td>
          <td class="n">${b.jumlah_peserta}</td><td><span class="st ${s}">${sl}</span></td></tr>`;
      }).join('') || '<tr><td colspan="7" class="empty">Tidak ada data</td></tr>';
    };

    $('#fKom').addEventListener('change', (e) => { state.komoditas = e.target.value; draw(); });
    $('#fTah').addEventListener('change', (e) => { state.tahapan = e.target.value; draw(); });
    await draw();
    setTimeout(() => map.invalidateSize(), 50);
  },
};
