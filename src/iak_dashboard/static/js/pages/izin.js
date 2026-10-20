(window.Pages ||= {}).izin = {
  title: 'Izin Tambang per Provinsi',

  async render(view, params) {
    const [wil, dim] = await Promise.all([Api.get('wilayah'), Api.get('dimensi')]);
    const LIMIT = 20;
    const prov = wil.data.filter((w) => w.izin_total || w.cadangan_juta_ton).map((w) => ({
      ...w, rasio: w.cadangan_juta_ton && w.izin_batubara ? w.cadangan_juta_ton / w.izin_batubara : null,
    }));
    const st = {
      sort: 'izin_total', dir: 'desc', all: false,
      q: params.q || '', provinsi: params.provinsi || '', komoditas: params.komoditas || '', kegiatan: params.kegiatan || '',
      order: 'luas', offset: 0,
    };

    view.innerHTML = `
      ${H.head('Izin Tambang per Provinsi',
        `${Fmt.int(prov.reduce((s, w) => s + w.izin_total, 0))} izin usaha tambang di ${prov.filter((w) => w.izin_total).length} provinsi, dari nikel sampai pasir.`,
        '', ['modi', 'heesi'])}
      <div class="grid">
        ${H.panel({ w: 12, id: 'pProv', title: '&nbsp;',
          body: `<div class="table-wrap"><table><thead><tr>
              <th class="sortable" data-k="nama_provinsi">Provinsi</th>
              <th class="sortable" data-k="pulau">Pulau</th>
              <th class="sortable n" data-k="izin_total">Semua izin</th>
              <th class="sortable n" data-k="izin_batubara">Izin batubara</th>
              <th class="sortable" data-k="cadangan_juta_ton">Cadangan batubara<span class="unit">juta ton</span></th>
              <th class="sortable n" data-k="rasio">Cadangan per izin batubara<span class="unit">juta ton</span></th>
            </tr></thead><tbody id="tProv"></tbody></table></div>
            <button class="btn" id="bAll" type="button" style="margin-top:12px"></button>` })}
      </div>

      <h2 class="section" id="daftar">Daftar izin</h2>
      <div class="filters">
        <label class="field">Cari<input type="search" id="fQ" placeholder="Perusahaan, kabupaten, atau nomor SK" value="${esc(st.q)}"></label>
        ${H.select('fProv', 'Provinsi', dim.provinsi.map((p) => p.nama_provinsi), st.provinsi)}
        ${H.select('fKom', 'Komoditas', dim.komoditas.map((k) => k.nama_komoditas), st.komoditas)}
        ${H.select('fKeg', 'Tahap', dim.kegiatan, st.kegiatan)}
        <button class="btn" id="bReset" type="button">Hapus filter</button>
        <button class="btn" id="bCsv" type="button">Unduh CSV</button>
      </div>
      <div class="grid">
        ${H.panel({ w: 4, id: 'pKom', title: '&nbsp;',
          body: '<div class="chart tall"><canvas id="cKom" role="img" aria-label="Jumlah izin per komoditas"></canvas></div>' })}
        ${H.panel({ w: 8, id: 'pTabel', card: true, title: '&nbsp;', body: `<div class="table-wrap"><table><thead><tr>
              <th class="sortable" data-o="nama">Perusahaan</th><th>Lokasi</th><th>Komoditas</th><th>Tahap</th>
              <th class="sortable n" data-o="luas">Luas<span class="unit">ha</span></th></tr></thead>
              <tbody id="tIzin"></tbody></table></div>
              <div class="pager"><span id="pgInfo"></span><div>
                <button class="btn" id="bPrev" type="button">Sebelumnya</button>
                <button class="btn" id="bNext" type="button">Berikutnya</button></div></div>` })}
      </div>`;

    // ---- Tabel provinsi ----
    const maxC = Math.max(...prov.map((w) => w.cadangan_juta_ton || 0));
    const topIzin = [...prov].sort((a, b) => b.izin_total - a.izin_total)[0];
    const topCad = [...prov].sort((a, b) => (b.cadangan_juta_ton || 0) - (a.cadangan_juta_ton || 0))[0];
    $('#pProv h2').textContent = topIzin.nama_provinsi === topCad.nama_provinsi
      ? `${topIzin.nama_provinsi}: izin terbanyak sekaligus cadangan batubara terbesar`
      : `Izin terbanyak di ${topIzin.nama_provinsi} (${Fmt.int(topIzin.izin_total)}), cadangan batubara terbesar di ${topCad.nama_provinsi}`;

    const drawProv = () => {
      view.querySelectorAll('#pProv th.sortable').forEach((th) => {
        if (th.dataset.k === st.sort) th.setAttribute('aria-sort', st.dir === 'asc' ? 'ascending' : 'descending');
        else th.removeAttribute('aria-sort');
      });
      const sorted = [...prov].sort(sorter(st.sort, st.dir));
      const shown = st.all ? sorted : sorted.slice(0, 10);
      $('#tProv').innerHTML = shown.map((w) => `
        <tr class="clickable${w.nama_provinsi === st.provinsi ? ' selected' : ''}" data-prov="${esc(w.nama_provinsi)}">
          <td>${esc(w.nama_provinsi)}</td><td class="muted">${esc(w.pulau)}</td>
          <td class="n">${Fmt.int(w.izin_total)}</td><td class="n">${w.izin_batubara || '–'}</td>
          <td>${w.cadangan_juta_ton ? H.barnum(w.cadangan_juta_ton / maxC, Fmt.int(w.cadangan_juta_ton)) : '<span class="muted">–</span>'}</td>
          <td class="n">${Fmt.n(w.rasio)}</td></tr>`).join('');
      $('#bAll').textContent = st.all ? 'Tampilkan 10 teratas' : `Tampilkan semua (${prov.length} provinsi)`;
    };
    view.querySelector('#pProv thead').addEventListener('click', (e) => {
      const th = e.target.closest('th.sortable'); if (!th) return;
      st.dir = st.sort === th.dataset.k && st.dir === 'desc' ? 'asc' : 'desc'; st.sort = th.dataset.k; drawProv();
    });
    $('#bAll').addEventListener('click', () => { st.all = !st.all; drawProv(); });
    $('#tProv').addEventListener('click', (e) => {
      const tr = e.target.closest('tr'); if (!tr) return;
      st.provinsi = st.provinsi === tr.dataset.prov ? '' : tr.dataset.prov;
      $('#fProv').value = st.provinsi; drawProv(); reset();
      $('#daftar').scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
    drawProv();

    // ---- Daftar izin ----
    const query = (extra = {}) => new URLSearchParams(Object.entries({
      q: st.q, provinsi: st.provinsi, komoditas: st.komoditas, kegiatan: st.kegiatan, ...extra,
    }).filter(([, v]) => v !== '' && v !== undefined)).toString();

    let komChart;
    const load = async () => {
      const d = await Api.get(`izin?${query({ sort: st.order, limit: LIMIT, offset: st.offset })}`);
      view.querySelectorAll('#pTabel th.sortable').forEach((th) => {
        if (th.dataset.o === st.order) th.setAttribute('aria-sort', st.order === 'luas' ? 'descending' : 'ascending');
        else th.removeAttribute('aria-sort');
      });
      const what = [st.komoditas && st.komoditas.toLowerCase(), st.kegiatan && `tahap ${st.kegiatan.toLowerCase()}`].filter(Boolean).join(', ');
      $('#pTabel h2').textContent = `${Fmt.int(d.total)} izin${what ? ` ${what}` : ''}${st.provinsi ? ` di ${st.provinsi}` : ''}${st.q ? `, cari “${st.q}”` : ''}`;
      $('#tIzin').innerHTML = d.data.map((r) => `<tr>
          <td>${esc(r.badan_usaha !== '-' ? `${r.badan_usaha} ` : '')}${esc(r.nama_perusahaan)}<div class="muted mono">${esc(r.sk_iup)}</div></td>
          <td>${esc(r.nama_provinsi)}<div class="muted">${esc(r.nama_kabupaten)}</div></td>
          <td>${esc(r.komoditas)}</td><td>${esc(r.kegiatan)}</td>
          <td class="n">${Fmt.n(r.luas_sk_ha, r.luas_sk_ha % 1 ? 1 : 0)}</td></tr>`).join('')
        || '<tr><td colspan="5" class="empty">Tidak ada izin yang cocok</td></tr>';
      const end = Math.min(st.offset + LIMIT, d.total);
      $('#pgInfo').textContent = d.total ? `${Fmt.int(st.offset + 1)}–${Fmt.int(end)} dari ${Fmt.int(d.total)}` : '';
      $('#bPrev').disabled = st.offset === 0;
      $('#bNext').disabled = end >= d.total;

      komChart?.destroy();
      const pk = d.per_komoditas, tot = pk.reduce((s, r) => s + r.n, 0);
      $('#pKom h2').textContent = pk.length
        ? (st.provinsi ? `Komoditas di ${st.provinsi}` : 'Komoditas')
        : 'Tidak ada izin';
      komChart = barChart($('#cKom'), {
        horizontal: true, unit: 'izin', decimals: 0,
        labels: pk.map((r) => r.komoditas),
        series: [{ label: 'Izin', data: pk.map((r) => r.n),
          backgroundColor: pk.map((r) => (!st.komoditas || r.komoditas === st.komoditas ? css('--bar') : css('--bar-muted'))) }],
        onClick: (i) => { st.komoditas = st.komoditas === pk[i].komoditas ? '' : pk[i].komoditas; $('#fKom').value = st.komoditas; reset(); },
      });
    };

    const reset = () => { st.offset = 0; load(); };
    let t;
    $('#fQ').addEventListener('input', (e) => { clearTimeout(t); t = setTimeout(() => { st.q = e.target.value.trim(); reset(); }, 250); });
    $('#fProv').addEventListener('change', (e) => { st.provinsi = e.target.value; drawProv(); reset(); });
    $('#fKom').addEventListener('change', (e) => { st.komoditas = e.target.value; reset(); });
    $('#fKeg').addEventListener('change', (e) => { st.kegiatan = e.target.value; reset(); });
    $('#bReset').addEventListener('click', () => {
      Object.assign(st, { q: '', provinsi: '', komoditas: '', kegiatan: '' });
      ['#fQ', '#fProv', '#fKom', '#fKeg'].forEach((s) => { $(s).value = ''; });
      drawProv(); reset();
    });
    $('#bPrev').addEventListener('click', () => { st.offset = Math.max(0, st.offset - LIMIT); load(); });
    $('#bNext').addEventListener('click', () => { st.offset += LIMIT; load(); });
    view.querySelector('#pTabel thead').addEventListener('click', (e) => {
      const th = e.target.closest('th.sortable'); if (!th) return;
      st.order = th.dataset.o; reset();
    });
    $('#bCsv').addEventListener('click', async (e) => {
      e.target.disabled = true;
      try { await Api.download(`izin.csv?${query()}`, 'izin_tambang.csv'); } finally { e.target.disabled = false; }
    });
    await load();
    if (params.provinsi || params.komoditas) $('#daftar').scrollIntoView({ block: 'start' });
  },
};
