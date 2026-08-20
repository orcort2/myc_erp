import Constants from 'expo-constants';
import * as Device from 'expo-device';
import * as Notifications from 'expo-notifications';
import * as SecureStore from 'expo-secure-store';
import { Platform } from 'react-native';

import { apiUrl } from '@/src/api/client';
import { shouldSkipForegroundRevalidation, type RegisterDeviceTrigger } from '@/src/services/push-notification-policy';

const DEVICE_ID_KEY = 'myc_push_device_id';

export type RegisterDeviceResult =
  | { ok: true; deviceId: number; skipped: boolean }
  | {
      ok: false;
      reason:
        | 'not_device'
        | 'permission_denied'
        | 'missing_project_id'
        | 'token_error'
        | 'network_error'
        | 'backend_rejected';
    };

/**
 * In-memory record of the last confirmed registration. Reset on every app
 * cold start on purpose: requirement A (register/revalidate after
 * session restore or login) must always attempt at least once per launch.
 * Only 'foreground' revalidations (requirement B) consult this to decide
 * whether the backend call can be skipped (requirement D).
 */
let lastSuccessToken: string | null = null;
let lastSuccessAt = 0;
let lastSuccessDeviceId: number | null = null;
let inFlight: Promise<RegisterDeviceResult> | null = null;

export async function registerCurrentDevice(
  authorizedFetch: (url: string, init?: RequestInit) => Promise<Response>,
  trigger: RegisterDeviceTrigger = 'login',
): Promise<RegisterDeviceResult> {
  if (inFlight) return inFlight;
  inFlight = attemptRegistration(authorizedFetch, trigger);
  try {
    return await inFlight;
  } finally {
    inFlight = null;
  }
}

async function attemptRegistration(
  authorizedFetch: (url: string, init?: RequestInit) => Promise<Response>,
  trigger: RegisterDeviceTrigger,
): Promise<RegisterDeviceResult> {
  if (!Device.isDevice) return { ok: false, reason: 'not_device' };

  const current = await Notifications.getPermissionsAsync();
  const permission = current.status === 'undetermined'
    ? await Notifications.requestPermissionsAsync()
    : current;
  if (permission.status !== 'granted') {
    console.warn(`[push-notifications] registro omitido (trigger=${trigger}): permiso ${permission.status}`);
    return { ok: false, reason: 'permission_denied' };
  }

  if (Platform.OS === 'android') {
    await Notifications.setNotificationChannelAsync('operational', {
      name: 'Operación MYC',
      importance: Notifications.AndroidImportance.HIGH,
    }).catch((error) => console.warn('[push-notifications] no fue posible configurar el canal Android', error));
  }

  const projectId = Constants.expoConfig?.extra?.eas?.projectId
    ?? Constants.easConfig?.projectId;
  if (!projectId) {
    console.warn('[push-notifications] registro omitido: projectId ausente en la configuración de EAS');
    return { ok: false, reason: 'missing_project_id' };
  }

  let token: string;
  try {
    token = (await Notifications.getExpoPushTokenAsync({ projectId })).data;
  } catch (error) {
    console.warn('[push-notifications] no fue posible obtener el Expo push token', error);
    return { ok: false, reason: 'token_error' };
  }

  const tokenChanged = token !== lastSuccessToken;
  if (shouldSkipForegroundRevalidation(trigger, tokenChanged, Date.now() - lastSuccessAt)) {
    return { ok: true, deviceId: lastSuccessDeviceId as number, skipped: true };
  }

  let response: Response;
  try {
    response = await authorizedFetch(apiUrl('/mobile/v1/notifications/devices'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        expo_push_token: token,
        platform: Platform.OS,
        device_name: Device.deviceName ?? null,
        app_version: Constants.expoConfig?.version ?? null,
      }),
    });
  } catch (error) {
    console.warn(`[push-notifications] fallo de red registrando el dispositivo (trigger=${trigger})`, error);
    return { ok: false, reason: 'network_error' };
  }

  if (!response.ok) {
    console.warn(`[push-notifications] el backend rechazó el registro del dispositivo (trigger=${trigger}, status=${response.status})`);
    return { ok: false, reason: 'backend_rejected' };
  }

  const device = await response.json() as { id: number };
  await SecureStore.setItemAsync(DEVICE_ID_KEY, String(device.id));
  lastSuccessToken = token;
  lastSuccessAt = Date.now();
  lastSuccessDeviceId = device.id;
  return { ok: true, deviceId: device.id, skipped: false };
}

export async function deactivateCurrentDevice(accessToken: string): Promise<void> {
  const deviceId = await SecureStore.getItemAsync(DEVICE_ID_KEY);
  if (!deviceId) return;
  try {
    await fetch(apiUrl(`/mobile/v1/notifications/devices/${deviceId}`), {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${accessToken}` },
    });
  } finally {
    await SecureStore.deleteItemAsync(DEVICE_ID_KEY);
    lastSuccessToken = null;
    lastSuccessAt = 0;
    lastSuccessDeviceId = null;
  }
}
