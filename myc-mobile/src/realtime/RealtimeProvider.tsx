import { createContext, PropsWithChildren, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { AppState } from 'react-native';

import { useAuth } from '@/src/auth/AuthProvider';
import { REALTIME_URL } from '@/src/config/environment';
import { RealtimeClient } from '@/src/realtime/realtime-client';
import type { RealtimeListener, RealtimeResynchronizer, RealtimeState } from '@/src/realtime/types';

type RealtimeContextValue = {
  state: RealtimeState;
  sendCommand(event: string, data?: Record<string, unknown>): boolean;
  subscribe(listener: RealtimeListener): () => void;
  registerResynchronizer(resynchronizer: RealtimeResynchronizer): () => void;
};

const RealtimeContext = createContext<RealtimeContextValue | null>(null);

// Intervalo/umbral de heartbeat: mantiene vivo el WebSocket y detecta
// conexiones muertas en silencio (p. ej. tras un cambio de red o un NAT idle
// timeout) que de otro modo nunca dispararían `onclose`. Ver MOB-005.
const REALTIME_HEARTBEAT_INTERVAL_MS = 25_000;
const REALTIME_HEARTBEAT_TIMEOUT_MS = 60_000;

export function RealtimeProvider({ children }: PropsWithChildren) {
  const { refreshSession, session, user } = useAuth();
  const [state, setState] = useState<RealtimeState>('disconnected');
  const listeners = useRef(new Set<RealtimeListener>());
  const resynchronizers = useRef(new Set<RealtimeResynchronizer>());
  const clientRef = useRef<RealtimeClient | null>(null);
  const sessionRef = useRef(session);
  const refreshRef = useRef(refreshSession);
  const userId = user?.id;
  sessionRef.current = session;
  refreshRef.current = refreshSession;

  const subscribe = useCallback((listener: RealtimeListener) => {
    listeners.current.add(listener);
    return () => listeners.current.delete(listener);
  }, []);

  const registerResynchronizer = useCallback((resynchronizer: RealtimeResynchronizer) => {
    resynchronizers.current.add(resynchronizer);
    return () => resynchronizers.current.delete(resynchronizer);
  }, []);

  const sendCommand = useCallback((event: string, data: Record<string, unknown> = {}) => (
    clientRef.current?.sendCommand(event, data) ?? false
  ), []);

  useEffect(() => {
    if (!userId) {
      setState('disconnected');
      return;
    }
    const client = new RealtimeClient({
      url: REALTIME_URL,
      getAccessToken: () => sessionRef.current?.access_token ?? null,
      async refreshAccessToken() {
        const refreshed = await refreshRef.current();
        return refreshed.access_token;
      },
      createSocket: (url, protocols) => new WebSocket(url, protocols),
      onState: setState,
      onEnvelope: (envelope) => listeners.current.forEach((listener) => listener(envelope)),
      async resynchronize() {
        await Promise.all([...resynchronizers.current].map((callback) => callback()));
      },
      heartbeatIntervalMs: REALTIME_HEARTBEAT_INTERVAL_MS,
      heartbeatTimeoutMs: REALTIME_HEARTBEAT_TIMEOUT_MS,
    });
    clientRef.current = client;
    client.start();
    if (AppState.currentState && AppState.currentState !== 'active') client.background();
    const appState = AppState.addEventListener('change', (nextState) => {
      if (nextState === 'active') client.foreground();
      else client.background();
    });
    return () => {
      clientRef.current = null;
      appState.remove();
      client.stop();
    };
  }, [userId]);

  const value = useMemo<RealtimeContextValue>(() => ({
    state,
    sendCommand,
    subscribe,
    registerResynchronizer,
  }), [registerResynchronizer, sendCommand, state, subscribe]);

  return <RealtimeContext.Provider value={value}>{children}</RealtimeContext.Provider>;
}

export function useRealtime(): RealtimeContextValue {
  const value = useContext(RealtimeContext);
  if (!value) throw new Error('useRealtime requiere RealtimeProvider');
  return value;
}
