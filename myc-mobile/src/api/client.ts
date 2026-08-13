import { API_BASE_URL } from '@/src/config/environment';

export async function readApiError(response: Response): Promise<string> {
  try {
    const body = await response.json();
    if (typeof body.detail === 'string') return body.detail;
    if (body.detail?.message) return body.detail.message;
  } catch {
    // El backend puede responder PDF/ZIP o un error sin JSON.
  }
  return `Error del servidor (${response.status})`;
}

export function apiUrl(path: string): string {
  return `${API_BASE_URL}${path.startsWith('/') ? path : `/${path}`}`;
}
