(window.Pages ||= {}).produksi = {
  title: 'Produksi & Ekspor Batubara',

  async render(view, params) {
    const [ekspor, rekon] = await Promise.all([Api.get('ekspor'), Api.get('rekonsiliasi')]);
    const years = ekspor.tahunan.map((r) => r.tahun);
    const lastY = years.at(-1), prevY = years.at(-2);
    const byCountry = {};
    ekspor.negara.forEach((r) => { (byCountry[r.negara_tujuan] ||= {})[r.tahun] = r; });
    const countries = ekspor.urutan_negara;
    const label = (c) => ({ Others: 'Negara lain', 'Korea. Republic Of': 'Korea Selatan', Hongkong: 'Hong Kong' }[c] || c);
    const state = { negara: countries.includes(params.negara) ? params.negara : '', ukuran: 'volume' };
    const M = {
      volume: { key: 'volume_ribu_ton', lower: 'volume', unit: 'jt ton', d: 1 },
      nilai: { key: 'nilai_fob_juta_usd', lower: 'nilai', unit: 'miliar US$', d: 2 },
    };

    const top2 = countries.slice(0, 2).map((c) => byCountry[c][lastY]?.volume_ribu_ton || 0);
    const share2 = (top2[0] + top2[1]) / ekspor.tahunan.at(-1).volume_ribu_ton;

    view.innerHTML = `
      ${H.head('Produksi & Ekspor Batubara',
        `${label(countries[0])} dan ${label(countries[1])} membeli ${Fmt.pct(share2, 0)} batubara yang diekspor Indonesia pada ${lastY}.`,
        '', ['bps', 'heesi'])}
      <div class="filters">
        ${H.select('fNegara', 'Negara tujuan', countries.map((c) => [c, label(c)]), state.negara, 'Semua negara')}
        <div class="field">Ukuran ${H.seg('ukuran', [['volume', 'Volume'], ['nilai', 'Nilai FOB']], 'volume')}</div>
      </div>
      <div class="grid">
        ${H.panel({ w: 12, id: 'pTren', title: '&nbsp;', sub: '&nbsp;',
          body: '<div class="chart"><canvas id="cTren" role="img" aria-label="Tren ekspor per tahun"></canvas></div>' })}
        ${H.panel({ w: 12, id: 'pMulti', title: `Per negara tujuan, ${years[0]}–${lastY}`, sub: '&nbsp;',
          body: '<div class="multiples" id="multi"></div>' })}
        ${H.panel({ w: 4, id: 'pHarga', title: '&nbsp;', sub: 'US$ per ton (nilai ekspor dibagi volume)',
          body: '<div class="chart"><canvas id="cHarga" role="img" aria-label="Harga rata-rata ekspor per ton"></canvas></div>' })}
        ${H.panel({ w: 8, id: 'pRekon', title: '&nbsp;', sub: 'Volume ekspor total, juta ton',
          body: `${H.legend([['HEESI, Kementerian ESDM', css('--c2')], ['BPS', css('--ref')]])}
                 <div class="chart"><canvas id="cRekon" role="img" aria-label="Ekspor menurut HEESI dan BPS"></canvas></div>` })}
      </div>`;

    let trenChart, minis = [];
    const drawExport = () => {
      trenChart?.destroy(); minis.forEach((c) => c.destroy()); minis = [];
      const m = M[state.ukuran];
      const raw = state.negara ? years.map((y) => byCountry[state.negara][y]?.[m.key] ?? null) : ekspor.tahunan.map((r) => r[m.key]);
      const vals = raw.map((v) => (v === null ? null : v / 1000));
      const name = state.negara ? label(state.negara) : 'Semua negara';
      const lv = vals.at(-1), pv = vals.at(-2);
      $('#pTren h2').textContent = state.negara ? `Ekspor ke ${name}` : 'Ekspor batubara Indonesia';
      $('#pTren .sub').innerHTML = lv === null
        ? `${m.unit}, tidak ada data ${lastY}`
        : `${m.unit}. Tahun ${lastY}: ${Fmt.n(lv, m.d)}, ${Fmt.delta(lv, pv) || '–'} dari ${prevY}`;
      trenChart = lineChart($('#cTren'), {
        labels: years, unit: m.unit, decimals: m.d,
        series: [lineSeries(name, vals, css('--c2'))],
      });

      // Small multiples: satu grafik kecil per negara, skala sama supaya bisa dibandingkan
      const series = Object.fromEntries(countries.map((c) => [c, years.map((y) => {
        const v = byCountry[c][y]?.[m.key]; return v == null ? null : v / 1000; })]));
      const max = Math.max(...Object.values(series).flat().filter((v) => v !== null));
      $('#pMulti .sub').textContent = `${m.unit}, skala sama untuk semua negara. Pilih untuk melihat lebih dekat.`;
      $('#multi').innerHTML = countries.map((c) => `
        <button type="button" class="mini" data-c="${esc(c)}" aria-pressed="${c === state.negara}">
          <span class="mini-name">${esc(label(c))}</span>
          <span class="mini-val">${Fmt.n(series[c].at(-1), m.d)}</span>
          <span class="mini-chart"><canvas aria-hidden="true"></canvas></span>
        </button>`).join('');
      $('#multi').querySelectorAll('.mini').forEach((btn) => {
        const c = btn.dataset.c, on = c === state.negara;
        minis.push(Charts.add(new Chart(btn.querySelector('canvas'), {
          type: 'line',
          data: { labels: years, datasets: [{ data: series[c], borderColor: on || !state.negara ? css('--c2') : css('--ink-3'),
            borderWidth: on ? 2 : 1.5, pointRadius: 0, tension: 0, spanGaps: false,
            fill: true, backgroundColor: on ? `${css('--c2')}22` : 'transparent' }] },
          options: { responsive: true, maintainAspectRatio: false, animation: false, events: [],
            plugins: { legend: { display: false }, tooltip: { enabled: false } },
            scales: { x: { display: false }, y: { display: false, min: 0, max } } },
        })));
      });
    };
    $('#fNegara').addEventListener('change', (e) => { state.negara = e.target.value; drawExport(); });
    $('#multi').addEventListener('click', (e) => {
      const b = e.target.closest('.mini'); if (!b) return;
      state.negara = state.negara === b.dataset.c ? '' : b.dataset.c;
      $('#fNegara').value = state.negara; drawExport();
      $('#pTren').scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
    onSeg(view, 'ukuran', (v) => { state.ukuran = v; drawExport(); });
    drawExport();

    const h = ekspor.tahunan;
    const peak = h.reduce((a, b) => (b.harga_usd_per_ton > a.harga_usd_per_ton ? b : a));
    $('#pHarga h2').textContent = `Harga ekspor sempat US$${Fmt.int(peak.harga_usd_per_ton)} per ton pada ${peak.tahun}`;
    lineChart($('#cHarga'), {
      labels: h.map((x) => x.tahun), unit: 'US$/ton', decimals: 0,
      callouts: [{ i: h.indexOf(peak), text: `puncak ${peak.tahun}` }],
      series: [lineSeries('Harga rata-rata', h.map((x) => x.harga_usd_per_ton), css('--c4'))],
    });

    const r = rekon.data, lr = r.at(-1);
    $('#pRekon h2').textContent = `Pada ${lr.tahun}, HEESI mencatat ekspor ${Fmt.int(lr.heesi_juta_ton - lr.bps_juta_ton)} juta ton lebih banyak dari BPS`;
    const ec = css('--c2');
    lineChart($('#cRekon'), {
      labels: r.map((x) => x.tahun), unit: 'jt ton', beginAtZero: false,
      series: [
        lineSeries('HEESI', r.map((x) => x.heesi_juta_ton), ec, { fill: { target: 1, above: `${ec}22`, below: 'transparent' } }),
        lineSeries('BPS', r.map((x) => x.bps_juta_ton), css('--ref')),
      ],
    });
  },
};
