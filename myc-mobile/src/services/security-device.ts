import Constants from 'expo-constants';
import * as Crypto from 'expo-crypto';
import * as Device from 'expo-device';
import * as SecureStore from 'expo-secure-store';
import { Platform } from 'react-native';

import type { MobileSecurityDeviceInput } from '@/src/types/auth';

const SECURITY_DEVICE_KEY = 'myc.security.device_uuid.v1';
let devicePromise: Promise<string> | null = null;

export function getSecurityDeviceUuid(): Promise<string> {
  if (!devicePromise) {
    devicePromise = (async () => {
      const stored = await SecureStore.getItemAsync(SECURITY_DEVICE_KEY);
      if (stored) return stored;
      const uuid = Crypto.randomUUID();
      await SecureStore.setItemAsync(SECURITY_DEVICE_KEY, uuid);
      return uuid;
    })().finally(() => { devicePromise = null; });
  }
  return devicePromise;
}

export async function getSecurityDevice(): Promise<MobileSecurityDeviceInput> {
  if (Platform.OS !== 'ios' && Platform.OS !== 'android') {
    throw new Error('La sesión Mobile requiere iOS o Android');
  }
  return {
    device_uuid: await getSecurityDeviceUuid(),
    platform: Platform.OS,
    device_name: Device.deviceName ?? null,
    app_version: Constants.expoConfig?.version ?? null,
  };
}
