import type { TokenPair } from '@/src/types/auth';

type FetchLike = typeof fetch;

async function parseResponse(response: Response): Promise<TokenPair> {
  const body = await response.json();
  if (!response.ok) {
    throw new Error(typeof body.detail === 'string' ? body.detail : 'No fue posible iniciar sesión');
  }
  return body as TokenPair;
}

export function createMobileAuthClient(apiBaseUrl: string, request: FetchLike = fetch) {
  return {
    async login(email: string, password: string): Promise<TokenPair> {
      return parseResponse(
        await request(`${apiBaseUrl}/mobile/v1/auth/login`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email: email.trim().toLowerCase(), password }),
        }),
      );
    },

    async refresh(refreshToken: string): Promise<TokenPair> {
      return parseResponse(
        await request(`${apiBaseUrl}/mobile/v1/auth/refresh`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: refreshToken }),
        }),
      );
    },
  };
}
