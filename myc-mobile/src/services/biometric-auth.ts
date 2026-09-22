import * as LocalAuthentication from 'expo-local-authentication';
import { Platform } from 'react-native';

export type BiometricType = 'face_id' | 'touch_id' | 'fingerprint' | 'biometric' | 'none';

export type BiometricAvailability = {
  available: boolean;
  enrolled: boolean;
  type: BiometricType;
  label: string;
};

function resolveTypeAndLabel(types: LocalAuthentication.AuthenticationType[]): { type: BiometricType; label: string } {
  const hasFacial = types.includes(LocalAuthentication.AuthenticationType.FACIAL_RECOGNITION);
  const hasFingerprint = types.includes(LocalAuthentication.AuthenticationType.FINGERPRINT);
  if (Platform.OS === 'ios') {
    if (hasFacial) return { type: 'face_id', label: 'Face ID' };
    if (hasFingerprint) return { type: 'touch_id', label: 'Touch ID' };
  } else if (Platform.OS === 'android') {
    if (hasFingerprint || hasFacial || types.includes(LocalAuthentication.AuthenticationType.IRIS)) {
      return { type: 'fingerprint', label: 'Huella' };
    }
  }
  return { type: 'biometric', label: 'Biometría' };
}

export async function getBiometricAvailability(): Promise<BiometricAvailability> {
  const available = await LocalAuthentication.hasHardwareAsync();
  if (!available) {
    return { available: false, enrolled: false, type: 'none', label: 'Biometría' };
  }
  const [enrolled, types] = await Promise.all([
    LocalAuthentication.isEnrolledAsync(),
    LocalAuthentication.supportedAuthenticationTypesAsync(),
  ]);
  return { available: true, enrolled, ...resolveTypeAndLabel(types) };
}

export async function authenticateBiometric(reason: string): Promise<boolean> {
  const result = await LocalAuthentication.authenticateAsync({
    promptMessage: reason,
    cancelLabel: 'Cancelar',
    // Biometry only: a device PIN/passcode fallback would silently downgrade
    // the security guarantee this feature exists to provide.
    disableDeviceFallback: true,
    biometricsSecurityLevel: 'strong',
  });
  return result.success;
}
