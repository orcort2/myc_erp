import { getAccessToken } from '../services/api.js';
import { invalidateResources } from './invalidation.js';

const REALTIME_PROTOCOL = 'myc.realtime.v1';
const RECONNECT_BASE_MS = 1000;
const RECONNECT_MAX_MS = 30000;

let socket = null;
let reconnectTimer = null;
let reconnectAttempts = 0;
let active = false;
let connectionToken = null;
let hasConnected = false;

function websocketUrl() {
  const configuredApi = import.meta.env.VITE_API_URL
    ?? 'http://127.0.0.1:8000/api';

  const apiUrl = new URL(configuredApi, window.location.origin);

  apiUrl.protocol = apiUrl.protocol === 'https:' ? 'wss:' : 'ws:';
  apiUrl.pathname = '/api/realtime/ws';
  apiUrl.search = '';
  apiUrl.hash = '';

  return apiUrl.toString();
}

function clearReconnectTimer() {
  if (reconnectTimer !== null) {
    window.clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }
}

function scheduleReconnect() {
  if (!active || reconnectTimer !== null) return;

  const delay = Math.min(
    RECONNECT_BASE_MS * (2 ** reconnectAttempts),
    RECONNECT_MAX_MS,
  );

  reconnectAttempts = Math.min(reconnectAttempts + 1, 10);

  reconnectTimer = window.setTimeout(() => {
    reconnectTimer = null;
    connect();
  }, delay);
}

function handleMessage(event) {
  let envelope;

  try {
    envelope = JSON.parse(event.data);
  } catch {
    return;
  }

  if (envelope?.version !== 1 || typeof envelope.event !== 'string') {
    return;
  }

  if (envelope.event === 'resource.changed') {
    const resources = envelope.data?.resources;

    if (
      Array.isArray(resources)
      && resources.every((resource) => typeof resource === 'string')
    ) {
      invalidateResources(resources);
    }
  }
}

function connect() {
  if (!active || socket) return;

  const token = getAccessToken();

  if (!token) {
    connectionToken = null;
    return;
  }

  connectionToken = token;

  const ws = new WebSocket(
    websocketUrl(),
    [REALTIME_PROTOCOL, `auth.${token}`],
  );

  socket = ws;

  ws.addEventListener('open', () => {
    if (socket !== ws) return;
    reconnectAttempts = 0;

    if (hasConnected) {
      invalidateResources(['*']);
    }

    hasConnected = true;
  });

  ws.addEventListener('message', handleMessage);

  ws.addEventListener('close', (event) => {
    if (socket !== ws) return;

    socket = null;

    if (!active) return;

    if (event.code === 4401 || event.code === 4403) {
      return;
    }

    scheduleReconnect();
  });

  ws.addEventListener('error', () => {
    if (socket === ws) {
      ws.close();
    }
  });
}

export function startRealtime() {
  if (active) {
    reconnectRealtimeIfTokenChanged();
    return;
  }

  active = true;
  reconnectAttempts = 0;
  connect();
}

export function stopRealtime() {
  active = false;
  connectionToken = null;
  hasConnected = false;
  clearReconnectTimer();

  const previousSocket = socket;
  socket = null;

  if (previousSocket) {
    previousSocket.close(1000, 'client_disconnected');
  }
}

export function reconnectRealtimeIfTokenChanged() {
  const currentToken = getAccessToken();

  if (!active || currentToken === connectionToken) return;

  stopRealtime();

  if (currentToken) {
    startRealtime();
  }
}
