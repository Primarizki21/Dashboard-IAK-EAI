/* Format angka, pembuat grafik Chart.js, dan potongan HTML yang dipakai semua halaman. */

const Fmt = {
  n(v, d = 1) {
    if (v === null || v === undefined || Number.isNaN(v)) return '–';
    return Number(v).toLocaleString('id-ID', { minimumFractionDigits: d, maximumFractionDigits: d });
  },
  int(v) { return this.n(v, 0); },
  pct(v, d = 1) { return v === null || v === undefined ? '–' : `${this.n(v * 100, d)}%`; },
  /* Rupiah ringkas: miliar / triliun */
  rp(v) {
    if (!v) return '–';
    if (v >= 1e12) return `Rp${this.n(v / 1e12, 2)} triliun`;
    return `Rp${this.n(v / 1e9, 1)} miliar`;
  },
  delta(cur, prev) {
    if (!prev || cur === null || prev === null) return '';
    const d = (cur - prev) / prev;
    const cls = d >= 0 ? 'up' : 'down';
    return `<span class="${cls}">${d >= 0 ? '▲' : '▼'} ${this.n(Math.abs(d) * 100)}%</span>`;
  },
  date(iso) {
    if (!iso) return '–';
    const d = new Date(iso);
    return d.toLocaleDateString('id-ID', { day: 'numeric', month: 'short', year: 'numeric' }) + ', ' +
      d.toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' });
  },
};

const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
const $ = (sel, root = document) => root.querySelector(sel);
const shortProv = (n) => n.replace(/^Kepulauan /, 'Kep. ');

/* ---------- Potongan HTML ---------- */
/* Sumber data per halaman: [format, penerbit dan judul] */
const SRC = {
  heesi: 'HEESI 2024, Kementerian ESDM (PDF)',
  bps: 'BPS (CSV)',
  modi: 'MoDI ESDM (CSV)',
  wiup: 'Ditjen Minerba (JSON)',
  kaltim: 'Dinas ESDM Kalimantan Timur (XLSX)',
  etl: 'log ETL di SQLite',
};

/* Penjelasan istilah, muncul saat kursor diarahkan */
const TERMS = {
  PKP2B: 'Perjanjian Karya Pengusahaan Pertambangan Batubara: kontrak tambang besar yang diteken pemerintah pusat.',
  'KP/IUP': 'Kuasa Pertambangan / Izin Usaha Pertambangan: izin tambang yang dulu diterbitkan pemerintah daerah.',
  KDI: 'Kompensasi Data Informasi: harga data geologi wilayah yang dibayar pemenang lelang.',
  FOB: 'Free on Board: nilai barang saat dimuat ke kapal di pelabuhan asal, belum termasuk ongkos kirim.',
  lifting: 'Volume minyak atau gas yang siap dijual, bukan seluruh yang disedot dari sumur.',
  WIUP: 'Wilayah Izin Usaha Pertambangan: lahan yang boleh ditambang setelah dilelang.',
};

const H = {
  head(title, lede, right = '', sources = []) {
    const src = sources.length ? `<p class="srcline">Data: ${sources.map((k) => SRC[k]).join(', ')}</p>` : '';
    return `<header class="head"><div><h1>${title}</h1>${lede ? `<p>${lede}</p>` : ''}${src}</div>
      ${right ? `<div class="side-info">${right}</div>` : ''}</header>`;
  },
  panel({ w = 12, id = '', title = '', sub = '', body = '', foot = '', card = false }) {
    return `<article class="panel w${w}${card ? ' card' : ''}" ${id ? `id="${id}"` : ''}>
      ${title ? `<h2>${title}</h2>` : ''}${sub ? `<p class="sub">${sub}</p>` : ''}
      ${body}${foot ? `<div class="foot">${foot}</div>` : ''}</article>`;
  },
  legend(items) {
    return `<div class="legend">${items.map(([label, color, kind = '']) =>
      `<span><i class="${kind}" style="background:${color}"></i>${label}</span>`).join('')}</div>`;
  },
  kpi({ label, value, unit = '', delta = '' }) {
    return `<div class="kpi"><div class="label">${label}</div>
      <div class="value">${value}${unit ? `<small>${unit}</small>` : ''}</div>
      ${delta ? `<div class="delta">${delta}</div>` : ''}</div>`;
  },
  term(word, shown = word) {
    return `<abbr class="term" title="${esc(TERMS[word])}" tabindex="0">${shown}</abbr>`;
  },
  seg(name, options, active) {
    return `<div class="seg" role="group" data-seg="${name}">${options.map(([v, l]) =>
      `<button type="button" data-value="${v}" aria-pressed="${v === active}">${l}</button>`).join('')}</div>`;
  },
  select(id, label, options, value = '', allLabel = 'Semua') {
    return `<label class="field">${label}<select id="${id}">
      <option value="">${allLabel}</option>
      ${options.map((o) => { const [v, l] = Array.isArray(o) ? o : [o, o];
        return `<option value="${esc(v)}" ${v === value ? 'selected' : ''}>${esc(l)}</option>`; }).join('')}
      </select></label>`;
  },
  /* Batang kecil + angka dalam satu sel tabel */
  barnum(frac, text) {
    return `<div class="barnum"><div class="b"><div style="width:${(Math.max(0, frac) * 100).toFixed(1)}%"></div></div><span>${text}</span></div>`;
  },
  error(msg) { return `<div class="panel w12"><p class="empty">${esc(msg)}</p></div>`; },
};

