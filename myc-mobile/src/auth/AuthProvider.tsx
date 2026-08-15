import { createContext, PropsWithChildren, useContext, useEffect, useMemo, useState } from 'react';

import { login as loginRequest, refresh as refreshRequest } from '@/src/services/auth.service';
import { deactivateCurrentDevice } from '@/src/services/push-notifications';
import { clearSession, readSession, writeSession } from '@/src/storage/secure-storage';
import type { AuthUser, TokenPair } from '@/src/types/auth';

type AuthContextValue = {
  isLoading: boolean;
  session: TokenPair | null;
  user: AuthUser | null;
  login(email: string, password: string): Promise<AuthUser>;
  logout(): Promise<void>;
  authorizedFetch(path: string, init?: RequestInit): Promise<Response>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: PropsWithChildren) {
  const [session, setSession] = useState<TokenPair | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    readSession().then(setSession).finally(() => setIsLoading(false));
  }, []);

  const value = useMemo<AuthContextValue>(() => ({
    isLoading,
    session,
    user: session?.user ?? null,
    async login(email, password) {
      const next = await loginRequest(email, password);
      const canUseLab = next.user.permissions.includes('*') || next.user.permissions.includes('lab_work_orders.use');
      if (!canUseLab) throw new Error('Tu usuario no tiene acceso a las OT LAB');
      await writeSession(next);
      setSession(next);
      return next.user;
    },
    async logout() {
      if (session) await deactivateCurrentDevice(session.access_token).catch(() => undefined);
      await clearSession();
      setSession(null);
    },
    async authorizedFetch(path, init = {}) {
      if (!session) throw new Error('Sesión no disponible');
      const headers = new Headers(init.headers);
      headers.set('Authorization', `Bearer ${session.access_token}`);
      let response = await fetch(path, { ...init, headers });
      if (response.status !== 401) return response;
      try {
        const next = await refreshRequest(session.refresh_token);
        await writeSession(next);
        setSession(next);
        headers.set('Authorization', `Bearer ${next.access_token}`);
        response = await fetch(path, { ...init, headers });
        return response;
      } catch (error) {
        await clearSession();
        setSession(null);
        throw error;
      }
    },
  }), [isLoading, session]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth requiere AuthProvider');
  return context;
}
