import * as SecureStore from 'expo-secure-store';

const PROFILE_KEY = 'myc.biometric.profile.v1';
const CREDENTIAL_KEY = 'myc.biometric.credential.v1';

export type BiometricProfile = {
  user_id: number;
  email: string;
  full_name: string;
  biometric_label: string;
};

// Not secret: only lets the login screen greet the user and offer biometric
// entry before any credential is touched. Never requires authentication to read.
export async function readBiometricProfile(): Promise<BiometricProfile | null> {
  const stored = await SecureStore.getItemAsync(PROFILE_KEY);
  if (!stored) return null;
  try {
    return JSON.parse(stored) as BiometricProfile;
  } catch {
    await SecureStore.deleteItemAsync(PROFILE_KEY);
    return null;
  }
}

export async function writeBiometricProfile(profile: BiometricProfile): Promise<void> {
  await SecureStore.setItemAsync(PROFILE_KEY, JSON.stringify(profile));
}

export async function clearBiometricProfile(): Promise<void> {
  await SecureStore.deleteItemAsync(PROFILE_KEY);
}

// Secret: requireAuthentication makes the OS itself demand Face ID/Touch ID/
// fingerprint before releasing the value.
//
// Per SecureStore's own contract this resolves `null` in exactly two cases:
// there is no stored entry, or the platform invalidated the entry because
// the device's enrolled biometric set changed (never falls back to a PIN).
// A cancelled or failed prompt instead REJECTS -- callers must keep that
// distinction: a rejection must never be treated as "invalidated" and must
// never clear the enrollment, only a resolved `null` may.
export async function readBiometricCredential(): Promise<string | null> {
  return SecureStore.getItemAsync(CREDENTIAL_KEY, {
    requireAuthentication: true,
    keychainAccessible: SecureStore.WHEN_UNLOCKED_THIS_DEVICE_ONLY,
    authenticationPrompt: 'Ingresa con biometría para continuar',
  });
}

export async function writeBiometricCredential(credential: string): Promise<void> {
  await SecureStore.setItemAsync(CREDENTIAL_KEY, credential, {
    requireAuthentication: true,
    keychainAccessible: SecureStore.WHEN_UNLOCKED_THIS_DEVICE_ONLY,
  });
}

export async function clearBiometricCredential(): Promise<void> {
  await SecureStore.deleteItemAsync(CREDENTIAL_KEY);
}

export async function clearBiometricEnrollment(): Promise<void> {
  await Promise.all([clearBiometricProfile(), clearBiometricCredential()]);
}
