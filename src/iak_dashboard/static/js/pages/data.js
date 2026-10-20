(window.Pages ||= {}).data = {
  title: 'Sumber Data & ETL',

  /* Penerbit asli vs jalur file diperoleh, ditulis terpisah supaya jujur soal asal salinan */
  SOURCES: {
    'export_coal_by_country.csv': { penerbit: 'Badan Pusat Statistik', jalur: 'Salinan tabel BPS di repositori GitHub supertypeai/coalresearch' },
    'kaltim_mining_operations.xlsx': { penerbit: 'Dinas ESDM Prov. Kalimantan Timur', jalur: 'Portal Satu Data Kaltim (data.kaltimprov.go.id)' },
    'wiup_auctions.json': { penerbit: 'Ditjen Mineral dan Batubara', jalur: 'Salinan data portal lelang WIUP di repositori supertypeai/coalresearch' },
    'esdm_heesi_statistics.pdf': { penerbit: 'Kementerian ESDM', jalur: 'Handbook of Energy & Economic Statistics of Indonesia 2024, esdm.go.id' },
    'modi_mining_licenses.csv': { penerbit: 'Minerba One Data Indonesia (MoDI)', jalur: 'Salinan data MoDI di repositori supertypeai/coalresearch' },
  },

  async render(view) {
    const p = await Api.get('pipeline', { fresh: true });
    const run = p.run;
    const st = (s) => ({ SUCCESS: ['good', 'Berhasil'], WARNING: ['warn', 'Peringatan'], FAILED: ['bad', 'Gagal'],
      PASS: ['good', 'Lolos'], WARN: ['warn', 'Perlu dicek'], REJECT: ['bad', 'Baris ditolak'] }[s] || ['', s]);
    const chip = (s) => { const [c, l] = st(s); return `<span class="st ${c}">${l}</span>`; };
    const totals = p.audit.reduce((a, r) => ({ e: a.e + r.records_extracted, l: a.l + r.records_loaded, r: a.r + r.records_rejected }), { e: 0, l: 0, r: 0 });
    const files = new Set(p.audit.map((r) => r.source_file));
    const formats = new Set(p.audit.map((r) => r.source_format));

    const issues = p.cek.filter((c) => c.result !== 'PASS');

    view.innerHTML = `
      ${H.head('Sumber Data & ETL', 'Lima berkas dalam empat format, dimuat ke satu basis data SQLite.',
        run ? `<span class="meta">Dijalankan ${Fmt.date(run.started_at)}, run <span class="mono">${esc(run.run_id)}</span></span>` : '', ['etl'])}
      <section class="kpis">
        ${H.kpi({ label: 'Berkas sumber', value: files.size, unit: `${formats.size} format`, delta: [...formats].join(', ') })}
        ${H.kpi({ label: 'Baris diekstrak', value: Fmt.int(totals.e), delta: `${p.audit.length} tahap load` })}
        ${H.kpi({ label: 'Baris dimuat', value: Fmt.int(totals.l), delta: totals.r ? `<span class="down">${totals.r} ditolak</span>` : 'tidak ada yang ditolak' })}
        ${H.kpi({ label: 'Hasil pemeriksaan', value: `${p.cek.filter((c) => c.result === 'PASS').length}/${p.cek.length}`, unit: 'lolos',
          delta: run ? chip(run.status) : '' })}
      </section>
      <div class="grid">
        ${H.panel({ w: 12, title: 'Sumber data dan hasil load', body: `<div class="table-wrap"><table><thead><tr>
            <th>Sumber</th><th>Berkas</th><th>Tabel tujuan</th><th class="n">Diekstrak</th><th class="n">Dimuat</th>
            <th class="n">Ditolak</th><th class="n">Durasi</th><th>Status</th></tr></thead><tbody>
            ${p.audit.map((r) => { const s = this.SOURCES[r.source_file] || {}; return `<tr>
              <td>${esc(r.source_name)}<div class="muted">${esc(s.jalur || '')}</div></td>
              <td><span class="mono">${esc(r.source_file)}</span><div class="muted">${esc(r.source_format)}</div></td>
              <td class="mono">${esc(r.target_table)}</td>
              <td class="n">${Fmt.int(r.records_extracted)}</td><td class="n">${Fmt.int(r.records_loaded)}</td>
              <td class="n">${r.records_rejected || '–'}</td><td class="n">${Fmt.int(r.duration_ms)} ms</td>
              <td>${chip(r.status)}${r.message ? `<div class="muted">${esc(r.message)}</div>` : ''}</td></tr>`; }).join('')}
            </tbody></table></div>`, })}
        ${H.panel({ w: 8, title: `${p.cek.filter((c) => c.result === 'PASS').length} dari ${p.cek.length} pemeriksaan lolos`,
          sub: issues.length ? `${issues.length} catatan:` : 'Tidak ada catatan.',
          body: `<ul class="issues">${issues.map((c) => `<li>${chip(c.result)}${esc(c.rule)}${c.affected_rows ? `, ${Fmt.int(c.affected_rows)} baris` : ''}
              ${c.detail ? `<div class="muted">${esc(c.detail)}</div>` : ''}</li>`).join('')}</ul>
            <details class="more"><summary>Lihat semua ${p.cek.length} pemeriksaan</summary><div class="table-wrap"><table><thead><tr><th>Tabel</th><th>Aturan</th><th>Hasil</th><th class="n">Baris</th></tr></thead><tbody>
            ${p.cek.map((c) => `<tr><td class="mono">${esc(c.target_table)}</td>
              <td>${esc(c.rule)}${c.detail ? `<div class="muted">${esc(c.detail)}</div>` : ''}</td>
              <td>${chip(c.result)}</td><td class="n">${c.affected_rows || '–'}</td></tr>`).join('')}
            </tbody></table></div></details>` })}
        ${H.panel({ w: 4, title: 'Hubungan tabel', 
          body: `<div class="schema">
              ${[['fact_cadangan_batubara_provinsi', 'PDF'], ['fact_izin_tambang', 'CSV'], ['fact_lelang_wiup', 'JSON'], ['fact_operasional_kaltim', 'XLSX']]
                .map(([t, f]) => `<div class="row"><div class="box">${t}<small>${f}</small></div><div class="arrow">→</div><div class="box">dim_provinsi<small>38 provinsi + pulau</small></div></div>`).join('')}
              ${[['fact_izin_tambang', 'CSV'], ['fact_lelang_wiup', 'JSON']]
                .map(([t, f]) => `<div class="row"><div class="box">${t}<small>${f}</small></div><div class="arrow">→</div><div class="box">dim_komoditas<small>15 komoditas baku</small></div></div>`).join('')}
              <div class="row"><div class="box">fact_ekspor_batubara<small>CSV</small></div><div class="arrow">↔</div><div class="box">fact_pasokan_batubara_nasional<small>PDF, digabung per tahun</small></div></div>
            </div>`, })}
      </div>`;
  },
};
