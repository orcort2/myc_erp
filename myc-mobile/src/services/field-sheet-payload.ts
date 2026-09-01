import type { LabFieldSheet } from '@/src/types/lab-work-order';

/**
 * Claves que son columnas reales de FieldSheet (ver backend/app/schemas/field_sheet.py
 * FieldSheetUpdate) y por lo tanto deben viajar a nivel superior del payload, no dentro
 * de capture_values. Todo lo que no esté aquí (instrument, brand, model, serial_number,
 * internal_id, scope, ...) se guarda en capture_values, que es lo que el PDF de equipo lee.
 */
export const directFields = new Set([
  'attention', 'company', 'address', 'reception_date', 'calibration_date', 'next_calibration_date',
  'initial_condition', 'final_condition', 'observations', 'evidence_notes', 'minimum_division',
  'location', 'calibration_place', 'environment_humidity_start', 'environment_humidity_end',
  'environment_temperature_start', 'environment_temperature_end', 'units', 'method',
  'environmental_conditions', 'technician_notes', 'results', 'pattern_used',
  'calibrated_by', 'reviewed_by', 'report_made_by', 'purchase_order_or_quotation',
  'equipment_general_condition',
]);

type FieldSheetFieldKind = 'date' | 'boolean';

/**
 * Subconjunto de directFields cuyo tipo en FieldSheetUpdate no es string
 * (date | None, bool | None). Los TextInput del formulario siempre producen
 * string, así que borrar el campo produce '' — un valor inválido para esos
 * tipos en Pydantic (422 "Unprocessable Entity"), a diferencia de los campos
 * string donde '' sí es un valor legítimo.
 */
const FIELD_SHEET_FIELD_KINDS: Record<string, FieldSheetFieldKind> = {
  reception_date: 'date',
  calibration_date: 'date',
  next_calibration_date: 'date',
  equipment_general_condition: 'boolean',
};

export type FieldSheetPayload = {
  direct: Record<string, unknown>;
  captureValues: Record<string, unknown>;
};

/**
 * Convierte el estado plano `values` del formulario en el payload que
 * FieldSheetUpdate realmente acepta: separa columnas directas de
 * capture_values, convierte '' a null en los campos con tipo no-string
 * (fecha/boolean) y omite las claves directas que no cambiaron respecto a
 * `original` (la última hoja cargada/guardada), para no reenviar de vuelta
 * datos intactos ni arriesgar tipos ya normalizados.
 */
export function normalizeFieldSheetPayload(
  values: Record<string, unknown>,
  original: LabFieldSheet | null,
): FieldSheetPayload {
  const direct: Record<string, unknown> = {};
  const captureValues: Record<string, unknown> = {};
  const originalRecord = original as unknown as Record<string, unknown> | null;

  for (const [key, rawValue] of Object.entries(values)) {
    if (!directFields.has(key)) {
      captureValues[key] = rawValue;
      continue;
    }
    const kind = FIELD_SHEET_FIELD_KINDS[key];
    const value = kind && rawValue === '' ? null : rawValue;
    if (originalRecord && key in originalRecord && originalRecord[key] === value) continue;
    direct[key] = value;
  }

  return { direct, captureValues };
}
