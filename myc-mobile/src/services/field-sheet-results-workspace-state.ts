import type { FieldSheetResultRow, FieldSheetResultSection } from '@/src/types/lab-work-order';

/**
 * Fase 6: estado del workspace de Resultados. Nada de PATCH por tecla --
 * edición local con dirty tracking explícito; el caller decide cuándo
 * disparar el guardado real (guardar explícito / debounce) y reporta el
 * resultado con markSaving/markSaved/markSaveError. Cerrar el workspace con
 * cambios sin guardar es responsabilidad del caller (ver
 * canCloseWithoutConfirmation): esta capa nunca pierde datos silenciosamente
 * por sí misma.
 */
export type SaveState = 'idle' | 'dirty' | 'saving' | 'saved' | 'error';

export type WorkspaceState = {
  rows: FieldSheetResultRow[];
  savedRows: FieldSheetResultRow[];
  saveState: SaveState;
  errorMessage: string | null;
};

export function initWorkspaceState(rows: FieldSheetResultRow[]): WorkspaceState {
  return { rows, savedRows: rows, saveState: 'idle', errorMessage: null };
}

function sameRows(a: FieldSheetResultRow[], b: FieldSheetResultRow[]): boolean {
  return JSON.stringify(a) === JSON.stringify(b);
}

export function isDirty(state: WorkspaceState): boolean {
  return !sameRows(state.rows, state.savedRows);
}

/** Antes de cerrar el workspace: true si es seguro cerrar sin guardar ni
 * confirmar (nada pendiente); false si hay cambios que exigen guardar o
 * pedir confirmación al técnico -- nunca se pierden en silencio. */
export function canCloseWithoutConfirmation(state: WorkspaceState): boolean {
  return !isDirty(state);
}

export function setCellValue(
  state: WorkspaceState,
  sectionKey: string,
  rowNumber: number,
  columnKey: string,
  value: unknown,
): WorkspaceState {
  const rows = state.rows.map((row) => (row.section_key === sectionKey && row.row_number === rowNumber)
    ? { ...row, row_data: { ...row.row_data, [columnKey]: value } }
    : row);
  return { ...state, rows, saveState: 'dirty', errorMessage: null };
}

export function addRow(state: WorkspaceState, section: FieldSheetResultSection): WorkspaceState {
  if (!section.allow_add_rows) return state;
  const sectionRows = state.rows.filter((row) => row.section_key === section.key);
  if (section.max_rows != null && sectionRows.length >= section.max_rows) return state;
  const newRow: FieldSheetResultRow = {
    section_key: section.key,
    row_number: sectionRows.length + 1,
    row_data: {},
  };
  return { ...state, rows: [...state.rows, newRow], saveState: 'dirty', errorMessage: null };
}

export function removeRow(
  state: WorkspaceState,
  section: FieldSheetResultSection,
  rowNumber: number,
): WorkspaceState {
  if (!section.allow_remove_rows) return state;
  const sectionRows = state.rows.filter((row) => row.section_key === section.key);
  if (section.min_rows != null && sectionRows.length <= section.min_rows) return state;
  const remaining = state.rows.filter(
    (row) => !(row.section_key === section.key && row.row_number === rowNumber),
  );
  // Renumera para mantener 1..N contiguo dentro de la sección -- las filas
  // fixed (sin allow_remove_rows) nunca pasan por esta función.
  let counter = 0;
  const renumbered = remaining.map((row) => (row.section_key === section.key
    ? { ...row, row_number: ++counter }
    : row));
  return { ...state, rows: renumbered, saveState: 'dirty', errorMessage: null };
}

export function markSaving(state: WorkspaceState): WorkspaceState {
  return { ...state, saveState: 'saving', errorMessage: null };
}

export function markSaved(state: WorkspaceState, savedRows: FieldSheetResultRow[]): WorkspaceState {
  return { ...state, rows: savedRows, savedRows, saveState: 'saved', errorMessage: null };
}

/** Confirma en backend EXACTAMENTE las filas que se enviaron (`submittedRows`),
 * no las que haya ahora en pantalla: si el técnico siguió editando durante el
 * guardado, esas ediciones permanecen dirty y la respuesta no las da por
 * guardadas. */
export function markSavedSnapshot(
  state: WorkspaceState,
  submittedRows: FieldSheetResultRow[],
): WorkspaceState {
  const clean = sameRows(state.rows, submittedRows);
  return {
    ...state,
    savedRows: submittedRows,
    saveState: clean ? 'saved' : 'dirty',
    errorMessage: null,
  };
}

/** Acción única del pie del workspace: 'save' mientras haya resultados sin
 * persistir (o el último guardado falló / está en curso); 'close' sólo cuando
 * las filas visibles ya fueron confirmadas por el backend. Sólo depende de las
 * filas de Resultados, nunca de los campos generales de la hoja. */
export type ResultsFooterAction = 'save' | 'close';

export function resultsFooterAction(state: WorkspaceState): ResultsFooterAction {
  return isDirty(state) || state.saveState === 'saving' || state.saveState === 'error' ? 'save' : 'close';
}

export function markSaveError(state: WorkspaceState, message: string): WorkspaceState {
  return { ...state, saveState: 'error', errorMessage: message };
}

/** Cierra sólo si el guardado confirmó éxito. El resultado explícito evita
 * que un catch interno convierta un fallo de red en pérdida silenciosa. */
export async function exitAfterSuccessfulSave(
  save: () => Promise<boolean>,
  close: () => void,
): Promise<boolean> {
  const saved = await save();
  if (saved) close();
  return saved;
}
