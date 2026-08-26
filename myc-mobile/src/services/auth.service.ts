import { API_BASE_URL } from '@/src/config/environment';
import { createMobileAuthClient } from '@/src/services/mobile-auth-client';
import type { TokenPair } from '@/src/types/auth';

const mobileAuthClient = createMobileAuthClient(API_BASE_URL);

export async function login(email: string, password: string): Promise<TokenPair> {
  return mobileAuthClient.login(email, password);
}

export async function refresh(refreshToken: string): Promise<TokenPair> {
  return mobileAuthClient.refresh(refreshToken);
}
