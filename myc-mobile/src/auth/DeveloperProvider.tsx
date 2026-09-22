import { createContext, PropsWithChildren, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';

import { useAuth } from '@/src/auth/AuthProvider';
import { hasPermission } from '@/src/permissions/permissions';
import {
  getDeveloperSessionStatus,
  lockDeveloperSession,
  openDeveloperSession,
} from '@/src/services/developer.service';
import { readBiometricCredential } from '@/src/storage/biometric-storage';

// DEV-0: Developer is a privilege session layered on top of the Mobile
// session, with its own (shorter, non-renewing) lifecycle -- it is
// deliberately its own provider, never folded into AuthProvider. Its token
// lives in memory ONLY (never SecureStore/AsyncStorage/filesystem): a cold
// start (process killed) must always come back locked, same invariant
// BIOMETRIC-2 already applies to the operational Mobile session.
const WARNING_THRESHOLD_SECONDS = 60;
const TICK_MS = 1000;

type DeveloperContextValue = {
  isDeveloperAvailable: boolean;
  isDeveloperUnlocked: boolean;
  remainingSeconds: number | null;
  showExpirationWarning: boolean;
  unlockDeveloper(): Promise<void>;
  lockDeveloper(): Promise<void>;
  dismissExpirationWarning(): void;
  refreshDeveloperStatus(): Promise<void>;
};

const DeveloperContext = createContext<DeveloperContextValue | null>(null);

export function DeveloperProvider({ children }: PropsWithChildren) {
  const { session, user } = useAuth();
  const isDeveloperAvailable = hasPermission(user?.permissions ?? [], 'developer.access');

  const [developerToken, setDeveloperToken] = useState<string | null>(null);
  const [remainingSeconds, setRemainingSeconds] = useState<number | null>(null);
  const [showExpirationWarning, setShowExpirationWarning] = useState(false);

  const developerTokenRef = useRef<string | null>(null);
  const accessTokenRef = useRef<string | null>(session?.access_token ?? null);
  const expiresAtRef = useRef<number | null>(null);
  // Bumped on logout or an explicit lock; an in-flight unlockDeveloper() that
  // observes its own captured version go stale must discard its result.
  const versionRef = useRef(0);
  // Exactly one warning per expiration cycle -- never re-shown just because
  // a re-render happened while remainingSeconds is still <= threshold.
  const warnedRef = useRef(false);
  const tickRef = useRef<ReturnType<typeof setInterval> | null>(null);

  accessTokenRef.current = session?.access_token ?? null;

  const stopTicking = useCallback(() => {
    if (tickRef.current) {
      clearInterval(tickRef.current);
      tickRef.current = null;
    }
  }, []);

  const clearLocal = useCallback(() => {
    stopTicking();
    developerTokenRef.current = null;
    expiresAtRef.current = null;
    warnedRef.current = false;
    setDeveloperToken(null);
    setRemainingSeconds(null);
    setShowExpirationWarning(false);
  }, [stopTicking]);

  const tick = useCallback(() => {
    const expiresAt = expiresAtRef.current;
    if (expiresAt === null) return;
    const remaining = Math.max(0, Math.round((expiresAt - Date.now()) / 1000));
    setRemainingSeconds(remaining);
    if (remaining <= 0) {
      // Natural expiry: never kill anything server-side beyond this
      // DeveloperSession -- there is no ShellSession yet in DEV-0. The
      // backend independently expires/lazily-revokes the same row; this
      // only forgets the token locally so the UI locks immediately.
      clearLocal();
      return;
    }
    if (remaining <= WARNING_THRESHOLD_SECONDS) {
      if (!warnedRef.current) {
        warnedRef.current = true;
        setShowExpirationWarning(true);
      }
    } else if (warnedRef.current) {
      warnedRef.current = false;
      setShowExpirationWarning(false);
    }
  }, [clearLocal]);

  const startTicking = useCallback((expiresAtIso: string) => {
    stopTicking();
    expiresAtRef.current = new Date(expiresAtIso).getTime();
    warnedRef.current = false;
    setShowExpirationWarning(false);
    tick();
    tickRef.current = setInterval(tick, TICK_MS);
  }, [stopTicking, tick]);

  // Logout must leave Developer locked immediately -- including when it
  // races an in-flight unlockDeveloper() still waiting on Face ID/network.
  useEffect(() => {
    if (session) return;
    versionRef.current += 1;
    const token = developerTokenRef.current;
    if (token) {
      // Best-effort: the Mobile access token is already gone from this
      // provider's perspective, but AuthProvider's own logout() already
      // revoked the Mobile session server-side, which independently
      // invalidates this DeveloperSession's live authority regardless.
      lockDeveloperSession(accessTokenRef.current ?? '', token).catch(() => undefined);
    }
    clearLocal();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session]);

  useEffect(() => stopTicking, [stopTicking]);

  const lockDeveloper = useCallback(async () => {
    versionRef.current += 1;
    const token = developerTokenRef.current;
    const accessToken = accessTokenRef.current;
    clearLocal();
    if (token && accessToken) {
      await lockDeveloperSession(accessToken, token).catch(() => undefined);
    }
  }, [clearLocal]);

  const unlockDeveloper = useCallback(async () => {
    if (!isDeveloperAvailable) throw new Error('Tu usuario no tiene acceso a Developer');
    const accessToken = accessTokenRef.current;
    if (!accessToken) throw new Error('Sesión no disponible');
    const version = versionRef.current;
    // requireAuthentication SecureStore read: the OS itself demands Face
    // ID/Touch ID/fingerprint here. A boolean "Face ID passed" is never
    // sent to the backend -- only this real, server-verifiable credential.
    const credential = await readBiometricCredential();
    if (!credential) throw new Error('Configura tu acceso biométrico para usar Developer');
    const opened = await openDeveloperSession(accessToken, credential);
    if (version !== versionRef.current || accessTokenRef.current !== accessToken) {
      // A logout (or another lock/unlock) happened while we were waiting.
      await lockDeveloperSession(accessToken, opened.developer_token).catch(() => undefined);
      throw new Error('La sesión cambió mientras se desbloqueaba Developer');
    }
    developerTokenRef.current = opened.developer_token;
    setDeveloperToken(opened.developer_token);
    startTicking(opened.expires_at);
  }, [isDeveloperAvailable, startTicking]);

  const refreshDeveloperStatus = useCallback(async () => {
    const token = developerTokenRef.current;
    const accessToken = accessTokenRef.current;
    if (!token || !accessToken) return;
    const status = await getDeveloperSessionStatus(accessToken, token).catch(() => null);
    if (developerTokenRef.current !== token) return; // superseded meanwhile
    if (!status?.active) {
      clearLocal();
      return;
    }
    if (status.expires_at) startTicking(status.expires_at);
  }, [clearLocal, startTicking]);

  const dismissExpirationWarning = useCallback(() => setShowExpirationWarning(false), []);

  const value = useMemo<DeveloperContextValue>(() => ({
    isDeveloperAvailable,
    isDeveloperUnlocked: developerToken !== null,
    remainingSeconds,
    showExpirationWarning,
    unlockDeveloper,
    lockDeveloper,
    dismissExpirationWarning,
    refreshDeveloperStatus,
  }), [
    isDeveloperAvailable, developerToken, remainingSeconds, showExpirationWarning,
    unlockDeveloper, lockDeveloper, dismissExpirationWarning, refreshDeveloperStatus,
  ]);

  return <DeveloperContext.Provider value={value}>{children}</DeveloperContext.Provider>;
}

export function useDeveloper(): DeveloperContextValue {
  const context = useContext(DeveloperContext);
  if (!context) throw new Error('useDeveloper requiere DeveloperProvider');
  return context;
}
