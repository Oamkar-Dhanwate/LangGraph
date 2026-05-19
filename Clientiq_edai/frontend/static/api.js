// Fetch wrappers
/**
 * ClientIQ — API Client
 * Centralized fetch wrappers for all backend REST endpoints.
 * Automatically injects JWT token and handles errors/toasts.
 */

const API_BASE = '/api';

// ── Core Fetch Wrapper ────────────────────────────────────────────────────────

async function apiFetch(path, options = {}) {
  const token = Auth.getToken();
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(options.headers || {}),
  };

  try {
    const res = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers,
    });

    if (res.status === 401) {
      Auth.logout();
      return null;
    }

    const data = await res.json().catch(() => null);

    if (!res.ok) {
      const msg = data?.detail || `Error ${res.status}`;
      Toast.error(msg);
      throw new Error(msg);
    }

    return data;
  } catch (err) {
    if (err.name !== 'Error' || !err.message.startsWith('Error ')) {
      console.error('[API]', path, err.message);
    }
    throw err;
  }
}

const get  = (path, params) => {
  const url = params ? `${path}?${new URLSearchParams(params)}` : path;
  return apiFetch(url, { method: 'GET' });
};
const post = (path, body) => apiFetch(path, { method: 'POST', body: JSON.stringify(body) });
const patch = (path, body) => apiFetch(path, { method: 'PATCH', body: JSON.stringify(body) });

// ── Auth ──────────────────────────────────────────────────────────────────────

const AuthAPI = {
  login: (email, password) => post('/auth/login', { email, password }),
  me:    ()                 => get('/auth/me'),
  logout: ()                => post('/auth/logout', {}),
};

// ── AI Query ──────────────────────────────────────────────────────────────────

const QueryAPI = {
  execute: (query, sessionId, companyId, companyName) =>
    post('/query/', { query, session_id: sessionId, company_id: companyId, company_name: companyName }),
  intents: () => get('/query/intents'),
};

// ── Analytics ─────────────────────────────────────────────────────────────────

const AnalyticsAPI = {
  overview:     ()            => get('/analytics/overview'),
  churnRisk:    (minRisk)     => get('/analytics/churn-risk', minRisk ? { min_risk: minRisk } : {}),
  revenueTrend: (months)      => get('/analytics/revenue-trend', { months: months || 6 }),
  sentimentTimeline: (companyId, days) =>
    get('/analytics/sentiment-timeline', { ...(companyId ? { company_id: companyId } : {}), days: days || 90 }),
  healthDistribution: ()      => get('/analytics/health-distribution'),
};

// ── Clients ───────────────────────────────────────────────────────────────────

const ClientsAPI = {
  list:      (search, tier)  => get('/clients/', { ...(search ? { search } : {}), ...(tier ? { tier } : {}) }),
  get:       (id)            => get(`/clients/${id}`),
  contacts:  (id)            => get(`/clients/${id}/contacts`),
  meetings:  (id)            => get(`/clients/${id}/meetings`),
  contracts: (id)            => get(`/clients/${id}/contracts`),
  tickets:   (id, status)    => get(`/clients/${id}/tickets`, status ? { status } : {}),
  emails:    (id)            => get(`/clients/${id}/emails`),
  calls:     (id)            => get(`/clients/${id}/calls`),
};

// ── Knowledge Graph ───────────────────────────────────────────────────────────

const GraphAPI = {
  data:       (companyId)    => get('/graph/', companyId ? { company_id: companyId } : {}),
  centrality: ()             => get('/graph/centrality'),
};

// ── Admin ─────────────────────────────────────────────────────────────────────

const AdminAPI = {
  auditLogs:   (params)      => get('/admin/audit-logs', params || {}),
  users:       ()            => get('/admin/users'),
  roles:       ()            => get('/admin/roles'),
  systemStats: ()            => get('/admin/system-stats'),
  predictSentiment: (body)   => post('/admin/sentiment-prediction', body),
  createRecord:(type, body)  => post(`/admin/records/${type}`, body),
  deactivate:  (userId)      => patch(`/admin/users/${userId}/deactivate`),
};

// ── Health ────────────────────────────────────────────────────────────────────

const SystemAPI = {
  health: () => get('/health'),
};
