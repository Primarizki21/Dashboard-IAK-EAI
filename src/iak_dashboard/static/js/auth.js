/**
 * Modul Autentikasi & Route Guard (Data-Level EAI)
 */
const AUTH_TOKEN_KEY = 'minerba_auth_token';
const AUTH_USER_KEY = 'minerba_auth_user';

function getAuthToken() {
  return localStorage.getItem(AUTH_TOKEN_KEY) || null;
}

function getAuthUser() {
  return localStorage.getItem(AUTH_USER_KEY) || null;
}

function setAuthSession(token, username) {
  localStorage.setItem(AUTH_TOKEN_KEY, token);
  localStorage.setItem(AUTH_USER_KEY, username);
}

function clearAuthSession() {
  localStorage.removeItem(AUTH_TOKEN_KEY);
  localStorage.removeItem(AUTH_USER_KEY);
}

/**
 * Route guard untuk dashboard terproteksi.
 * Jika belum login atau sesi tidak valid, alihkan ke landing page.
 */
function requireAuth() {
  const token = getAuthToken();
  const user = getAuthUser();
  if (!token || !user || user !== 'admin') {
    clearAuthSession();
    window.location.replace('/?auth=required');
    return false;
  }
  return true;
}

/**
 * Route guard untuk landing page.
 * Jika sudah login sebagai admin, langsung arahkan ke /dashboard.
 */
function redirectIfAuthenticated() {
  const token = getAuthToken();
  const user = getAuthUser();
  if (token && user === 'admin') {
    window.location.replace('/dashboard');
  }
}

/**
 * Melakukan login ke backend API.
 */
async function loginUser(username, password) {
  const res = await fetch('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password })
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Kombinasi nama pengguna atau kata sandi salah.');
  }

  const data = await res.json();
  setAuthSession(data.token, data.username);
  return data;
}

/**
 * Melakukan logout dan mengalihkan ke landing page.
 */
function logoutUser() {
  clearAuthSession();
  window.location.replace('/?auth=logout');
}
