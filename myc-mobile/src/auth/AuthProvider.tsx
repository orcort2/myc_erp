import { createContext, PropsWithChildren, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';

import { login as loginRequest, logout as logoutRequest, refresh as refreshRequest } from '@/src/services/auth.service';
import { deactivateCurrentDevice } from '@/src/services/push-notifications';
import { clearSession, readSession, writeSession } from '@/src/storage/secure-storage';
import type { AuthUser, TokenPair } from '@/src/types/auth';

type AuthContextValue = {
  isLoading: boolean;
  session: TokenPair | null;
  user: AuthUser | null;
  login(email: string, password: string): Promise<AuthUser>;
  logout(): Promise<void>;
  refreshSession(): Promise<TokenPair>;
  authorizedFetch(path: string, init?: RequestInit): Promise<Response>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: PropsWithChildren) {
  const [session, setSession] = useState<TokenPair | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const sessionRef = useRef<TokenPair | null>(null);
  const refreshPromise = useRef<Promise<TokenPair> | null>(null);
  const logoutPromise = useRef<Promise<void> | null>(null);
  const sessionVersion = useRef(0);
  const storageQueue = useRef<Promise<void>>(Promise.resolve());

  // Serialize persistence too: an in-flight write must never outlive a logout clear.
  const persist = useCallback((operation: () => Promise<void>) => {
    const pending = storageQueue.current.catch(() => undefined).then(operation);
    storageQueue.current = pending;
    return pending;
  }, []);

  useEffect(() => {
    let mounted = true;
    const version = sessionVersion.current;
    readSession().then((stored) => {
      if (mounted && version === sessionVersion.current) {
        sessionRef.current = stored;
        setSession(stored);
      }
    }).catch(() => undefined).finally(() => { if (mounted) setIsLoading(false); });
    return () => { mounted = false; };
  }, []);

  const refreshSession = useCallback((): Promise<TokenPair> => {
    if (refreshPromise.current) return refreshPromise.current;
    const current = sessionRef.current;
    if (!current || logoutPromise.current) return Promise.reject(new Error('Sesión no disponible'));
    const version = sessionVersion.current;
    const pending = (async () => {
      try {
        const next = await refreshRequest(current.refresh_token);
        if (version !== sessionVersion.current) {
          await logoutRequest(next.access_token).catch(() => undefined);
          throw new Error('La sesión cambió durante la renovación');
        }
        await persist(async () => {
          if (version === sessionVersion.current) await writeSession(next);
        });
        if (version !== sessionVersion.current) {
          await logoutRequest(next.access_token).catch(() => undefined);
          throw new Error('La sesión cambió durante la renovación');
        }
        sessionRef.current = next;
        setSession(next);
        return next;
      } catch (error) {
        if (version === sessionVersion.current) {
          sessionVersion.current += 1;
          sessionRef.current = null;
          setSession(null);
          await persist(clearSession).catch(() => undefined);
        }
        throw error;
      } finally {
        refreshPromise.current = null;
      }
    })();
    refreshPromise.current = pending;
    return pending;
  }, [persist]);

  const value = useMemo<AuthContextValue>(() => ({
    isLoading,
    session,
    user: session?.user ?? null,
    async login(email, password) {
      await logoutPromise.current;
      const version = ++sessionVersion.current;
      const next = await loginRequest(email, password);
      const canUseMobile = next.user.permissions.includes('*') || next.user.permissions.includes('mobile.access');
      if (!canUseMobile) throw new Error('Tu usuario no tiene acceso a MYC Mobile');
      if (version !== sessionVersion.current) {
        await logoutRequest(next.access_token).catch(() => undefined);
        throw new Error('La sesión cambió durante el acceso');
      }
      await persist(async () => {
        if (version === sessionVersion.current) await writeSession(next);
      });
      if (version !== sessionVersion.current) {
        await logoutRequest(next.access_token).catch(() => undefined);
        throw new Error('La sesión cambió durante el acceso');
      }
      sessionRef.current = next;
      setSession(next);
      return next.user;
    },
    logout() {
      if (logoutPromise.current) return logoutPromise.current;
      const current = sessionRef.current;
      sessionVersion.current += 1;
      sessionRef.current = null;
      setSession(null);
      const pending = (async () => {
        try {
          // A refresh already in flight revokes its successor when it observes the version change.
          await refreshPromise.current?.catch(() => undefined);
          if (current) {
            await logoutRequest(current.access_token).catch(() => undefined);
            await deactivateCurrentDevice(current.access_token).catch(() => undefined);
          }
        } finally {
          try { await persist(clearSession); }
          finally { logoutPromise.current = null; }
        }
      })();
      logoutPromise.current = pending;
      return pending;
    },
    refreshSession,
    async authorizedFetch(path, init = {}) {
      const current = sessionRef.current;
      const version = sessionVersion.current;
      if (!current) throw new Error('Sesión no disponible');
      const headers = new Headers(init.headers);
      headers.set('Authorization', `Bearer ${current.access_token}`);
      const response = await fetch(path, { ...init, headers });
      if (response.status !== 401) return response;
      if (version !== sessionVersion.current || !sessionRef.current) throw new Error('Sesión no disponible');
      // A late 401 from the old token reuses the completed renewal, without rotating again.
      const next = sessionRef.current.access_token !== current.access_token
        ? sessionRef.current : await refreshSession();
      if (version !== sessionVersion.current) throw new Error('Sesión no disponible');
      headers.set('Authorization', `Bearer ${next.access_token}`);
      return fetch(path, { ...init, headers });
    },
  }), [isLoading, persist, refreshSession, session]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth requiere AuthProvider');
  return context;
}
