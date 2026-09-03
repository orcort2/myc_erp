// Lógica pura de parseo/presentación de errores HTTP, separada de client.ts
// para que sea unit-testeable sin arrastrar expo-constants/RN (client.ts
// importa src/config/environment.ts, que sí los necesita).

// Cierre UX 2026-09: varios servicios backend (operational_tickets.py,
// lab_work_orders.py) todavía devuelven `detail` como un código interno
// crudo SCREAMING_SNAKE_CASE en vez de un mensaje pensado para mostrarse.
// Se traducen aquí, centralizado, para que ningún Alert de Mobile los
// muestre tal cual sin tener que tocar cada pantalla ni cambiar el contrato
// de la API (los códigos siguen viajando igual en el body).
const KNOWN_ERROR_CODE_MESSAGES: Record<string, string> = {
  OT_NOT_CLOSED: 'Esta OT todavía no está cerrada; no se puede solicitar ni ejecutar la reapertura.',
  CLOSURE_COHORT_NOT_CLOSED: 'No todos los equipos del grupo de cierre están cerrados todavía.',
  REOPEN_NOT_AUTHORIZED: 'No tienes permiso para reabrir esta OT con la política de firmas seleccionada.',
  TICKET_ALREADY_RESOLVED: 'Esta solicitud ya fue resuelta por otro usuario.',
  TICKET_SELF_APPROVAL_FORBIDDEN: 'No puedes aprobar o rechazar una solicitud que tú mismo creaste.',
  INVALID_STATE_TRANSITION: 'La OT tiene equipos que todavía no están listos para cerrarse.',
};

export function humanizeErrorMessage(message: string): string {
  return KNOWN_ERROR_CODE_MESSAGES[message] ?? message;
}

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
  fieldErrors: FieldError[];
};

export type FieldError = {
  field: string;
  code: string;
  message: string;
  expected?: string | null;
};

const DATE_FIELD_MESSAGES: Record<string, string> = {
  reception_date: 'Fecha de recepción: formato incorrecto. Usa AAAA-MM-DD.',
  calibration_date: 'Fecha de calibración: formato incorrecto. Usa AAAA-MM-DD.',
  next_calibration_date: 'Próxima calibración: formato incorrecto. Usa AAAA-MM-DD.',
};

function parseValidationErrors(detail: unknown[]): FieldError[] {
  return detail.flatMap((item) => {
    if (!item || typeof item !== 'object') return [];
    const raw = item as { loc?: unknown; msg?: unknown; type?: unknown; ctx?: { expected?: unknown } };
    const location = Array.isArray(raw.loc)
      ? raw.loc.map(String).filter((part) => !['body', 'query', 'path'].includes(part))
      : [];
    if (location.length === 0) return [];
    const field = location.join('.');
    const leaf = location.at(-1) ?? field;
    const message = DATE_FIELD_MESSAGES[leaf]
      ?? `Revisa el campo ${field.replaceAll('_', ' ')}.`;
    return [{
      field,
      code: typeof raw.type === 'string' ? raw.type : 'validation_error',
      message,
      expected: raw.ctx?.expected == null ? null : String(raw.ctx.expected),
    }];
  });
}

/**
 * Lee el detalle de un error HTTP conservando `missing_fields`/`code`/`items`
 * cuando el motor backend ya los produce, en vez de aplanarlos a un solo
 * string. Consume el body de `response`; no debe llamarse dos veces sobre la
 * misma Response.
 */
export async function readApiErrorDetail(response: Response): Promise<ApiErrorDetail> {
  try {
    const body = await response.json();
    if (Array.isArray(body.detail)) {
      const fieldErrors = parseValidationErrors(body.detail);
      return {
        message: fieldErrors.length === 1 ? fieldErrors[0].message : 'Revisa los campos marcados.',
        missingFields: null,
        code: 'validation_error',
        items: null,
        fieldErrors,
      };
    }
    if (typeof body.detail === 'string') {
      return { message: humanizeErrorMessage(body.detail), missingFields: null, code: null, items: null, fieldErrors: [] };
    }
    if (body.detail?.message) {
      const missingFields = Array.isArray(body.detail.missing_fields)
        ? body.detail.missing_fields.map((item: unknown) => String(item))
        : null;
      return { message: humanizeErrorMessage(body.detail.message), missingFields, code: null, items: null, fieldErrors: [] };
    }
    if (body.detail?.code) {
      const items = Array.isArray(body.detail.items) ? body.detail.items : null;
      const code = String(body.detail.code);
      return { message: humanizeErrorMessage(code), missingFields: null, code, items, fieldErrors: [] };
    }
  } catch {
    // El backend puede responder PDF/ZIP o un error sin JSON.
  }
  return { message: `Error del servidor (${response.status})`, missingFields: null, code: null, items: null, fieldErrors: [] };
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
  readonly fieldErrors: FieldError[];

  constructor(
    message: string,
    status: number,
    missingFields: string[] | null = null,
    code: string | null = null,
    items: Record<string, unknown>[] | null = null,
    fieldErrors: FieldError[] = [],
  ) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.missingFields = missingFields;
    this.code = code;
    this.items = items;
    this.fieldErrors = fieldErrors;
  }
}
