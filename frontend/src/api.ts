const TOKEN_KEY = 'openmlr_token';

function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null) {
  if (token) {
    localStorage.setItem(TOKEN_KEY, token);
  } else {
    localStorage.removeItem(TOKEN_KEY);
  }
}

function authHeaders(): Record<string, string> {
  const token = getToken();
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

async function request(method: string, path: string, body?: unknown) {
  const opts: RequestInit = {
    method,
    headers: authHeaders(),
  };
  if (body !== undefined) {
    opts.body = JSON.stringify(body);
  }
  const res = await fetch(path, opts);

  if (res.status === 401) {
    // Token expired or invalid — clear it; App.tsx catch handler shows login
    setToken(null);
    throw new Error('Unauthorized');
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: `HTTP ${res.status}` }));
    throw new Error(err.detail || err.error || `HTTP ${res.status}`);
  }
  return res.json();
}

async function post(path: string, body: unknown) {
  return request('POST', path, body);
}

async function get(path: string) {
  return request('GET', path);
}

async function put(path: string, body: unknown) {
  return request('PUT', path, body);
}

async function del(path: string) {
  return request('DELETE', path);
}

export const api = {
  // Auth
  checkSetup: () => get('/api/auth/check'),
  register: (username: string, password: string, display_name?: string) =>
    post('/api/auth/register', { username, password, display_name }),
  login: (username: string, password: string) =>
    post('/api/auth/login', { username, password }),
  getMe: () => get('/api/auth/me'),

  // Messages
  sendMessage: (message: string, mode?: string) => post('/api/message', { message, mode }),
  submitAnswers: (answers: Record<string, string>) => post('/api/answers', { answers }),
  interrupt: () => post('/api/interrupt', {}),
  sendApproval: (approvals: Record<string, boolean>) => post('/api/approval', { approvals }),
  undo: () => post('/api/undo', {}),
  compact: () => post('/api/compact', {}),
  setModel: (model: string) => post('/api/model', { model }),

  // Conversations
  listConversations: () => get('/api/conversations'),
  createConversation: (title?: string, model?: string, mode?: string) =>
    post('/api/conversations', { title, model, mode }),
  getConversation: (uuid: string) => get(`/api/conversations/${uuid}`),
  deleteConversation: (uuid: string) => del(`/api/conversations/${uuid}`),
  switchConversation: (uuid: string) => post(`/api/conversations/${uuid}/switch`, {}),

  // Settings
  getSettings: () => get('/api/settings'),
  getSettingsCategory: (category: string) => get(`/api/settings/${category}`),
  updateSetting: (category: string, key: string, value: any) =>
    put(`/api/settings/${category}/${key}`, { value }),
  deleteSetting: (category: string, key: string) => del(`/api/settings/${category}/${key}`),

  // Reports
  getReport: (reportId: string) => get(`/api/reports/${reportId}`),

  // Background Jobs
  getJobStatus: (jobId: string) => get(`/api/jobs/${jobId}`),
  getConversationJobs: (uuid: string) => get(`/api/conversations/${uuid}/jobs`),
  cancelJob: (jobId: string) => post(`/api/jobs/${jobId}/cancel`, {}),

  // Providers & Models
  getProviders: () => get('/api/providers'),
  getModels: () => get('/api/models'),
  getStatus: () => get('/api/status'),
  saveConfig: (config: Record<string, string>) => post('/api/config', config),
};
