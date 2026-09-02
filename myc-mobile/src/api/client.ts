import { API_BASE_URL } from '@/src/config/environment';

export type ApiErrorDetail = {
  message: string;
  missingFields: string[] | null;
  // Cierre UX 2026-09: algunos endpoints devuelven detail: {code, items}
  // (p.ej. LAB_DRAFT_SHEETS_REQUIRE_CONFIRMATION/LAB_DRAFT_SHEETS_INVALID)
  // en vez de {message, missing_fields} -- se conservan crudos para que la
  // UI decida cómo presentarlos (confirmar, listar blockers) sin volver a
  // golpear el endpoint ni adivinar la forma del error.
  code: string | null;
  items: Record<string, unknown>[] | null;
};

/**
 * Lee el detalle de un error HTTP conservando `missing_fields`/`code`/`items`
 * cuando el motor backend ya los produce, en vez de aplanarlos a un solo
 * string. Consume el body de `response`; no debe llamarse dos veces sobre la
 * misma Response.
 */
export async function readApiErrorDetail(response: Response): Promise<ApiErrorDetail> {
  try {
    const body = await response.json();
    if (typeof body.detail === 'string') {
      return { message: body.detail, missingFields: null, code: null, items: null };
    }
    if (body.detail?.message) {
      const missingFields = Array.isArray(body.detail.missing_fields)
        ? body.detail.missing_fields.map((item: unknown) => String(item))
        : null;
      return { message: body.detail.message, missingFields, code: null, items: null };
    }
    if (body.detail?.code) {
      const items = Array.isArray(body.detail.items) ? body.detail.items : null;
      return { message: String(body.detail.code), missingFields: null, code: String(body.detail.code), items };
    }
  } catch {
    // El backend puede responder PDF/ZIP o un error sin JSON.
  }
  return { message: `Error del servidor (${response.status})`, missingFields: null, code: null, items: null };
}

export async function readApiError(response: Response): Promise<string> {
  return (await readApiErrorDetail(response)).message;
}

/** Error HTTP enriquecido con el status y, si el backend lo produjo, la lista
 * estructurada de campos faltantes o el code/items estructurado — para que
 * la UI distinga un dato técnico incompleto (o una confirmación pendiente)
 * de un fallo de red/servidor genérico sin volver a parsear nada. */
export class ApiError extends Error {
  readonly status: number;
  readonly missingFields: string[] | null;
  readonly code: string | null;
  readonly items: Record<string, unknown>[] | null;

  constructor(
    message: string,
    status: number,
    missingFields: string[] | null = null,
    code: string | null = null,
    items: Record<string, unknown>[] | null = null,
  ) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.missingFields = missingFields;
    this.code = code;
    this.items = items;
  }
}

export function apiUrl(path: string): string {
  return `${API_BASE_URL}${path.startsWith('/') ? path : `/${path}`}`;
}
