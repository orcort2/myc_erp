import { API_BASE_URL } from '@/src/config/environment';
import {
  createMobileDeveloperClient,
  type DeveloperSessionOpened,
  type DeveloperSessionStatus,
} from '@/src/services/mobile-developer-client';

const developerClient = createMobileDeveloperClient(API_BASE_URL);

export async function openDeveloperSession(
  accessToken: string,
  biometricCredential: string,
): Promise<DeveloperSessionOpened> {
  return developerClient.open(accessToken, biometricCredential);
}

export async function getDeveloperSessionStatus(
  accessToken: string,
  developerToken: string,
): Promise<DeveloperSessionStatus> {
  return developerClient.status(accessToken, developerToken);
}

export async function lockDeveloperSession(
  accessToken: string,
  developerToken: string,
): Promise<void> {
  return developerClient.lock(accessToken, developerToken);
}
