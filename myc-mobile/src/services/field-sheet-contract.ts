import type { FieldSheetTemplateBlock } from '@/src/types/lab-work-order';

/**
 * Fase 6: contrato de campo declarativo. La autoridad principal para
 * label/tipo/orden/placeholder/requerido es block.fields[] (mismo shape que
 * backend/app/schemas/field_sheet_template.py::FieldSheetFieldRead) cuando
 * el backend lo puebla para esa clave. FIELD_LABELS (el mapa hardcodeado en
 * LabTechnicalCapture) queda como fallback legacy únicamente para las claves
 * que un bloque declara en visible_fields sin traer una entrada rica en
 * fields[] -- hoy la mayoría de las plantillas, porque el catálogo legacy
 * (Fase 6, ver hallazgo de inventario) todavía no puebla fields[]. Esto no
 * inventa datos: sólo prioriza correctamente lo que el snapshot sí trae en
 * cuanto exista.
 */
export type ResolvedCaptureField = {
  key: string;
  label: string;
  fieldType: string;
  required: boolean;
  order: number;
  placeholder: string | null;
  readOnly: boolean;
  options: string[];
};

export function resolveBlockFields(
  block: FieldSheetTemplateBlock,
  options: { fallbackLabels: Record<string, string>; readOnlyKeys: Set<string> },
): ResolvedCaptureField[] {
  const richByKey = new Map((block.fields ?? []).map((field) => [field.key, field]));
  const keys = block.visible_fields ?? [];
  return keys
    .map((key, index) => {
      const rich = richByKey.get(key);
      return {
        key,
        label: rich?.label || options.fallbackLabels[key] || key,
        fieldType: rich?.field_type ?? 'text',
        required: rich?.required ?? false,
        order: rich?.order ?? index,
        placeholder: rich?.placeholder ?? null,
        readOnly: options.readOnlyKeys.has(key),
        options: rich?.options ?? [],
      };
    })
    .sort((a, b) => a.order - b.order);
}

/** field_type -> teclado RN (ver TextInput keyboardType en el workspace/formulario). */
export function keyboardTypeForFieldType(fieldType: string | undefined): 'default' | 'numeric' | 'decimal-pad' | 'email-address' | 'phone-pad' {
  switch (fieldType) {
    case 'integer':
      return 'numeric';
    case 'number':
    case 'decimal':
      return 'decimal-pad';
    case 'email':
      return 'email-address';
    case 'phone':
      return 'phone-pad';
    default:
      return 'default';
  }
}
