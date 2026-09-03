import { API_BASE_URL } from '@/src/config/environment';

export { ApiError, readApiError, readApiErrorDetail, humanizeErrorMessage } from './error-detail';
export type { ApiErrorDetail, FieldError } from './error-detail';

export function apiUrl(path: string): string {
  return `${API_BASE_URL}${path.startsWith('/') ? path : `/${path}`}`;
}
