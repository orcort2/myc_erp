import type { FieldSheetTemplate } from '@/src/types/lab-work-order';

function normalize(value: string): string {
  return value
    .normalize('NFKD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .trim();
}

/**
 * Fase 2 del catalogo LAB (2026-09, item 2.2/2.4): nombre visible con la
 * organización y la magnitud como autoridad explícita -- NUNCA se deriva
 * parseando `name`. Una misma magnitud puede tener varias variantes
 * documentales reales (geometrías/hojas distintas); document_variant_label
 * la identifica cuando existe, sin representar un equipo:
 *   - organización + magnitud + variante -> "[MYC] Dimensional · Calibradores"
 *   - organización + magnitud sin variante -> "[MYC] Presión"
 *   - sin metadata (plantilla histórica/fallback) -> `name` tal cual.
 */
export function templateDisplayLabel(template: FieldSheetTemplate): string {
  const organizationLabel = template.metadata?.organization_label;
  if (!organizationLabel) return template.name;
  const subject = template.metadata?.magnitude_label || template.name;
  const variant = template.metadata?.document_variant_label;
  return variant ? `[${organizationLabel}] ${subject} · ${variant}` : `[${organizationLabel}] ${subject}`;
}

/**
 * Fase 2 del catalogo LAB (2026-09, item 2.3/2.5): la unidad de búsqueda ya
 * no es sólo `name` -- también organization_label/key, magnitude_label/key,
 * document_variant_label/key (para encontrar "Calibradores" buscando
 * "dimensional" o viceversa) y supported_equipment/search_aliases (para
 * encontrar la magnitud correcta buscando el equipo real, p.ej.
 * "manómetro" o "vernier").
 */
function searchableText(template: FieldSheetTemplate): string {
  const metadata = template.metadata;
  const parts = [
    template.name,
    metadata?.organization_label,
    metadata?.organization_key,
    metadata?.magnitude_label,
    metadata?.magnitude_key,
    metadata?.document_variant_label,
    metadata?.document_variant_key,
    ...(metadata?.supported_equipment ?? []),
    ...(metadata?.search_aliases ?? []),
  ].filter((part): part is string => Boolean(part));
  return normalize(parts.join(' | '));
}

export function filterFieldSheetTemplates(
  templates: FieldSheetTemplate[],
  searchTerm: string,
): FieldSheetTemplate[] {
  const term = normalize(searchTerm);
  return term
    ? templates.filter((template) => searchableText(template).includes(term))
    : templates;
}
