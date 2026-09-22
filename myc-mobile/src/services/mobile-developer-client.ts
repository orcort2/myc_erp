import { ApiError, readApiError } from '@/src/api/error-detail';

type FetchLike = typeof fetch;

export type DeveloperSessionOpened = {
  developer_token: string;
  expires_at: string;
  session_id: number;
};

export type DeveloperSessionStatus = {
  active: boolean;
  expires_at: string | null;
  remaining_seconds: number | null;
  user_id: number | null;
  device_id: number | null;
};

// Every call carries the Mobile Bearer token: DEV-0's endpoints are Mobile
// routes first (mobile.access is enforced by the global gate) and Developer
// routes second. open() is additionally gated server-side on developer.access
// + internal actor; status()/lock() additionally require the opaque
// Developer token in its own header, never mixed into the JWT.
export function createMobileDeveloperClient(apiBaseUrl: string, request: FetchLike = fetch) {
  return {
    async open(accessToken: string, biometricCredential: string): Promise<DeveloperSessionOpened> {
      const response = await request(`${apiBaseUrl}/mobile/v1/developer/session`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${accessToken}`,
        },
        body: JSON.stringify({ biometric_credential: biometricCredential }),
      });
      if (!response.ok) throw new ApiError(await readApiError(response), response.status);
      return (await response.json()) as DeveloperSessionOpened;
    },

    async status(accessToken: string, developerToken: string): Promise<DeveloperSessionStatus> {
      const response = await request(`${apiBaseUrl}/mobile/v1/developer/session`, {
        method: 'GET',
        headers: {
          Authorization: `Bearer ${accessToken}`,
          'X-MYC-Developer-Token': developerToken,
        },
      });
      if (!response.ok) throw new ApiError(await readApiError(response), response.status);
      return (await response.json()) as DeveloperSessionStatus;
    },

    async lock(accessToken: string, developerToken: string): Promise<void> {
      const response = await request(`${apiBaseUrl}/mobile/v1/developer/session`, {
        method: 'DELETE',
        headers: {
          Authorization: `Bearer ${accessToken}`,
          'X-MYC-Developer-Token': developerToken,
        },
      });
      if (!response.ok) throw new ApiError(await readApiError(response), response.status);
    },
  };
}
