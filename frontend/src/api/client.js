// src/api/client.js
// Axios instance for ILA backend — connect to Likhita's FastAPI

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

// Lightweight fetch wrapper (no Axios install needed for mock-first dev)
async function request(method, path, body = null, token = null) {
  const headers = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const opts = { method, headers };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(`${BASE_URL}${path}`, opts);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

export const api = {
  // Auth
  login: (username, password) =>
    request('POST', '/api/v1/auth/login', { username, password }),

  // Alerts
  getAlerts: (params = {}) => {
    const q = new URLSearchParams(params).toString();
    return request('GET', `/api/v1/alerts?${q}`);
  },
  getAlert: (id) => request('GET', `/api/v1/alerts/${id}`),
  updateAlertStatus: (id, status) =>
    request('PATCH', `/api/v1/alerts/${id}/status`, { status }),

  // Entities
  getEntities: (params = {}) => {
    const q = new URLSearchParams(params).toString();
    return request('GET', `/api/v1/entities?${q}`);
  },
  getEntity: (id) => request('GET', `/api/v1/entities/${id}`),
  getEntityTimeline: (id) => request('GET', `/api/v1/entities/${id}/timeline`),
  explainEntity: (id) => request('GET', `/api/v1/entities/${id}/explain`),

  // Graph
  getGraph: (entityId, hops = 2) =>
    request('GET', `/api/v1/graph/entity/${entityId}/neighbors?hops=${hops}`),
  searchGraph: (q) => request('GET', `/api/v1/graph/search?q=${encodeURIComponent(q)}`),

  // Keywords
  getKeywords: () => request('GET', '/api/v1/keywords'),
  createKeyword: (word, group) => request('POST', '/api/v1/keywords', { word, group }),
  deleteKeyword: (id) => request('DELETE', `/api/v1/keywords/${id}`),
  updateKeyword: (id, data) => request('PATCH', `/api/v1/keywords/${id}`, data),

  // Sources
  getSources: () => request('GET', '/api/v1/sources'),

  // Dashboard
  getDashboardStats: () => request('GET', '/api/v1/dashboard/stats'),

  // Evidence
  generateEvidence: (entityId, note = '') =>
    request('POST', '/api/v1/evidence', { entity_id: entityId, investigation_note: note }),
};

// WebSocket connection for real-time alerts
export function connectAlertStream(onAlert) {
  const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000';
  const ws = new WebSocket(`${WS_URL}/ws/alerts`);
  ws.onmessage = (event) => {
    try {
      const alert = JSON.parse(event.data);
      onAlert(alert);
    } catch (e) {
      console.error('WS parse error', e);
    }
  };
  ws.onerror = (e) => console.error('WS error:', e);
  return ws;
}
