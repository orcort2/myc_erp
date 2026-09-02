import assert from 'node:assert/strict';
import test from 'node:test';

import {
  addRow,
  canCloseWithoutConfirmation,
  initWorkspaceState,
  isDirty,
  markSaveError,
  markSaved,
  markSaving,
  removeRow,
  setCellValue,
} from './field-sheet-results-workspace-state';
import type { FieldSheetResultRow, FieldSheetResultSection } from '@/src/types/lab-work-order';

function fixedSection(overrides: Partial<FieldSheetResultSection> = {}): FieldSheetResultSection {
  return { key: 'measurements', title: 'Resultados', rows: 2, columns: [], ...overrides };
}

function rows(): FieldSheetResultRow[] {
  return [
    { section_key: 'measurements', row_number: 1, row_data: { pattern_value: '1.00' } },
    { section_key: 'measurements', row_number: 2, row_data: {} },
  ];
}

test('estado inicial nunca está dirty', () => {
  const state = initWorkspaceState(rows());
  assert.equal(isDirty(state), false);
  assert.equal(state.saveState, 'idle');
  assert.equal(canCloseWithoutConfirmation(state), true);
});

test('editar una celda marca dirty y bloquea el cierre sin confirmar', () => {
  let state = initWorkspaceState(rows());
  state = setCellValue(state, 'measurements', 2, 'pattern_value', '2.00');
  assert.equal(isDirty(state), true);
  assert.equal(state.saveState, 'dirty');
  assert.equal(canCloseWithoutConfirmation(state), false);
  assert.equal(state.rows[1].row_data.pattern_value, '2.00');
  // La otra fila no se toca.
  assert.equal(state.rows[0].row_data.pattern_value, '1.00');
});

test('guardar exitoso limpia dirty y deja saveState=saved', () => {
  let state = initWorkspaceState(rows());
  state = setCellValue(state, 'measurements', 2, 'pattern_value', '2.00');
  state = markSaving(state);
  assert.equal(state.saveState, 'saving');
  state = markSaved(state, state.rows);
  assert.equal(state.saveState, 'saved');
  assert.equal(isDirty(state), false);
  assert.equal(canCloseWithoutConfirmation(state), true);
});

test('error de guardado conserva los cambios locales -- nunca se pierden', () => {
  let state = initWorkspaceState(rows());
  state = setCellValue(state, 'measurements', 2, 'pattern_value', '2.00');
  state = markSaving(state);
  state = markSaveError(state, 'La red falló');
  assert.equal(state.saveState, 'error');
  assert.equal(state.errorMessage, 'La red falló');
  assert.equal(state.rows[1].row_data.pattern_value, '2.00');
  assert.equal(isDirty(state), true);
  assert.equal(canCloseWithoutConfirmation(state), false);
});

test('addRow respeta allow_add_rows y max_rows', () => {
  const dynamic = fixedSection({ allow_add_rows: true, max_rows: 3 });
  let state = initWorkspaceState(rows());
  state = addRow(state, dynamic);
  assert.equal(state.rows.length, 3);
  assert.equal(state.rows[2].row_number, 3);
  state = addRow(state, dynamic);
  // Ya en el máximo (3) -- no agrega una cuarta.
  assert.equal(state.rows.length, 3);
});

test('addRow es un no-op sobre una sección fixed (sin allow_add_rows)', () => {
  const fixedRows = fixedSection({ allow_add_rows: false });
  let state = initWorkspaceState(rows());
  state = addRow(state, fixedRows);
  assert.equal(state.rows.length, 2);
  assert.equal(state.saveState, 'idle');
});

test('removeRow respeta allow_remove_rows y min_rows, y renumera contiguo', () => {
  const dynamic = fixedSection({ allow_add_rows: true, allow_remove_rows: true, min_rows: 1 });
  let state = initWorkspaceState(rows());
  state = addRow(state, dynamic); // 3 filas
  state = removeRow(state, dynamic, 2); // quita la fila del medio
  assert.equal(state.rows.length, 2);
  assert.deepEqual(state.rows.map((row) => row.row_number), [1, 2]);
});

test('removeRow no baja del min_rows', () => {
  const dynamic = fixedSection({ allow_add_rows: true, allow_remove_rows: true, rows: 1, min_rows: 2 });
  let state = initWorkspaceState(rows()); // ya trae 2 filas == min_rows
  state = removeRow(state, dynamic, 1);
  assert.equal(state.rows.length, 2);
});

test('removeRow es un no-op sin allow_remove_rows (filas fixed de la plantilla)', () => {
  const fixedNoRemove = fixedSection({ allow_remove_rows: false });
  let state = initWorkspaceState(rows());
  state = removeRow(state, fixedNoRemove, 1);
  assert.equal(state.rows.length, 2);
});
