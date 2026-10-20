(window.Pages ||= {}).kaltim = {
  title: 'Operasional Tambang Kaltim',

  async render(view) {
    const k = await Api.get('kaltim');
    const ind = {};
    k.data.forEach((r) => { (ind[r.indikator] ||= []).push(r); });
    const get = (name) => ind[name] || [];
    const pkp = get('Produksi Batubara PKP2B'), iup = get('Produksi Batubara KP/IUP');
    const total = get('Total Produksi Batubara (PKP2B+KP/IUP)');
    const minyak = get('Lifting Minyak Bumi'), gas = get('Lifting Gas Alam');
    const years = pkp.map((r) => r.tahun);
    const berjalan = pkp.filter((r) => r.status_periode === 'berjalan').map((r) => r.tahun);
    const final = (arr) => arr.filter((r) => r.status_periode === 'final');
    const tf = final(total), tLast = tf.at(-1), tPrev = tf.at(-2);
    const porsi = k.porsi_nasional;
    const pLast = porsi.at(-1);
    const mLast = final(minyak).at(-1), mPrev = final(minyak).at(-2);
    const gLast = final(gas).at(-1), gPrev = final(gas).at(-2);
    const tBerjalan = total.find((r) => r.status_periode === 'berjalan');
    const ket = tBerjalan
      ? `Data ${tBerjalan.tahun} baru sampai ${Fmt.n(tBerjalan.nilai / 1e6, 2)} juta ton, belum setahun penuh.`
      : '';

    // Indikator lingkungan: tandai yang nilainya identik setiap tahun
    const envNames = ['Reklamasi Batubara', 'Persentase Area Yang Direhabilitasi Dari Lahan Terganggu',
      'Luas Area Penambangan Yang Liar', 'Luas Penambangan Liar Yang Diterbitkan', 'Jumlah Perusahaan Batubara'];
    const envYears = [...new Set(envNames.flatMap((n) => get(n).map((r) => r.tahun)))].sort();

    view.innerHTML = `
      ${H.head('Operasional Tambang Kaltim', `Kalimantan Timur punya cadangan batubara terbesar di Indonesia dan menyumbang ${Fmt.pct(pLast.kaltim_juta_ton / pLast.nasional_juta_ton, 0)} produksi nasional ${pLast.tahun}.`, '', ['kaltim', 'heesi'])}
      <section class="kpis">
        ${H.kpi({ label: `Produksi batubara ${tLast.tahun}`, value: Fmt.n(tLast.nilai / 1e6), unit: 'juta ton',
          delta: `${Fmt.delta(tLast.nilai, tPrev.nilai)} dari ${tPrev.tahun}`, src: 'ESDM Kaltim (XLSX)' })}
        ${H.kpi({ label: `Porsi dari produksi nasional ${pLast.tahun}`, value: Fmt.pct(pLast.kaltim_juta_ton / pLast.nasional_juta_ton, 0),
          delta: `${Fmt.n(pLast.kaltim_juta_ton)} dari ${Fmt.n(pLast.nasional_juta_ton)} jt ton`, src: 'XLSX × HEESI (PDF)' })}
        ${H.kpi({ label: `Lifting minyak ${mLast.tahun}`, value: Fmt.n(mLast.nilai / 1e6), unit: 'juta barel',
          delta: `${Fmt.delta(mLast.nilai, mPrev.nilai)} dari ${mPrev.tahun}`, src: 'ESDM Kaltim (XLSX)' })}
        ${H.kpi({ label: `Lifting gas ${gLast.tahun}`, value: Fmt.n(gLast.nilai / 1e6), unit: 'juta MMBTU',
          delta: `${Fmt.delta(gLast.nilai, gPrev.nilai)} dari ${gPrev.tahun}`, src: 'ESDM Kaltim (XLSX)' })}
      </section>
      <div class="grid">
        ${H.panel({ w: 7, id: 'pSkema', title: '&nbsp;', sub: `juta ton, menurut jenis izin (${H.term('PKP2B')} dan ${H.term('KP/IUP')})`,
          body: `${H.legend([['PKP2B (kontrak pusat)', css('--c1'), 'sq'], ['KP/IUP (izin daerah)', css('--c3'), 'sq']])}
                 <div class="chart"><canvas id="cSkema" role="img" aria-label="Produksi PKP2B dan IUP per tahun"></canvas></div>
                 ${ket ? `<p class="note">${ket}</p>` : ''}`, })}
        ${H.panel({ w: 5, id: 'pPorsi', title: 'Porsi dari produksi nasional', sub: 'persen, dihitung dari data Kaltim dan HEESI',
          body: `<div class="chart"><canvas id="cPorsi" role="img" aria-label="Porsi Kaltim terhadap produksi nasional"></canvas></div>
`, })}
        ${H.panel({ w: 12, id: 'pLift', title: '&nbsp;',
          body: `<div class="pair">
            <div><h3>Minyak bumi, juta barel</h3><div class="chart short"><canvas id="cMinyak" role="img" aria-label="Lifting minyak per tahun"></canvas></div></div>
            <div><h3>Gas alam, juta MMBTU</h3><div class="chart short"><canvas id="cGas" role="img" aria-label="Lifting gas per tahun"></canvas></div></div></div>` })}
        ${H.panel({ w: 12, title: 'Lingkungan dan perizinan',
          sub: 'Angka yang pudar tidak berubah sama sekali dari tahun ke tahun di sumber.',
          body: `<div class="table-wrap"><table><thead><tr><th>Indikator</th><th>Satuan</th>
              ${envYears.map((y) => `<th class="n">${y}</th>`).join('')}</tr></thead><tbody>
              ${envNames.filter((n) => get(n).length).map((n) => {
                const r = get(n), vals = new Set(r.map((x) => x.nilai));
                const flat = r.length >= 3 && vals.size === 1;
                return `<tr><td>${esc(n)}</td><td class="muted">${esc(r[0].satuan)}</td>
                  ${envYears.map((y) => { const x = r.find((v) => v.tahun === y); return `<td class="n${flat ? ' flat' : ''}">${x ? Fmt.n(x.nilai, x.nilai % 1 ? 1 : 0) : '–'}</td>`; }).join('')}</tr>`;
              }).join('')}</tbody></table></div>`, })}
      </div>`;

    // Produksi per skema izin
    const finalYears = years.filter((y) => !berjalan.includes(y));
    const lastF = finalYears.at(-1);
    const pk = pkp.find((r) => r.tahun === lastF), ip = iup.find((r) => r.tahun === lastF);
    $('#pSkema h2').textContent = pk.nilai > ip.nilai
      ? `PKP2B menyumbang ${Fmt.pct(pk.nilai / (pk.nilai + ip.nilai), 0)} produksi Kaltim pada ${lastF}`
      : `Izin daerah (KP/IUP) menyumbang ${Fmt.pct(ip.nilai / (pk.nilai + ip.nilai), 0)} produksi Kaltim pada ${lastF}`;
    barChart($('#cSkema'), {
      labels: finalYears, unit: 'jt ton',
      series: [
        { label: 'PKP2B', data: final(pkp).map((r) => r.nilai / 1e6), backgroundColor: css('--c1') },
        { label: 'KP/IUP', data: final(iup).map((r) => r.nilai / 1e6), backgroundColor: css('--c3') },
      ],
    });

    barChart($('#cPorsi'), {
      labels: porsi.map((r) => r.tahun), unit: '%', decimals: 1,
      series: [{ label: 'Porsi Kaltim', data: porsi.map((r) => (r.kaltim_juta_ton / r.nasional_juta_ton) * 100), backgroundColor: css('--bar') }],
    });

    const liftLine = (canvas, rows, label, color) => lineChart(canvas, {
      labels: final(rows).map((r) => r.tahun), unit: '', decimals: 1,
      series: [lineSeries(label, final(rows).map((r) => r.nilai / 1e6), color)],
    });
    const trend = (rows, what) => {
      const f = final(rows), b = f.at(-1);
      const peak = f.reduce((x, y) => (y.nilai > x.nilai ? y : x));
      if (peak.tahun === b.tahun) return `${what} ${b.tahun} tertinggi dalam periode ini`;
      return `${what} ${b.tahun} turun ${Fmt.n((1 - b.nilai / peak.nilai) * 100, 0)}% dari puncaknya pada ${peak.tahun}`;
    };
    $('#pLift h2').textContent = `${trend(minyak, 'Lifting minyak')}, ${trend(gas, 'gas')}`;
    liftLine($('#cMinyak'), minyak, 'Minyak', css('--c4'));
    liftLine($('#cGas'), gas, 'Gas', css('--c2'));
  },
};
