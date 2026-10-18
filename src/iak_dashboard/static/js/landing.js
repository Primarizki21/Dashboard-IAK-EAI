/**
 * Modul Landing Page: Teaser Metrik Publik EAI & Handler Login Administrator
 */

document.addEventListener('DOMContentLoaded', () => {
  // 1. Jika sudah punya sesi login aktif, langsung ke dashboard
  redirectIfAuthenticated();

  // 2. Muat ringkasan teaser publik (Data EAI)
  loadPublicTeaserMetrics();

  // 3. Periksa notifikasi status di URL (misal: redirect karena belum login atau setelah logout)
  checkUrlNotifications();

  // 4. Pasang listener form login
  const form = document.getElementById('landingLoginForm');
  if (form) {
    form.addEventListener('submit', handleLandingLogin);
  }
});

function checkUrlNotifications() {
  const params = new URLSearchParams(window.location.search);
  const noticeDiv = document.getElementById('landingNotice');
  if (!noticeDiv) return;

  if (params.get('auth') === 'required') {
    noticeDiv.textContent = 'Akses Terbatas: Silakan masuk dengan akun Administrator untuk mengakses dashboard.';
    noticeDiv.className = 'mb-4 p-3 rounded-lg text-xs font-medium bg-amber-50 text-amber-800 border border-amber-200';
    noticeDiv.classList.remove('hidden');
    window.history.replaceState({}, document.title, window.location.pathname);
  } else if (params.get('auth') === 'logout') {
    noticeDiv.textContent = 'Anda telah berhasil keluar dari akun Administrator.';
    noticeDiv.className = 'mb-4 p-3 rounded-lg text-xs font-medium bg-emerald-50 text-emerald-800 border border-emerald-200';
    noticeDiv.classList.remove('hidden');
    window.history.replaceState({}, document.title, window.location.pathname);
  }
}

async function loadPublicTeaserMetrics() {
  try {
    const res = await fetch('/api/mining/summary');
    if (!res.ok) return;
    const d = await res.json();

    const elIzin = document.getElementById('pub-kpi-izin');
    const elProv = document.getElementById('pub-kpi-prov');
    const elKomoditas = document.getElementById('pub-kpi-komoditas');
    const elWiup = document.getElementById('pub-kpi-wiup');
    const elEkspor = document.getElementById('pub-kpi-ekspor');

    if (elIzin) elIzin.textContent = Number(d.total_izin_tambang).toLocaleString();
    if (elProv) elProv.textContent = d.jumlah_provinsi_terdata;
    if (elKomoditas) elKomoditas.textContent = d.jumlah_komoditas_terdata;
    if (elWiup) elWiup.textContent = d.total_blok_lelang_wiup;
    if (elEkspor) elEkspor.textContent = `US$ ${(d.nilai_ekspor_terkini_juta_usd / 1000).toFixed(1)} Miliar`;
  } catch (e) {
    console.error('Error memuat teaser KPI:', e);
  }
}

async function handleLandingLogin(e) {
  e.preventDefault();
  const usernameInput = document.getElementById('usernameInput');
  const passwordInput = document.getElementById('passwordInput');
  const errorDiv = document.getElementById('loginErrorMsg');
  const submitBtn = document.getElementById('submitLoginBtn');

  if (!usernameInput || !passwordInput) return;

  const u = usernameInput.value.trim();
  const p = passwordInput.value;

  if (errorDiv) errorDiv.classList.add('hidden');
  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.textContent = 'Memverifikasi...';
  }

  try {
    await loginUser(u, p);
    window.location.href = '/dashboard?login=success';
  } catch (err) {
    if (errorDiv) {
      errorDiv.textContent = err.message;
      errorDiv.classList.remove('hidden');
    }
  } finally {
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.textContent = 'Masuk ke Dashboard';
    }
  }
}
