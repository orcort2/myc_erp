import { ApiError, readApiError } from '@/src/api/error-detail';
import type { MobileSecurityDeviceInput, TokenPair } from '@/src/types/auth';

type FetchLike = typeof fetch;

export type BiometricEnrollResponse = {
  biometric_credential: string;
  expires_at: string;
};

export function isLegacyRefreshToken(token: string): boolean {
  // Dispatch by standard compact JWT shape; only the backend verifies its claims/signature.
  return /^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$/.test(token);
}

async function parseResponse(response: Response): Promise<TokenPair> {
  const body = await response.json();
  if (!response.ok) {
    throw new Error(typeof body.detail === 'string' ? body.detail : 'No fue posible iniciar sesión');
  }
  return body as TokenPair;
}

// Biometric calls carry the HTTP status on the thrown error: AuthProvider
// needs to tell a definitive 401/403 (credential/device/account no longer
// valid) apart from a transient network failure before touching local storage.
async function parseJsonOrThrowApiError<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw new ApiError(await readApiError(response), response.status);
  }
  return (await response.json()) as T;
}

export function createMobileAuthClient(apiBaseUrl: string, request: FetchLike = fetch) {
  return {
    async login(email: string, password: string, device: MobileSecurityDeviceInput): Promise<TokenPair> {
      return parseResponse(
        await request(`${apiBaseUrl}/mobile/v1/auth/login`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email: email.trim().toLowerCase(), password, device }),
        }),
      );
    },

    async refresh(refreshToken: string, device?: MobileSecurityDeviceInput): Promise<TokenPair> {
      const legacy = isLegacyRefreshToken(refreshToken);
      if (legacy && !device) throw new Error('La migración de sesión requiere el dispositivo de seguridad');
      return parseResponse(
        await request(`${apiBaseUrl}/mobile/v1/auth/refresh`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: refreshToken, ...(legacy ? { device } : {}) }),
        }),
      );
    },

    async logout(accessToken: string): Promise<void> {
      const response = await request(`${apiBaseUrl}/mobile/v1/auth/logout`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${accessToken}` },
      });
      if (!response.ok) throw new Error('No fue posible revocar la sesión Mobile');
    },

    async enrollBiometric(accessToken: string): Promise<BiometricEnrollResponse> {
      return parseJsonOrThrowApiError(
        await request(`${apiBaseUrl}/mobile/v1/auth/biometric/enroll`, {
          method: 'POST',
          headers: { Authorization: `Bearer ${accessToken}` },
        }),
      );
    },

    async exchangeBiometric(biometricCredential: string): Promise<TokenPair> {
      return parseJsonOrThrowApiError(
        await request(`${apiBaseUrl}/mobile/v1/auth/biometric/exchange`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ biometric_credential: biometricCredential }),
        }),
      );
    },

    async revokeBiometric(accessToken: string): Promise<void> {
      const response = await request(`${apiBaseUrl}/mobile/v1/auth/biometric`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${accessToken}` },
      });
      if (!response.ok) throw new ApiError(await readApiError(response), response.status);
    },
  };
}
