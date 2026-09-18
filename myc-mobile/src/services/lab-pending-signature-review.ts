import type { LabEquipment, LabWorkOrder } from '@/src/types/lab-work-order';

export type PendingSignatureReview = LabWorkOrder['pending_signature_review'];

/**
 * PENDIENTE 4 (encargo de corrección LAB): "Completar cambios" consume
 * pending_signature_review tal cual backend lo calcula
 * (_pending_signature_impact_since_last_close) -- este módulo sólo traduce
 * las claves crudas (CRITICAL_GENERAL_FIELDS/CRITICAL_EQUIPMENT_FIELDS, la
 * misma autoridad ya existente) a lenguaje natural para el warning. No
 * decide qué es sensible; sólo describe lo que backend ya decidió.
 *
 * Mismas etiquetas que ya usan los formularios de esta pantalla (Fecha de
 * recepción / Cliente / Domicilio en "Corregir datos de la orden";
 * Instrumento / Marca / Modelo / Identificación / Serie / Estado físico en
 * LabEquipmentForm) -- para que el técnico reconozca el mismo nombre de
 * campo que ya vio al editar.
 */
const GENERAL_FIELD_LABELS: Record<string, string> = {
  reception_date: 'Fecha de recepción',
  client_name: 'Cliente',
  address: 'Domicilio',
};

const EQUIPMENT_FIELD_LABELS: Record<string, string> = {
  instrument: 'Instrumento',
  brand: 'Marca',
  identification: 'Identificación',
  serial_number: 'Serie',
  model: 'Modelo',
  is_good_condition: 'Estado físico',
};

/** Un campo general es la clave cruda ("reception_date"); uno de equipo
 * viaja como "equipment:{id}:{key}" (ver _pending_signature_impact_since_last_close).
 * Resuelve la posición del equipo cuando el equipo sigue activo en la OT --
 * si ya no está (caso extremo, equipo anulado después), cae de vuelta a la
 * clave cruda en vez de fabricar un dato que no existe. */
export function describeSensitiveField(
  field: string,
  equipment: Pick<LabEquipment, 'id' | 'position'>[],
): string {
  if (field.startsWith('equipment:')) {
    const [, equipmentIdRaw, key] = field.split(':');
    const equipmentId = Number(equipmentIdRaw);
    const label = EQUIPMENT_FIELD_LABELS[key] ?? key;
    const item = equipment.find((candidate) => candidate.id === equipmentId);
    return item ? `Equipo ${item.position} — ${label}` : label;
  }
  return GENERAL_FIELD_LABELS[field] ?? field;
}

export function describePendingSignatureReviewFields(
  review: PendingSignatureReview,
  equipment: Pick<LabEquipment, 'id' | 'position'>[],
): string[] {
  return review.sensitive_fields.map((field) => describeSensitiveField(field, equipment));
}
