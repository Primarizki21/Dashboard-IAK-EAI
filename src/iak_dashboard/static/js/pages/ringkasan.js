(window.Pages ||= {}).ringkasan = {
  title: 'Ringkasan',

  async render(view) {
    const [sum, neraca] = await Promise.all([Api.get('summary'), Api.get('neraca')]);
    const N = neraca.data, last = N.at(-1), first = N[0];
    const fobLast = sum.fob.at(-1), fobPrev = sum.fob.at(-2);
    const k = sum.kaltim, run = sum.etl;
    const naik = (last.produksi_ton / first.produksi_ton - 1) * 100;
    const ekspor = last.ekspor_ton / last.produksi_ton;

    view.innerHTML = `
      ${H.head('Ringkasan', '', run ? `<span class="meta">Data dimuat ${Fmt.date(run.finished_at)}</span>` : '',
        ['heesi', 'bps', 'modi', 'wiup', 'kaltim'])}
      <section class="lead">
        <div class="lead-text">
          <div class="lead-num">${Fmt.n(last.produksi_ton / 1e6)}<small>juta ton</small></div>
          <p>batubara diproduksi Indonesia pada ${last.tahun}, naik ${Fmt.n(naik, 0)}% dari ${first.tahun}.
             ${ekspor > 0.6 ? 'Dua pertiga' : Fmt.pct(ekspor, 0)} di antaranya dijual ke luar negeri.</p>
          ${H.legend([['Produksi', css('--c1')], ['Ekspor', css('--c2')], ['Dipakai di dalam negeri', css('--c3')]])}
        </div>
        <div class="chart tall"><canvas id="cNeraca" role="img" aria-label="Produksi, ekspor, dan pemakaian dalam negeri per tahun"></canvas></div>
      </section>
      <section class="kpis">
        ${H.kpi({ label: `Nilai ekspor ${H.term('FOB')} ${fobLast.tahun}`, value: `US$${Fmt.n(fobLast.fob / 1000)}`, unit: 'miliar',
          delta: `${Fmt.delta(fobLast.fob, fobPrev.fob)} dari ${fobPrev.tahun}` })}
        ${H.kpi({ label: 'Izin usaha tambang', value: Fmt.int(sum.izin.total), delta: `${sum.izin.komoditas} jenis komoditas` })}
        ${H.kpi({ label: `Blok ${H.term('WIUP')} dilelang`, value: sum.lelang.blok, delta: `${sum.lelang.selesai} sudah ada pemenangnya` })}
        ${H.kpi({ label: `Porsi Kaltim, ${k.tahun}`, value: Fmt.pct(k.kaltim_juta_ton / k.nasional_juta_ton, 0),
          delta: 'dari produksi batubara nasional' })}
      </section>
      <div class="grid">
        ${H.panel({ w: 12, id: 'pKom', title: 'Izin tambang per komoditas',
          body: '<div class="chart tall"><canvas id="cKom" role="img" aria-label="Jumlah izin per komoditas"></canvas></div>' })}
      </div>`;

    const low = N.reduce((m, r, i) => (r.ekspor_ton < N[m].ekspor_ton ? i : m), 0);
    lineChart($('#cNeraca'), {
      labels: N.map((r) => r.tahun), unit: 'juta ton',
      callouts: [{ ds: 1, i: low, text: `ekspor terendah, ${N[low].tahun}` }],
      series: [
        lineSeries('Produksi', N.map((r) => r.produksi_ton / 1e6), css('--c1')),
        lineSeries('Ekspor', N.map((r) => r.ekspor_ton / 1e6), css('--c2')),
        lineSeries('Dalam negeri', N.map((r) => r.konsumsi_domestik_ton / 1e6), css('--c3')),
      ],
    });

    const pk = sum.per_komoditas;
    barChart($('#cKom'), {
      horizontal: true, unit: 'izin', decimals: 0,
      labels: pk.map((r) => r.komoditas),
      series: [{ label: 'Izin', data: pk.map((r) => r.n),
        backgroundColor: pk.map((r) => (r.komoditas === 'Batubara' ? css('--c1') : css('--bar-muted'))) }],
      onClick: (i) => Router.go('izin', { komoditas: pk[i].komoditas }),
    });
  },
};
