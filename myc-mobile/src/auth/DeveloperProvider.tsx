import { createContext, PropsWithChildren, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { AppState } from 'react-native';

import { useAuth } from '@/src/auth/AuthProvider';
import { hasDeveloperCapability } from '@/src/permissions/developer-policy';
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
//
// The local countdown is UX only; the backend stays the authority. Server
// state is reconciled (GET /developer/session) only on discrete lifecycle
// events -- never by polling, and never while Developer is locked:
//   - the app returns to foreground (AppState 'active');
//   - the Developer Center is (re)entered (the screen calls
//     refreshDeveloperStatus on mount);
//   - the Mobile access token changes (a refresh rotation ends the
//     DeveloperSession server-side).
// Losing the explicit Developer capability locally (permissions refreshed,
// logout) locks immediately, without waiting for any request or countdown.
// isDeveloperUnlocked is a UI hint only: no server operation may trust it.
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
  const isDeveloperAvailable = hasDeveloperCapability(user);
  const accessToken = session?.access_token ?? null;
  // Developer may only be held while there is a Mobile session AND the
  // explicit capability -- any true -> false transition locks at once.
  const canHoldDeveloper = accessToken !== null && isDeveloperAvailable;

  const [developerToken, setDeveloperToken] = useState<string | null>(null);
  const [remainingSeconds, setRemainingSeconds] = useState<number | null>(null);
  const [showExpirationWarning, setShowExpirationWarning] = useState(false);

  const developerTokenRef = useRef<string | null>(null);
  const accessTokenRef = useRef<string | null>(accessToken);
  // The Mobile access token the current DeveloperSession is bound to: still
  // the right credential for a best-effort server-side lock once the
  // provider no longer sees a session (logout).
  const boundAccessTokenRef = useRef<string | null>(null);
  const expiresAtRef = useRef<number | null>(null);
  // Bumped on logout, capability loss or an explicit lock; an in-flight
  // unlockDeveloper()/reconciliation that observes its own captured version
  // go stale must discard its result.
  const versionRef = useRef(0);
  // Exactly one warning per expiration cycle -- never re-shown just because
  // a re-render (or a reconciliation) happened while remainingSeconds is
  // still <= threshold.
  const warnedRef = useRef(false);
  const tickRef = useRef<ReturnType<typeof setInterval> | null>(null);
  // Dedupes overlapping reconciliations of the SAME Developer token
  // (e.g. foreground + screen entry at once).
  const reconcileRef = useRef<{ token: string; pending: Promise<void> } | null>(null);

  accessTokenRef.current = accessToken;

  const stopTicking = useCallback(() => {
    if (tickRef.current) {
      clearInterval(tickRef.current);
      tickRef.current = null;
    }
  }, []);

  const clearLocal = useCallback(() => {
    stopTicking();
    developerTokenRef.current = null;
    boundAccessTokenRef.current = null;
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

  // newCycle: a fresh DeveloperSession (unlock/extend) re-arms the warning;
  // a reconciliation of the SAME session only re-syncs the clock.
  const startTicking = useCallback((expiresAtIso: string, newCycle: boolean) => {
    stopTicking();
    expiresAtRef.current = new Date(expiresAtIso).getTime();
    if (newCycle) {
      warnedRef.current = false;
      setShowExpirationWarning(false);
    }
    tick();
    tickRef.current = setInterval(tick, TICK_MS);
  }, [stopTicking, tick]);

  // Immediate local lock that never depends on the current render's session;
  // best-effort server revoke with whatever Mobile credential is left.
  const discardDeveloper = useCallback(() => {
    versionRef.current += 1;
    const token = developerTokenRef.current;
    const credential = accessTokenRef.current ?? boundAccessTokenRef.current;
    clearLocal();
    if (token && credential) {
      // If the Mobile session is already gone (logout), the backend's live
      // revalidation independently invalidates this DeveloperSession anyway.
      lockDeveloperSession(credential, token).catch(() => undefined);
    }
  }, [clearLocal]);

  // Logout OR loss of the explicit Developer capability must leave Developer
  // locked immediately -- including when it races an in-flight
  // unlockDeveloper() still waiting on biometry/network.
  useEffect(() => {
    if (canHoldDeveloper) return;
    discardDeveloper();
  }, [canHoldDeveloper, discardDeveloper]);

  useEffect(() => stopTicking, [stopTicking]);

  const lockDeveloper = useCallback(async () => {
    versionRef.current += 1;
    const token = developerTokenRef.current;
    const credential = accessTokenRef.current;
    clearLocal();
    if (token && credential) {
      await lockDeveloperSession(credential, token).catch(() => undefined);
    }
  }, [clearLocal]);

  const unlockDeveloper = useCallback(async () => {
    if (!isDeveloperAvailable) throw new Error('Tu usuario no tiene acceso a Developer');
    const credentialAccessToken = accessTokenRef.current;
    if (!credentialAccessToken) throw new Error('Sesión no disponible');
    const version = versionRef.current;
    // requireAuthentication SecureStore read: the OS itself demands Face
    // ID/Touch ID/fingerprint here. A boolean "Face ID passed" is never
    // sent to the backend -- only this real, server-verifiable credential.
    const credential = await readBiometricCredential();
    if (!credential) throw new Error('Configura tu acceso biométrico para usar Developer');
    const opened = await openDeveloperSession(credentialAccessToken, credential);
    if (version !== versionRef.current || accessTokenRef.current !== credentialAccessToken) {
      // A logout/capability loss (or another lock/unlock) happened while we
      // were waiting.
      await lockDeveloperSession(credentialAccessToken, opened.developer_token).catch(() => undefined);
      throw new Error('La sesión cambió mientras se desbloqueaba Developer');
    }
    // Opening supersedes any previous DeveloperSession server-side (at most
    // one per trusted device); the new token replaces it locally as well.
    developerTokenRef.current = opened.developer_token;
    boundAccessTokenRef.current = credentialAccessToken;
    setDeveloperToken(opened.developer_token);
    startTicking(opened.expires_at, true);
  }, [isDeveloperAvailable, startTicking]);

  // Fail-closed: a network error also locks locally -- a fresh biometric
  // unlock is always available, a stale "unlocked" UI is not acceptable.
  const refreshDeveloperStatus = useCallback((): Promise<void> => {
    const token = developerTokenRef.current;
    const credential = accessTokenRef.current;
    if (!token || !credential) return Promise.resolve();
    if (reconcileRef.current?.token === token) return reconcileRef.current.pending;
    const version = versionRef.current;
    const pending = (async () => {
      try {
        const status = await getDeveloperSessionStatus(credential, token).catch(() => null);
        // Superseded meanwhile by a lock, logout, capability loss or a new unlock.
        if (version !== versionRef.current || developerTokenRef.current !== token) return;
        if (!status?.active || !status.expires_at) {
          clearLocal();
          return;
        }
        boundAccessTokenRef.current = credential;
        startTicking(status.expires_at, false);
      } finally {
        if (reconcileRef.current?.token === token) reconcileRef.current = null;
      }
    })();
    reconcileRef.current = { token, pending };
    return pending;
  }, [clearLocal, startTicking]);

  // Foreground reconciliation: one listener for the provider's lifetime,
  // removed on unmount. refreshDeveloperStatus is stable and reads refs, so
  // the listener never holds a stale closure.
  useEffect(() => {
    const subscription = AppState.addEventListener('change', (nextState) => {
      if (nextState === 'active') refreshDeveloperStatus().catch(() => undefined);
    });
    return () => subscription.remove();
  }, [refreshDeveloperStatus]);

  // A different Mobile access token (refresh rotation) is a different
  // MobileAuthSession generation: let the backend confirm the Developer
  // token is no longer bound to it instead of trusting the countdown.
  useEffect(() => {
    const bound = boundAccessTokenRef.current;
    if (!accessToken || !bound || accessToken === bound) return;
    refreshDeveloperStatus().catch(() => undefined);
  }, [accessToken, refreshDeveloperStatus]);

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
