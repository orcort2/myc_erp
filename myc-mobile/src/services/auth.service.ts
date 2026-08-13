import { API_BASE_URL } from '@/src/config/environment';
import type { TokenPair } from '@/src/types/auth';

async function parseResponse(response: Response): Promise<TokenPair> {
  const body = await response.json();
  if (!response.ok) {
    throw new Error(typeof body.detail === 'string' ? body.detail : 'No fue posible iniciar sesión');
  }
  return body as TokenPair;
}

export async function login(email: string, password: string): Promise<TokenPair> {
  return parseResponse(
    await fetch(`${API_BASE_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: email.trim().toLowerCase(), password }),
    }),
  );
}

export async function refresh(refreshToken: string): Promise<TokenPair> {
  return parseResponse(
    await fetch(`${API_BASE_URL}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    }),
  );
}
