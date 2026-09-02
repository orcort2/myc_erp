import type { FieldSheetResultRow, FieldSheetResultSection } from '@/src/types/lab-work-order';

/**
 * Fase 6: progreso real de resultados, calculado desde definición + rows --
 * nunca "hay una fila, entonces está completa". Cuando la sección declara
 * columnas required (validation del snapshot), una fila cuenta como
 * capturada sólo si TODAS esas columnas tienen valor. Hoy el catálogo legacy
 * no declara ninguna columna required (ver hallazgo de inventario Fase 6);
 * mientras eso no cambie, se usa la señal más honesta disponible: la fila
 * cuenta como capturada si al menos una columna editable tiene valor (el
 * técnico la tocó), no por el sólo hecho de existir vacía.
 */
export type SectionProgress = {
  key: string;
  title: string;
  totalRequired: number;
  completed: number;
  missing: number;
  isComplete: boolean;
};

export type OverallProgress = {
  sections: SectionProgress[];
  totalRequired: number;
  totalCompleted: number;
  allComplete: boolean;
};

function isRowCaptured(row: FieldSheetResultRow, section: FieldSheetResultSection): boolean {
  const requiredColumns = section.columns.filter((column) => column.required);
  const columnsToCheck = requiredColumns.length > 0
    ? requiredColumns
    : section.columns.filter((column) => column.editable !== false);
  if (columnsToCheck.length === 0) return false;
  const hasValue = (value: unknown) => value !== undefined && value !== null && String(value).trim() !== '';
  return requiredColumns.length > 0
    // Con columnas required declaradas: TODAS deben tener valor.
    ? columnsToCheck.every((column) => hasValue(row.row_data[column.source ?? column.key]))
    // Sin required declarado: basta con que el técnico haya tocado alguna.
    : columnsToCheck.some((column) => hasValue(row.row_data[column.source ?? column.key]));
}

export function computeSectionProgress(
  section: FieldSheetResultSection,
  rows: FieldSheetResultRow[],
): SectionProgress {
  const sectionRows = rows.filter((row) => row.section_key === section.key);
  const totalRequired = section.allow_add_rows
    ? Math.max(section.min_rows ?? 0, sectionRows.length)
    : (section.rows || sectionRows.length);
  const completed = sectionRows.filter((row) => isRowCaptured(row, section)).length;
  const missing = Math.max(totalRequired - completed, 0);
  return {
    key: section.key,
    title: section.title,
    totalRequired,
    completed,
    missing,
    isComplete: totalRequired > 0 && completed >= totalRequired,
  };
}

export function computeOverallProgress(
  sections: FieldSheetResultSection[],
  rows: FieldSheetResultRow[],
): OverallProgress {
  const perSection = sections.map((section) => computeSectionProgress(section, rows));
  const totalRequired = perSection.reduce((sum, item) => sum + item.totalRequired, 0);
  const totalCompleted = perSection.reduce((sum, item) => sum + item.completed, 0);
  return {
    sections: perSection,
    totalRequired,
    totalCompleted,
    allComplete: perSection.every((item) => item.isComplete),
  };
}
