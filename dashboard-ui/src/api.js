const BASE = '';

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || 'Request failed');
  return data;
}

export const api = {
  login: (username, password) =>
    request('/api/login', { method: 'POST', body: JSON.stringify({ username, password }) }),

  logout: () => request('/api/logout', { method: 'POST' }),

  me: () => request('/api/me'),

  dashboard: () => request('/api/dashboard'),

  appointment: (id) => request(`/api/appointment/${id}`),

  saveNotes: (id, data) =>
    request(`/api/appointment/${id}/save`, { method: 'POST', body: JSON.stringify(data) }),

  cancelAppointment: (id) =>
    request(`/api/appointment/${id}/cancel`, { method: 'POST' }),

  sendMessage: (id, message) =>
    request(`/api/appointment/${id}/message`, { method: 'POST', body: JSON.stringify({ message }) }),

  broadcast: (data) =>
    request('/api/broadcast', { method: 'POST', body: JSON.stringify(data) }),

  expandNotes: (text) =>
    request('/api/expand_notes', { method: 'POST', body: JSON.stringify({ text }) }),

  patients: () => request('/api/patients'),
};
