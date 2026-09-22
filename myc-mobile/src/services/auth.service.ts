import { API_BASE_URL } from '@/src/config/environment';
import { createMobileAuthClient, isLegacyRefreshToken, type BiometricEnrollResponse } from '@/src/services/mobile-auth-client';
import { getSecurityDevice } from '@/src/services/security-device';
import type { TokenPair } from '@/src/types/auth';

const mobileAuthClient = createMobileAuthClient(API_BASE_URL);

export async function login(email: string, password: string): Promise<TokenPair> {
  return mobileAuthClient.login(email, password, await getSecurityDevice());
}

export async function refresh(refreshToken: string): Promise<TokenPair> {
  return mobileAuthClient.refresh(refreshToken, isLegacyRefreshToken(refreshToken) ? await getSecurityDevice() : undefined);
}

export async function logout(accessToken: string): Promise<void> {
  return mobileAuthClient.logout(accessToken);
}

export async function enrollBiometric(accessToken: string): Promise<BiometricEnrollResponse> {
  return mobileAuthClient.enrollBiometric(accessToken);
}

export async function exchangeBiometric(biometricCredential: string): Promise<TokenPair> {
  return mobileAuthClient.exchangeBiometric(biometricCredential);
}

export async function revokeBiometric(accessToken: string): Promise<void> {
  return mobileAuthClient.revokeBiometric(accessToken);
}
