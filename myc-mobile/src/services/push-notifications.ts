import Constants from 'expo-constants';
import * as Device from 'expo-device';
import * as Notifications from 'expo-notifications';
import * as SecureStore from 'expo-secure-store';
import { Platform } from 'react-native';

import { apiUrl } from '@/src/api/client';

const DEVICE_ID_KEY = 'myc_push_device_id';

export async function registerCurrentDevice(
  authorizedFetch: (url: string, init?: RequestInit) => Promise<Response>,
): Promise<number | null> {
  if (!Device.isDevice) return null;
  const current = await Notifications.getPermissionsAsync();
  const permission = current.status === 'undetermined'
    ? await Notifications.requestPermissionsAsync()
    : current;
  if (permission.status !== 'granted') return null;

  if (Platform.OS === 'android') {
    await Notifications.setNotificationChannelAsync('operational', {
      name: 'Operación MYC',
      importance: Notifications.AndroidImportance.HIGH,
    });
  }
  const projectId = Constants.expoConfig?.extra?.eas?.projectId
    ?? Constants.easConfig?.projectId;
  if (!projectId) return null;
  const token = (await Notifications.getExpoPushTokenAsync({ projectId })).data;
  const response = await authorizedFetch(apiUrl('/mobile/v1/notifications/devices'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      expo_push_token: token,
      platform: Platform.OS,
      device_name: Device.deviceName ?? null,
      app_version: Constants.expoConfig?.version ?? null,
    }),
  });
  if (!response.ok) return null;
  const device = await response.json() as { id: number };
  await SecureStore.setItemAsync(DEVICE_ID_KEY, String(device.id));
  return device.id;
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
  }
}
