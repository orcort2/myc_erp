import assert from 'node:assert/strict';
import test from 'node:test';

import { computeOverallProgress, computeSectionProgress } from './field-sheet-progress';
import type { FieldSheetResultRow, FieldSheetResultSection } from '@/src/types/lab-work-order';

function fixedSection(overrides: Partial<FieldSheetResultSection> = {}): FieldSheetResultSection {
  return {
    key: 'measurements',
    title: 'Resultados de la calibración',
    rows: 3,
    columns: [
      { key: 'pattern_value', label: 'Patrón', source: 'pattern_value' },
      { key: 'instrument_reading', label: 'Indicación', source: 'instrument_reading' },
    ],
    ...overrides,
  };
}

function row(rowNumber: number, data: Record<string, string>): FieldSheetResultRow {
  return { section_key: 'measurements', row_number: rowNumber, row_data: data };
}

test('una fila vacía nunca cuenta como capturada (no basta con existir)', () => {
  const section = fixedSection();
  const rows = [row(1, {}), row(2, {}), row(3, {})];
  const progress = computeSectionProgress(section, rows);
  assert.equal(progress.totalRequired, 3);
  assert.equal(progress.completed, 0);
  assert.equal(progress.missing, 3);
  assert.equal(progress.isComplete, false);
});

test('sin columnas required declaradas, basta con que el técnico haya tocado alguna columna editable', () => {
  const section = fixedSection();
  const rows = [row(1, { pattern_value: '1.00' }), row(2, {}), row(3, {})];
  const progress = computeSectionProgress(section, rows);
  assert.equal(progress.completed, 1);
  assert.equal(progress.missing, 2);
});

test('con columnas required declaradas, TODAS deben tener valor -- una sola no basta', () => {
  const section = fixedSection({
    columns: [
      { key: 'pattern_value', label: 'Patrón', source: 'pattern_value', required: true },
      { key: 'instrument_reading', label: 'Indicación', source: 'instrument_reading', required: true },
    ],
  });
  const rows = [
    row(1, { pattern_value: '1.00' }), // sólo una de las dos requeridas
    row(2, { pattern_value: '1.00', instrument_reading: '1.01' }), // ambas
    row(3, {}),
  ];
  const progress = computeSectionProgress(section, rows);
  assert.equal(progress.completed, 1);
  assert.equal(progress.missing, 2);
});

test('columnas no editables (sólo lectura) nunca cuentan para completitud', () => {
  const section = fixedSection({
    columns: [
      { key: 'row_label', label: 'Punto', source: 'row_label', editable: false },
      { key: 'pattern_value', label: 'Patrón', source: 'pattern_value' },
    ],
  });
  const rows = [row(1, { row_label: '1' })]; // sólo la columna no editable tiene valor
  const progress = computeSectionProgress(section, rows);
  assert.equal(progress.completed, 0);
});

test('8 de 8: sección fija totalmente llenada queda completa', () => {
  const section = fixedSection({ rows: 2 });
  const rows = [
    row(1, { pattern_value: '1.00' }),
    row(2, { pattern_value: '2.00' }),
  ];
  const progress = computeSectionProgress(section, rows);
  assert.equal(progress.totalRequired, 2);
  assert.equal(progress.completed, 2);
  assert.equal(progress.missing, 0);
  assert.equal(progress.isComplete, true);
});

test('sección dinámica (allow_add_rows): el total crece con las filas agregadas, no queda fijo', () => {
  const section = fixedSection({ rows: 1, allow_add_rows: true, min_rows: 1 });
  const rows = [
    row(1, { pattern_value: '1.00' }),
    row(2, { pattern_value: '2.00' }),
    row(3, {}),
  ];
  const progress = computeSectionProgress(section, rows);
  assert.equal(progress.totalRequired, 3);
  assert.equal(progress.completed, 2);
  assert.equal(progress.isComplete, false);
});

test('sección dinámica sin filas agregadas todavía respeta min_rows como piso', () => {
  const section = fixedSection({ rows: 1, allow_add_rows: true, min_rows: 2 });
  const progress = computeSectionProgress(section, []);
  assert.equal(progress.totalRequired, 2);
  assert.equal(progress.completed, 0);
});

test('computeOverallProgress agrega varias secciones (p.ej. "Antes"/"Después" del ajuste) sin mezclarlas', () => {
  const before = fixedSection({ key: 'before', title: 'Antes del ajuste', rows: 2 });
  const after = fixedSection({ key: 'after', title: 'Después del ajuste', rows: 2 });
  const rows: FieldSheetResultRow[] = [
    { section_key: 'before', row_number: 1, row_data: { pattern_value: '1' } },
    { section_key: 'before', row_number: 2, row_data: { pattern_value: '2' } },
    { section_key: 'after', row_number: 1, row_data: { pattern_value: '1' } },
    { section_key: 'after', row_number: 2, row_data: {} },
  ];
  const overall = computeOverallProgress([before, after], rows);
  assert.equal(overall.sections.length, 2);
  assert.equal(overall.sections[0].isComplete, true);
  assert.equal(overall.sections[1].isComplete, false);
  assert.equal(overall.totalCompleted, 3);
  assert.equal(overall.totalRequired, 4);
  assert.equal(overall.allComplete, false);
});

test('computeOverallProgress: allComplete sólo si TODAS las secciones lo están', () => {
  const only = fixedSection({ rows: 1 });
  const complete = computeOverallProgress([only], [row(1, { pattern_value: '1' })]);
  assert.equal(complete.allComplete, true);
});
