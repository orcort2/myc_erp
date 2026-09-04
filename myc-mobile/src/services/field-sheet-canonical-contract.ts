import type { FieldSheetTemplateBlock, LabEquipment, LabFieldSheet } from '@/src/types/lab-work-order';
import { resolveBlockFields, type ResolvedCaptureField } from '@/src/services/field-sheet-contract';

/**
 * Cierre de contrato canónico LAB (2026-09).
 *
 * Todas las hojas de campo LAB comparten exactamente la misma experiencia
 * de captura común -- la plantilla NUNCA es autoridad de qué campos
 * comunes aparecen, sus labels, su orden, si son required o su tipo de
 * input. Esa autoridad es SIEMPRE este archivo, fija, independiente de
 * `template_definition.blocks[].fields[]` (que sigue existiendo, pero sólo
 * para layout/PDF y para campos genuinamente especializados -- ver
 * `specializedCaptureFields` más abajo).
 *
 * Mismo contrato en el backend: backend/app/services/field_sheets.py
 * (CANONICAL_FIELD_SHEET_KEYS). Duplicado deliberado: no hay codegen
 * compartido en este repo entre Mobile y backend.
 */

export type CanonicalFieldGroupKey = 'user' | 'instrument' | 'calibration' | 'environmental' | 'condition';

export const CANONICAL_GROUP_ORDER: CanonicalFieldGroupKey[] = [
  'user',
  'instrument',
  'calibration',
  'environmental',
  'condition',
];

export const CANONICAL_GROUP_TITLES: Record<CanonicalFieldGroupKey, string> = {
  user: 'Datos del usuario',
  instrument: 'Datos del instrumento',
  calibration: 'Datos de calibración',
  environmental: 'Condiciones ambientales',
  condition: 'Condición / observaciones',
};

export type CanonicalFieldKind = 'text' | 'textarea' | 'date' | 'boolean';

export type CanonicalFieldDescriptor = {
  key: string;
  label: string;
  group: CanonicalFieldGroupKey;
  /** true = snapshot readonly desde OT/cliente documental/equipo -- nunca
   * editable desde el formulario de captura, sin importar la plantilla. */
  readOnly: boolean;
  kind: CanonicalFieldKind;
  /**
   * Cierre de contrato canónico LAB (2026-09, item B): el contrato canónico
   * es TAMBIÉN autoridad explícita de `required` -- ninguna plantilla puede
   * volver obligatorio un campo canónico (ver `_validate_specialized_template_fields`
   * en el backend, que descarta cualquier `required` de plantilla sobre estas
   * 24 claves). Deliberadamente `false` en los 24 campos: este cierre no
   * introduce NINGUNA obligatoriedad nueva, sólo hace explícita la autoridad
   * -- preserva el comportamiento existente. Si en el futuro se decide que
   * algún campo canónico debe ser obligatorio, el único lugar autorizado
   * para expresarlo es aquí (y su espejo en el backend,
   * `_validate_canonical_common_fields`), nunca en una plantilla.
   */
  required: boolean;
};

// El orden del arreglo ES el orden de captura -- fijo, no depende de
// ninguna plantilla.
export const CANONICAL_FIELDS: CanonicalFieldDescriptor[] = [
  // Datos del usuario -- identidad documental + cliente (readonly, snapshot).
  { key: 'work_order_number', label: 'No. de orden de trabajo', group: 'user', readOnly: true, kind: 'text', required: false },
  { key: 'reserved_certificate_folio', label: 'Folio de certificado', group: 'user', readOnly: true, kind: 'text', required: false },
  { key: 'attention', label: 'Atención a', group: 'user', readOnly: true, kind: 'text', required: false },
  { key: 'company', label: 'Empresa', group: 'user', readOnly: true, kind: 'text', required: false },
  { key: 'address', label: 'Dirección', group: 'user', readOnly: true, kind: 'text', required: false },
  // Datos del instrumento -- identidad (readonly, snapshot del equipo) + captura técnica.
  { key: 'instrument', label: 'Instrumento', group: 'instrument', readOnly: true, kind: 'text', required: false },
  { key: 'brand', label: 'Marca', group: 'instrument', readOnly: true, kind: 'text', required: false },
  { key: 'model', label: 'Modelo', group: 'instrument', readOnly: true, kind: 'text', required: false },
  { key: 'serial_number', label: 'No. de serie', group: 'instrument', readOnly: true, kind: 'text', required: false },
  { key: 'internal_id', label: 'ID interno', group: 'instrument', readOnly: true, kind: 'text', required: false },
  { key: 'scope', label: 'Alcance / capacidad', group: 'instrument', readOnly: false, kind: 'text', required: false },
  { key: 'minimum_division', label: 'División mínima', group: 'instrument', readOnly: false, kind: 'text', required: false },
  { key: 'location', label: 'Ubicación', group: 'instrument', readOnly: false, kind: 'text', required: false },
  // Datos de calibración -- reception_date es readonly (snapshot de la OT); el resto es captura técnica.
  { key: 'reception_date', label: 'Fecha de recepción', group: 'calibration', readOnly: true, kind: 'date', required: false },
  { key: 'calibration_place', label: 'Lugar de calibración', group: 'calibration', readOnly: false, kind: 'text', required: false },
  { key: 'calibration_date', label: 'Fecha de calibración', group: 'calibration', readOnly: false, kind: 'date', required: false },
  { key: 'next_calibration_date', label: 'Próxima calibración', group: 'calibration', readOnly: false, kind: 'date', required: false },
  // Condiciones ambientales -- captura técnica.
  { key: 'environment_humidity_start', label: 'Humedad inicial', group: 'environmental', readOnly: false, kind: 'text', required: false },
  { key: 'environment_humidity_end', label: 'Humedad final', group: 'environmental', readOnly: false, kind: 'text', required: false },
  { key: 'environment_temperature_start', label: 'Temperatura inicial', group: 'environmental', readOnly: false, kind: 'text', required: false },
  { key: 'environment_temperature_end', label: 'Temperatura final', group: 'environmental', readOnly: false, kind: 'text', required: false },
  // Condición / observaciones -- captura técnica.
  { key: 'equipment_general_condition', label: 'Condición general del equipo', group: 'condition', readOnly: false, kind: 'boolean', required: false },
  { key: 'consider_equipment_deviations', label: 'Considerar desviaciones del equipo', group: 'condition', readOnly: false, kind: 'boolean', required: false },
  { key: 'observations', label: 'Observaciones', group: 'condition', readOnly: false, kind: 'textarea', required: false },
];

