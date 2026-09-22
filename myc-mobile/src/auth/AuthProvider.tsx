import { createContext, PropsWithChildren, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';

import { ApiError } from '@/src/api/error-detail';
import {
  enrollBiometric as enrollBiometricRequest,
  exchangeBiometric as exchangeBiometricRequest,
  login as loginRequest,
  logout as logoutRequest,
  refresh as refreshRequest,
  revokeBiometric as revokeBiometricRequest,
} from '@/src/services/auth.service';
import { authenticateBiometric, getBiometricAvailability } from '@/src/services/biometric-auth';
import { deactivateCurrentDevice } from '@/src/services/push-notifications';
import {
  clearBiometricEnrollment,
  readBiometricCredential,
  readBiometricProfile,
  writeBiometricCredential,
  writeBiometricProfile,
  type BiometricProfile,
} from '@/src/storage/biometric-storage';
import { clearSession, readSession, writeSession } from '@/src/storage/secure-storage';
import type { AuthUser, TokenPair } from '@/src/types/auth';

type AuthContextValue = {
  isLoading: boolean;
  session: TokenPair | null;
  user: AuthUser | null;
  biometricProfile: BiometricProfile | null;
  biometricAvailable: boolean;
  login(email: string, password: string): Promise<AuthUser>;
  logout(): Promise<void>;
  refreshSession(): Promise<TokenPair>;
  authorizedFetch(path: string, init?: RequestInit): Promise<Response>;
  biometricLogin(): Promise<AuthUser>;
  enableBiometric(): Promise<void>;
  disableBiometric(): Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: PropsWithChildren) {
  const [session, setSession] = useState<TokenPair | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [biometricProfile, setBiometricProfile] = useState<BiometricProfile | null>(null);
  const [biometricAvailable, setBiometricAvailable] = useState(false);
  const sessionRef = useRef<TokenPair | null>(null);
  const refreshPromise = useRef<Promise<TokenPair> | null>(null);
  const logoutPromise = useRef<Promise<void> | null>(null);
  const sessionVersion = useRef(0);
  const storageQueue = useRef<Promise<void>>(Promise.resolve());
  // Mirrors `biometricProfile` for synchronous reads inside closures that
  // must not depend on a stale render (same reason `sessionRef` exists).
  const biometricProfileRef = useRef<BiometricProfile | null>(null);

  // Serialize persistence too: an in-flight write must never outlive a logout clear.
  const persist = useCallback((operation: () => Promise<void>) => {
    const pending = storageQueue.current.catch(() => undefined).then(operation);
    storageQueue.current = pending;
    return pending;
  }, []);

  // While biometric login is enabled for this installation, the operational
  // TokenPair is kept in memory only: a cold start (process killed) must
  // never resume an operative session without biometry. Backgrounding alone
  // never kills `sessionRef`, so refresh/foreground continue to work.
  const persistOperationalSession = useCallback(async (next: TokenPair) => {
    if (biometricProfileRef.current) return;
    await writeSession(next);
  }, []);

  useEffect(() => {
    let mounted = true;
    const version = sessionVersion.current;
    (async () => {
      const [profile, availability] = await Promise.all([
        readBiometricProfile(),
        getBiometricAvailability().catch(() => ({ available: false, enrolled: false, type: 'none' as const, label: 'Biometría' })),
      ]);
      if (!mounted || version !== sessionVersion.current) return;
      biometricProfileRef.current = profile;
      setBiometricProfile(profile);
      setBiometricAvailable(availability.available && availability.enrolled);
      if (profile) return; // Biometric enabled: never auto-restore from a cold start.
      const stored = await readSession();
      if (mounted && version === sessionVersion.current) {
        sessionRef.current = stored;
        setSession(stored);
      }
    })().catch(() => undefined).finally(() => { if (mounted) setIsLoading(false); });
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
          if (version === sessionVersion.current) await persistOperationalSession(next);
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
  }, [persist, persistOperationalSession]);

  // Shared session-setup authority for both password login and biometric
  // login: neither may reimplement version-race handling or persistence.
  const applySession = useCallback(async (next: TokenPair, version: number): Promise<AuthUser> => {
    if (version !== sessionVersion.current) {
      await logoutRequest(next.access_token).catch(() => undefined);
      throw new Error('La sesión cambió durante el acceso');
    }
    await persist(async () => {
      if (version === sessionVersion.current) await persistOperationalSession(next);
    });
    if (version !== sessionVersion.current) {
      await logoutRequest(next.access_token).catch(() => undefined);
      throw new Error('La sesión cambió durante el acceso');
    }
    sessionRef.current = next;
    setSession(next);
    return next.user;
  }, [persist, persistOperationalSession]);

  const value = useMemo<AuthContextValue>(() => ({
    isLoading,
    session,
    user: session?.user ?? null,
    biometricProfile,
    biometricAvailable,
    async login(email, password) {
      await logoutPromise.current;
      const version = ++sessionVersion.current;
      const next = await loginRequest(email, password);
      const canUseMobile = next.user.permissions.includes('*') || next.user.permissions.includes('mobile.access');
      if (!canUseMobile) throw new Error('Tu usuario no tiene acceso a MYC Mobile');
      return applySession(next, version);
    },
    async biometricLogin() {
      await logoutPromise.current;
      const credential = await readBiometricCredential();
      if (!credential) {
        // SecureStore's own contract: a resolved `null` here (as opposed to a
        // rejection) means the entry was invalidated by a device-level
        // biometric change. Clear both keys so the login screen falls back
        // to password instead of offering a biometric button that can never
        // succeed again.
        await clearBiometricEnrollment();
        biometricProfileRef.current = null;
        setBiometricProfile(null);
        throw new Error('Tu acceso biométrico debe configurarse nuevamente.');
      }
      const version = ++sessionVersion.current;
      let next: TokenPair;
      try {
        next = await exchangeBiometricRequest(credential);
      } catch (error) {
        if (error instanceof ApiError && (error.status === 401 || error.status === 403)) {
          await clearBiometricEnrollment();
          biometricProfileRef.current = null;
          setBiometricProfile(null);
        }
        throw error;
      }
      return applySession(next, version);
    },
    async enableBiometric() {
      const current = sessionRef.current;
      if (!current) throw new Error('Sesión no disponible');
      const availability = await getBiometricAvailability();
      if (!availability.available || !availability.enrolled) {
        throw new Error('Este dispositivo no tiene biometría configurada');
      }
      const confirmed = await authenticateBiometric('Confirma tu identidad para activar el acceso biométrico');
      if (!confirmed) throw new Error('No fue posible validar tu biometría');
      const enrolled = await enrollBiometricRequest(current.access_token);
      await writeBiometricCredential(enrolled.biometric_credential);
      const profile: BiometricProfile = {
        user_id: current.user.id,
        email: current.user.email,
        full_name: current.user.full_name,
        biometric_label: availability.label,
      };
      await writeBiometricProfile(profile);
      // Biometric storage is now durable (credential + profile both written):
      // only now is it safe to drop the plain password-login TokenPair that
      // may have been persisted to disk before biometry was enabled, so a
      // cold start relies on biometry instead of resurrecting it. The active
      // session already in memory (sessionRef/session state) is untouched --
      // this clears disk persistence only, never the in-flight session.
      await persist(clearSession);
      biometricProfileRef.current = profile;
      setBiometricProfile(profile);
    },
    async disableBiometric() {
      const current = sessionRef.current;
      if (current) {
        // Best-effort: local biometric access is what actually matters here.
        // A network failure never blocks disabling on this device; see
        // docs/closures/BIOMETRIC_2_BIOMETRIC_LOGIN.md for the accepted risk.
        await revokeBiometricRequest(current.access_token).catch(() => undefined);
      }
      await clearBiometricEnrollment();
      biometricProfileRef.current = null;
      setBiometricProfile(null);
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
            await deactivateCurrentDevice(current.access_token).catch(() => undefined);
            await logoutRequest(current.access_token).catch(() => undefined);
          }
        } finally {
          // Biometric enrollment is a device capability, not a session: logout
          // never touches it. Only the explicit "disable biometric" action does.
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
  }), [isLoading, persist, applySession, refreshSession, session, biometricProfile, biometricAvailable]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth requiere AuthProvider');
  return context;
}
