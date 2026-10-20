/* Sesi login dan pemanggilan API. Token disimpan di localStorage dan dikirim sebagai Bearer. */
const Auth = {
  KEY: 'neraca_token',
  USER: 'neraca_user',
  token() { try { return localStorage.getItem(this.KEY); } catch { return null; } },
  user() { try { return localStorage.getItem(this.USER) || ''; } catch { return ''; } },
  save(token, user) { try { localStorage.setItem(this.KEY, token); localStorage.setItem(this.USER, user); } catch {} },
  clear() { try { localStorage.removeItem(this.KEY); localStorage.removeItem(this.USER); } catch {} },

  async login(username, password) {
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail || 'Gagal masuk. Coba lagi.');
    }
    const data = await res.json();
    this.save(data.token, data.username);
    return data;
  },

  async logout() {
    const t = this.token();
    this.clear();
    if (t) await fetch('/api/auth/logout', { method: 'POST', headers: { Authorization: `Bearer ${t}` } }).catch(() => {});
    location.replace('/');
  },
};

const Api = {
  cache: new Map(),

  async get(path, { fresh = false } = {}) {
    if (!fresh && this.cache.has(path)) return this.cache.get(path);
    const res = await fetch(`/api/mining/${path}`, { headers: { Authorization: `Bearer ${Auth.token()}` } });
    if (res.status === 401) {
      Auth.clear();
      location.replace('/?r=expired');
      throw new Error('Sesi berakhir');
    }
    if (!res.ok) throw new Error(`Gagal memuat ${path} (${res.status})`);
    const data = await res.json();
    this.cache.set(path, data);
    return data;
  },

  /* Unduhan berkas tetap butuh header Authorization, jadi lewat fetch + blob */
  async download(path, filename) {
    const res = await fetch(`/api/mining/${path}`, { headers: { Authorization: `Bearer ${Auth.token()}` } });
    if (!res.ok) throw new Error('Gagal mengunduh');
    const url = URL.createObjectURL(await res.blob());
    const a = Object.assign(document.createElement('a'), { href: url, download: filename });
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  },
};
