/* Navigasi antarhalaman berbasis hash: #halaman?param=nilai */
const Pages = window.Pages || {};

const Router = {
  current: null,

  /* Nama lama tetap diarahkan supaya tautan lama tidak rusak */
  alias: { ikhtisar: 'ringkasan', wilayah: 'izin', pipeline: 'data' },

  parse() {
    let [name, query] = location.hash.replace(/^#/, '').split('?');
    name = this.alias[name] || name;
    return { name: Pages[name] ? name : 'ringkasan', params: Object.fromEntries(new URLSearchParams(query || '')) };
  },

  go(name, params = {}) {
    const q = new URLSearchParams(Object.entries(params).filter(([, v]) => v)).toString();
    location.hash = q ? `${name}?${q}` : name;
  },

  async render() {
    const { name, params } = this.parse();
    this.current = name;
    document.querySelectorAll('.nav a').forEach((a) => {
      if (a.getAttribute('href') === `#${name}`) a.setAttribute('aria-current', 'page');
      else a.removeAttribute('aria-current');
    });
    Charts.destroyAll();
    applyChartDefaults();
    const view = document.getElementById('view');
    view.innerHTML = '<p class="empty">Memuat…</p>';
    try {
      await Pages[name].render(view, params);
      document.title = `${Pages[name].title} · Neraca Tambang`;
    } catch (e) {
      console.error(e);
      view.innerHTML = H.error(`Data belum bisa dimuat: ${e.message}`);
    }
  },
};

document.addEventListener('DOMContentLoaded', async () => {
  if (!Auth.token()) { location.replace('/'); return; }
  document.getElementById('whoName').textContent = Auth.user();
  document.getElementById('logoutBtn').addEventListener('click', () => Auth.logout());
  window.addEventListener('hashchange', () => Router.render());
  matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => Router.render());
  await document.fonts.ready;
  Router.render();
});
