import { API_BASE_URL } from '@/src/config/environment';

export type ApiErrorDetail = {
  message: string;
  missingFields: string[] | null;
};

/**
 * Lee el detalle de un error HTTP conservando `missing_fields` cuando el
 * motor backend ya lo produce (p.ej. FieldSheet `/complete`, `detail: {
 * message, missing_fields }`), en vez de aplanarlo a un solo string. Consume
 * el body de `response`; no debe llamarse dos veces sobre la misma Response.
 */
export async function readApiErrorDetail(response: Response): Promise<ApiErrorDetail> {
  try {
    const body = await response.json();
    if (typeof body.detail === 'string') return { message: body.detail, missingFields: null };
    if (body.detail?.message) {
      const missingFields = Array.isArray(body.detail.missing_fields)
        ? body.detail.missing_fields.map((item: unknown) => String(item))
        : null;
      return { message: body.detail.message, missingFields };
    }
  } catch {
    // El backend puede responder PDF/ZIP o un error sin JSON.
  }
  return { message: `Error del servidor (${response.status})`, missingFields: null };
}

export async function readApiError(response: Response): Promise<string> {
  return (await readApiErrorDetail(response)).message;
}

/** Error HTTP enriquecido con el status y, si el backend lo produjo, la lista
 * estructurada de campos faltantes — para que la UI distinga un dato técnico
 * incompleto de un fallo de red/servidor genérico sin volver a parsear nada. */
export class ApiError extends Error {
  readonly status: number;
  readonly missingFields: string[] | null;

  constructor(message: string, status: number, missingFields: string[] | null = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.missingFields = missingFields;
  }
}

export function apiUrl(path: string): string {
  return `${API_BASE_URL}${path.startsWith('/') ? path : `/${path}`}`;
}
