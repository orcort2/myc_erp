import type { MobileSecurityDeviceInput, TokenPair } from '@/src/types/auth';

type FetchLike = typeof fetch;

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
  };
}
