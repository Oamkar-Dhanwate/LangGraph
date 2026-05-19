// JWT handling
/**
 * ClientIQ — Auth Module
 * Manages JWT tokens, session state, and RBAC permission checks.
 */

const Auth = (() => {
  const TOKEN_KEY  = 'ciq_token';
  const USER_KEY   = 'ciq_user';

  // ── Storage ────────────────────────────────────────────────────────────────
  const getToken  = () => sessionStorage.getItem(TOKEN_KEY);
  const getUser   = () => { try { return JSON.parse(sessionStorage.getItem(USER_KEY)); } catch { return null; } };
  const setToken  = (t) => sessionStorage.setItem(TOKEN_KEY, t);
  const setUser   = (u) => sessionStorage.setItem(USER_KEY, JSON.stringify(u));

  // ── Login / Logout ─────────────────────────────────────────────────────────
  const login = async (email, password) => {
    const data = await AuthAPI.login(email, password);
    if (!data) return false;
    setToken(data.access_token);
    setUser({ id: data.user_id, name: data.full_name, role: data.role, email });
    return true;
  };

  const logout = () => {
    sessionStorage.removeItem(TOKEN_KEY);
    sessionStorage.removeItem(USER_KEY);
    window.location.href = 'index.html';
  };

  // ── Guard ──────────────────────────────────────────────────────────────────
  const requireAuth = () => {
    if (!getToken()) {
      window.location.href = 'index.html';
      return false;
    }
    return true;
  };

  // ── RBAC ───────────────────────────────────────────────────────────────────
  const ROLE_HIERARCHY = { admin: 4, manager: 3, analyst: 2, viewer: 1 };

  const can = (action) => {
    const user = getUser();
    if (!user) return false;
    const roleLevel = ROLE_HIERARCHY[user.role] || 0;

    const PERMISSIONS = {
      read_crm:          1,
      read_financials:   2,
      read_contracts:    3,
      read_pii:          4,
      read_audit_logs:   4,
      export_data:       3,
      manage_users:      4,
    };
    return roleLevel >= (PERMISSIONS[action] || 99);
  };

  const isAdmin   = () => getUser()?.role === 'admin';
  const isManager = () => ['admin', 'manager'].includes(getUser()?.role);

  // ── UI Helpers ─────────────────────────────────────────────────────────────
  const populateUserUI = () => {
    const user = getUser();
    if (!user) return;

    document.querySelectorAll('[data-user-name]').forEach(el => el.textContent = user.name);
    document.querySelectorAll('[data-user-role]').forEach(el => {
      el.textContent = user.role.charAt(0).toUpperCase() + user.role.slice(1);
    });
    document.querySelectorAll('[data-user-initials]').forEach(el => {
      el.textContent = user.name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2);
    });

    // Hide elements that require higher permissions
    document.querySelectorAll('[data-requires]').forEach(el => {
      const required = el.dataset.requires;
      if (!can(required)) el.style.display = 'none';
    });
  };

  // ── Role badge color ───────────────────────────────────────────────────────
  const getRoleBadgeClass = (role) => ({
    admin:   'badge-red',
    manager: 'badge-amber',
    analyst: 'badge-blue',
    viewer:  'badge-gray',
  }[role] || 'badge-gray');

  return { getToken, getUser, setToken, setUser, login, logout, requireAuth, can, isAdmin, isManager, populateUserUI, getRoleBadgeClass };
})();

// ── Toast Notification System ──────────────────────────────────────────────────

const Toast = (() => {
  let container;

  const init = () => {
    if (!document.getElementById('toast-container')) {
      container = document.createElement('div');
      container.id = 'toast-container';
      document.body.appendChild(container);
    }
    container = document.getElementById('toast-container');
  };

  const icons = { success: '✓', error: '✕', info: 'ℹ', warning: '⚠' };
  const colors = { success: 'var(--accent-green)', error: 'var(--accent-red)', info: 'var(--accent-blue)', warning: 'var(--accent-amber)' };

  const show = (message, type = 'info', duration = 3500) => {
    init();
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.innerHTML = `
      <span style="color:${colors[type]};font-weight:700;font-size:16px">${icons[type]}</span>
      <span>${message}</span>`;
    container.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateX(20px)';
      toast.style.transition = 'all 0.2s ease';
      setTimeout(() => toast.remove(), 200);
    }, duration);
  };

  return {
    success: (msg) => show(msg, 'success'),
    error:   (msg) => show(msg, 'error'),
    info:    (msg) => show(msg, 'info'),
    warning: (msg) => show(msg, 'warning'),
  };
})();
