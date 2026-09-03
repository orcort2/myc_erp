import type { FieldSheetTemplate } from '@/src/types/lab-work-order';

/** Cierre UX 2026-09: mismo criterio de "no mostrar listas gigantes" que
 * lab-client-selector.ts -- las ~30 plantillas ya viajan en un solo GET
 * (no se copia el catálogo aparte); esto sólo filtra/recorta lo ya
 * cargado, client-side, por nombre. */
export const MAX_VISIBLE_TEMPLATES = 5;

function normalize(value: string): string {
  return value
    .normalize('NFKD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .trim();
}

/**
 * Fase 2 del catalogo LAB (2026-09, item 2.2): nombre visible con la
 * organización como autoridad explícita -- NUNCA se deriva parseando
 * `name`. Formato "[ORG] Magnitud" sólo cuando la plantilla trae
 * organization_label; si falta (plantilla histórica/fallback sin
 * metadata), cae de vuelta a `name` tal cual, sin romper nada.
 */
export function templateDisplayLabel(template: FieldSheetTemplate): string {
  const organizationLabel = template.metadata?.organization_label;
  if (!organizationLabel) return template.name;
  const subject = template.metadata?.magnitude_label || template.name;
  return `[${organizationLabel}] ${subject}`;
}

/**
 * Fase 2 del catalogo LAB (2026-09, item 2.3): la unidad de búsqueda ya no
 * es sólo `name` -- también organization_label/magnitude_label (para
 * encontrar "[MYC] Presión" buscando "capymet" o "presión") y
 * supported_equipment/search_aliases (para encontrar la magnitud correcta
 * buscando el equipo real, p.ej. "manómetro" o "multímetro").
 */
function searchableText(template: FieldSheetTemplate): string {
  const metadata = template.metadata;
  const parts = [
    template.name,
    metadata?.organization_label,
    metadata?.organization_key,
    metadata?.magnitude_label,
    metadata?.magnitude_key,
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
  const matches = term
    ? templates.filter((template) => searchableText(template).includes(term))
    : templates;
  return matches.slice(0, MAX_VISIBLE_TEMPLATES);
}