/* Pasang handler pada tombol segmented */
function onSeg(root, name, fn) {
  const seg = root.querySelector(`[data-seg="${name}"]`);
  if (!seg) return;
  seg.addEventListener('click', (e) => {
    const b = e.target.closest('button');
    if (!b) return;
    seg.querySelectorAll('button').forEach((x) => x.setAttribute('aria-pressed', String(x === b)));
    fn(b.dataset.value);
  });
}

/* ---------- Grafik ---------- */
const Charts = {
  list: [],
  destroyAll() { this.list.forEach((c) => c.destroy()); this.list = []; },
  add(c) { this.list.push(c); return c; },
};

const crosshairPlugin = {
  id: 'crosshair',
  afterDatasetsDraw(chart) {
    const act = chart.tooltip?.getActiveElements?.();
    if (!act?.length || chart.config.type !== 'line') return;
    const x = act[0].element.x;
    const { top, bottom } = chart.chartArea;
    const c = chart.ctx;
    c.save(); c.strokeStyle = css('--rule-strong'); c.lineWidth = 1;
    c.beginPath(); c.moveTo(x, top); c.lineTo(x, bottom); c.stroke(); c.restore();
  },
};

/* Label nilai terakhir di ujung kanan garis */
const endLabelPlugin = {
  id: 'endLabel',
  afterDatasetsDraw(chart, _args, opts) {
    if (!opts?.on) return;
    const c = chart.ctx;
    c.save();
    c.font = '500 12px "IBM Plex Sans", sans-serif';
    c.fillStyle = css('--ink-2');
    c.textBaseline = 'middle';
    const placed = [];
    chart.data.datasets.forEach((ds, i) => {
      const meta = chart.getDatasetMeta(i);
      if (meta.hidden) return;
      let idx = ds.data.length - 1;
      while (idx >= 0 && (ds.data[idx] === null || ds.data[idx] === undefined)) idx--;
      const p = meta.data[idx];
      if (!p) return;
      let y = p.y;
      placed.forEach((py) => { if (Math.abs(py - y) < 13) y = py + (y >= py ? 13 : -13); });
      placed.push(y);
      c.fillText(opts.format ? opts.format(ds.data[idx]) : Fmt.n(ds.data[idx]), p.x + 7, y);
    });
    c.restore();
  },
};

/* Label penting di titik tertentu: { ds, i, text } */
const calloutPlugin = {
  id: 'callout',
  afterDatasetsDraw(chart, _args, opts) {
    const items = opts?.items || [];
    if (!items.length) return;
    const c = chart.ctx;
    c.save();
    c.font = 'italic 12px "Source Serif 4", Georgia, serif';
    c.fillStyle = css('--ink-2');
    c.strokeStyle = css('--ink-3');
    c.lineWidth = 1;
    items.forEach(({ ds = 0, i, text }) => {
      const p = chart.getDatasetMeta(ds).data[i];
      if (!p) return;
      const y = Math.max(chart.chartArea.top + 4, p.y - 22);
      c.beginPath(); c.moveTo(p.x, p.y - 5); c.lineTo(p.x, y + 4); c.stroke();
      c.beginPath(); c.arc(p.x, p.y, 3, 0, Math.PI * 2); c.fillStyle = css('--ink'); c.fill();
      c.fillStyle = css('--ink-2');
      const w = c.measureText(text).width;
      const right = p.x + 6 + w > chart.chartArea.right;
      c.textAlign = right ? 'right' : 'left';
      c.textBaseline = 'bottom';
      c.fillText(text, right ? p.x - 6 : p.x + 6, y + 4);
    });
    c.restore();
  },
};

