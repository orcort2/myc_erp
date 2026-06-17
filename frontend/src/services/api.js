const API_URL = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000/api';
const ACCESS_TOKEN_KEY = 'myc_access_token';
const REFRESH_TOKEN_KEY = 'myc_refresh_token';

export function getAccessToken() {
  return window.localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function getRefreshToken() {
  return window.localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function saveTokens({ access_token, refresh_token }) {
  window.localStorage.setItem(ACCESS_TOKEN_KEY, access_token);
  window.localStorage.setItem(REFRESH_TOKEN_KEY, refresh_token);
}

export function clearTokens() {
  window.localStorage.removeItem(ACCESS_TOKEN_KEY);
  window.localStorage.removeItem(REFRESH_TOKEN_KEY);
}

async function request(path, options = {}) {
  const token = getAccessToken();
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers ?? {})
  };

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers
  });

  if (!response.ok) {
    let message = 'No se pudo completar la solicitud';
    try {
      const payload = await response.json();
      message = typeof payload.detail === 'string' ? payload.detail : message;
    } catch {
      // Keep default message when response is not JSON.
    }
    throw new Error(message);
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}

export async function login(email, password) {
  const payload = await request('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password })
  });
  saveTokens(payload);
  return payload.user;
}

export async function register({ email, fullName, password }) {
  const payload = await request('/auth/register', {
    method: 'POST',
    body: JSON.stringify({
      email,
      full_name: fullName,
      password
    })
  });
  saveTokens(payload);
  return payload.user;
}

export async function getCurrentUser() {
  return request('/auth/me');
}

export async function refreshSession() {
  const refreshToken = getRefreshToken();
  if (!refreshToken) {
    throw new Error('Sesion expirada');
  }
  const payload = await request('/auth/refresh', {
    method: 'POST',
    body: JSON.stringify({ refresh_token: refreshToken })
  });
  saveTokens(payload);
  return payload.user;
}

export async function getModules() {
  return request('/modules');
}

export async function getDashboardCounts() {
  const endpoints = [
    ['clients', '/clients'],
    ['quotations', '/quotations'],
    ['serviceOrders', '/service-orders'],
    ['equipment', '/equipment'],
    ['fieldSheets', '/field-sheets'],
    ['certificates', '/certificates']
  ];

  const results = await Promise.all(
    endpoints.map(async ([key, path]) => {
      const items = await request(path);
      return [key, Array.isArray(items) ? items.length : 0];
    })
  );

  return Object.fromEntries(results);
}
