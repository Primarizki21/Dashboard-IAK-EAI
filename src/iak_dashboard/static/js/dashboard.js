/**
 * Modul Utama Dashboard EVD: Navigasi Tab, Inisialisasi, & Alert Banner
 */

function switchTab(tabId) {
  document.querySelectorAll('.tab-content').forEach(el => el.classList.add('hidden'));
  document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('tab-active'));

  const activeSection = document.getElementById(tabId);
  if (activeSection) activeSection.classList.remove('hidden');

  const btnId = tabId.replace('tab-', 'nav-');
  const activeBtn = document.getElementById(btnId);
  if (activeBtn) activeBtn.classList.add('tab-active');

  // Khusus tab lelang WIUP: segarkan ukuran canvas peta Leaflet
  if (tabId === 'tab-lelang') {
    refreshMapSize();
  }
}

function showAlert(msg, type = 'info') {
  const banner = document.getElementById('alertBanner');
  const content = document.getElementById('alertContent');
  const text = document.getElementById('alertMessage');
  if (!banner || !content || !text) return;

  text.textContent = msg;
  banner.classList.remove('hidden');

  if (type === 'success') {
    content.className = 'p-3 rounded-lg text-sm flex justify-between items-center bg-emerald-50 text-emerald-800 border border-emerald-200';
  } else {
    content.className = 'p-3 rounded-lg text-sm flex justify-between items-center bg-amber-50 text-amber-800 border border-amber-200';
  }

  setTimeout(hideAlert, 5000);
}

function hideAlert() {
  const banner = document.getElementById('alertBanner');
  if (banner) banner.classList.add('hidden');
}

// Inisialisasi Aplikasi Dashboard Terproteksi
document.addEventListener('DOMContentLoaded', () => {
  // 1. Periksa hak akses (Route Guard)
  if (!requireAuth()) return;

  // 2. Set label username admin
  const user = getAuthUser();
  const userLabel = document.getElementById('authStatusText');
  if (userLabel) userLabel.textContent = `Admin: ${user}`;

  // 3. Tampilkan pesan selamat datang sekali saat baru masuk
  const urlParams = new URLSearchParams(window.location.search);
  if (urlParams.get('login') === 'success') {
    showAlert(`Selamat datang, Administrator ${user}! Berhasil masuk ke sistem dashboard.`, 'success');
    window.history.replaceState({}, document.title, window.location.pathname);
  }

  // 4. Inisialisasi seluruh data analitik
  loadSummaryData();
  loadSupplyAndReserves();
  loadExportFilterOptions();
  loadExportData();
  loadKaltimData();
  initMap();
  loadAuctionData();
  loadLicenseFilterOptions();
  loadLicensesData(0);
  loadAuditLog();
});