export const CANONICAL_FIELD_SHEET_KEYS = new Set(CANONICAL_FIELDS.map((field) => field.key));

export function canonicalFieldsForDefinition(
  blocks: FieldSheetTemplateBlock[] | undefined,
): CanonicalFieldDescriptor[] {
  const visible = new Set<string>();
  const labelOverrides = new Map<string, string>();
  for (const block of blocks ?? []) {
    if (block.capture_visible === false || block.visible === false || block.block_type.includes('Table')) continue;
    for (const key of block.visible_fields ?? []) visible.add(key);
    for (const field of block.fields ?? []) {
      if ((block.visible_fields ?? []).includes(field.key) && field.visible !== false && field.label) {
        labelOverrides.set(field.key, field.label);
      }
    }
  }
  return CANONICAL_FIELDS
    .filter((field) => visible.has(field.key))
    .map((field) => ({ ...field, label: labelOverrides.get(field.key) ?? field.label }));
}

export function canonicalFieldsByGroup(
  group: CanonicalFieldGroupKey,
  fields: CanonicalFieldDescriptor[] = CANONICAL_FIELDS,
): CanonicalFieldDescriptor[] {
  return fields.filter((field) => field.group === group);
}

/** Etiquetas canónicas expuestas para reutilizar en mensajes (p.ej. la
 * lista de missing_fields que devuelve el backend al no poder completar). */
export const CANONICAL_FIELD_LABELS: Record<string, string> = Object.fromEntries(
  CANONICAL_FIELDS.map((field) => [field.key, field.label]),
);

type CanonicalValueContext = {
  sheet: LabFieldSheet | null;
  equipment: LabEquipment;
  values: Record<string, unknown>;
};

/**
 * Valor de un campo canónico readonly: SIEMPRE se lee del snapshot real
 * (sheet para identidad documental/cliente/reception_date, equipment para
 * identidad del instrumento) -- nunca de `values`/capture_values, para que
 * no exista ninguna ruta donde un valor editado localmente se muestre como
 * si fuera el snapshot verdadero. Los campos editables (captura técnica)
 * se leen de `values`, igual que cualquier campo de formulario normal.
 */
export function canonicalFieldValue(field: CanonicalFieldDescriptor, ctx: CanonicalValueContext): string {
  if (field.readOnly) {
    switch (field.key) {
      case 'work_order_number':
        return ctx.sheet?.work_order_number != null ? String(ctx.sheet.work_order_number) : '-';
      case 'reserved_certificate_folio':
        return ctx.sheet?.reserved_certificate_folio ?? '-';
      case 'attention':
        return ctx.sheet?.attention ?? '-';
      case 'company':
        return ctx.sheet?.company ?? '-';
      case 'address':
        return ctx.sheet?.address ?? '-';
      case 'reception_date':
        return ctx.sheet?.reception_date ?? '-';
      case 'instrument':
        return ctx.equipment.instrument;
      case 'brand':
        return ctx.equipment.brand;
      case 'model':
        return ctx.equipment.model ?? '-';
      case 'serial_number':
        return ctx.equipment.serial_number;
      case 'internal_id':
        return ctx.equipment.identification;
      default:
        return '-';
    }
  }
  const raw = ctx.values[field.key];
  if (field.kind === 'boolean') return raw === true ? 'Sí' : raw === false ? 'No' : 'Pendiente';
  return String(raw ?? '');
}

/**
 * Campos especializados: TODO lo que un bloque de plantilla declara en
 * `visible_fields`/`fields[]` que NO pertenece al contrato canónico común
 * (ver CANONICAL_FIELD_SHEET_KEYS). Esta es la ÚNICA vía por la que una
 * plantilla sigue teniendo autoridad real sobre label/tipo/orden/required
 * de un campo -- exactamente lo que finding #2 exige conservar, acotado a
 * lo que de verdad es específico de la plantilla (o legado, p.ej.
 * initial_condition/final_condition/units/method, que existían antes de
 * este contrato y no forman parte de él).
 */
export function specializedCaptureFields(
  blocks: FieldSheetTemplateBlock[] | undefined,
  options: { fallbackLabels: Record<string, string>; readOnlyKeys: Set<string> },
): ResolvedCaptureField[] {
  return (blocks ?? [])
    .filter((block) => block.capture_visible !== false && !block.block_type.includes('Table'))
    .flatMap((block) => resolveBlockFields(block, options))
    .filter((field) => !CANONICAL_FIELD_SHEET_KEYS.has(field.key));
}