function baseOptions({ unit = '', beginAtZero = true, min, max, endLabels = true, decimals = 1, horizontal = false, stacked = false, callouts = [] } = {}) {
  const grid = { color: css('--rule'), drawTicks: false, lineWidth: 0.75 };
  const valueAxis = {
    beginAtZero, min, max, stacked,
    grid, border: { display: false, dash: [2, 3] },
    ticks: { padding: 8, maxTicksLimit: 5, callback: (v) => Number(v).toLocaleString('id-ID') },
  };
  const catAxis = {
    stacked,
    grid: { display: false }, border: { color: css('--rule-strong') },
    ticks: { padding: 6, maxRotation: 0, autoSkipPadding: 12 },
  };
  return {
    responsive: true, maintainAspectRatio: false, animation: false,
    indexAxis: horizontal ? 'y' : 'x',
    interaction: { mode: horizontal ? 'nearest' : 'index', intersect: horizontal, axis: horizontal ? 'y' : 'x' },
    layout: { padding: { right: endLabels && !horizontal ? 46 : 8 } },
    plugins: {
      legend: { display: false },
      endLabel: { on: endLabels && !horizontal, format: (v) => Fmt.n(v, decimals) },
      callout: { items: callouts },
      tooltip: {
        backgroundColor: css('--surface'), titleColor: css('--ink'), bodyColor: css('--ink-2'),
        borderColor: css('--rule-strong'), borderWidth: 1, padding: 10, boxPadding: 4,
        usePointStyle: true, titleFont: { weight: '600' },
        callbacks: {
          label: (t) => {
            const v = horizontal ? t.parsed.x : t.parsed.y;
            return ` ${t.dataset.label}: ${v === null ? 'tidak tersedia' : Fmt.n(v, decimals)} ${unit}`;
          },
        },
      },
    },
    scales: horizontal
      ? { x: valueAxis, y: { ...catAxis, border: { display: false }, ticks: { ...catAxis.ticks, autoSkip: false } } }
      : { x: catAxis, y: valueAxis },
    elements: {
      line: { borderWidth: 2, tension: 0 },
      point: { radius: 0, hoverRadius: 5, hitRadius: 14 },
      bar: { borderRadius: 3, borderSkipped: 'start' },
    },
  };
}

function lineSeries(label, data, color, extra = {}) {
  return {
    label, data, borderColor: color, backgroundColor: color,
    pointBackgroundColor: color, pointBorderColor: css('--surface'), pointBorderWidth: 2,
    spanGaps: false, ...extra,
  };
}

function lineChart(canvas, { labels, series, ...opts }) {
  return Charts.add(new Chart(canvas, {
    type: 'line',
    data: { labels, datasets: series },
    options: baseOptions(opts),
    plugins: [crosshairPlugin, endLabelPlugin, calloutPlugin],
  }));
}

function barChart(canvas, { labels, series, onClick, ...opts }) {
  const options = baseOptions({ endLabels: false, ...opts });
  options.datasets = { bar: { maxBarThickness: 28, categoryPercentage: 0.72, barPercentage: 0.86 } };
  if (opts.horizontal) {
    // Label panjang dipendekkan di sumbu; nama lengkap tetap muncul di tooltip
    options.scales.y.ticks.callback = (_v, i) => (labels[i].length > 16 ? `${labels[i].slice(0, 15)}…` : labels[i]);
  }
  if (onClick) {
    options.onClick = (_e, els) => { if (els.length) onClick(els[0].index); };
    options.onHover = (e, els) => { e.native.target.style.cursor = els.length ? 'pointer' : 'default'; };
  }
  return Charts.add(new Chart(canvas, { type: 'bar', data: { labels, datasets: series }, options }));
}

function applyChartDefaults() {
  Chart.defaults.font.family = '"IBM Plex Sans", system-ui, sans-serif';
  Chart.defaults.font.size = 12;
  Chart.defaults.color = css('--ink-3');
}

/* Urutkan tabel: kembalikan fungsi pembanding */
function sorter(key, dir) {
  return (a, b) => {
    const va = a[key], vb = b[key];
    if (va === vb) return 0;
    if (va === null || va === undefined) return 1;
    if (vb === null || vb === undefined) return -1;
    const r = typeof va === 'string' ? va.localeCompare(vb, 'id') : va - vb;
    return dir === 'asc' ? r : -r;
  };
}
