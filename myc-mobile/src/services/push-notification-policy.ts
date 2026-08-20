export type RegisterDeviceTrigger = 'login' | 'foreground';

/**
 * MOB-004: how long a successful registration is trusted before a
 * 'foreground' revalidation is allowed to skip re-hitting the backend.
 * 'login' (session restore / actual login) never skips — every app cold
 * start or credential login re-confirms the device, per requirement A.
 */
export const FOREGROUND_REVALIDATE_INTERVAL_MS = 30 * 60 * 1000;

/**
 * Pure decision extracted so it can be unit-tested without mocking
 * expo-notifications/expo-device/expo-secure-store/react-native (none of
 * which resolve under the plain Node test runner used in this project).
 *
 * A changed Expo push token always forces a fresh registration attempt
 * (requirement C), regardless of trigger or elapsed time — this is how a
 * device that got a new token (reinstall, OS-level push reset) recovers
 * without waiting for the throttle window. A 'foreground' revalidation
 * with an unchanged token is only skipped within the throttle window
 * (requirement D, avoid redundant backend calls on every app switch); a
 * failed previous attempt never updates the "last success" state the
 * caller feeds in here, so the next natural trigger (foreground, login)
 * retries instead of leaving the user stuck until next login
 * (requirement F).
 */
export function shouldSkipForegroundRevalidation(
  trigger: RegisterDeviceTrigger,
  tokenChanged: boolean,
  msSinceLastSuccess: number,
): boolean {
  if (trigger !== 'foreground') return false;
  if (tokenChanged) return false;
  return msSinceLastSuccess < FOREGROUND_REVALIDATE_INTERVAL_MS;
}
