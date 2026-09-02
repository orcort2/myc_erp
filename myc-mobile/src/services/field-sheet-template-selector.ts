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

export function filterFieldSheetTemplates(
  templates: FieldSheetTemplate[],
  searchTerm: string,
): FieldSheetTemplate[] {
  const term = normalize(searchTerm);
  const matches = term
    ? templates.filter((template) => normalize(template.name).includes(term))
    : templates;
  return matches.slice(0, MAX_VISIBLE_TEMPLATES);
}
