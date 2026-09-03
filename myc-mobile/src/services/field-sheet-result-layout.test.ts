import assert from 'node:assert/strict';
import test from 'node:test';

import {
  buildGroupedHeaderLayout,
  declaredWidth,
  rowLabel,
} from './field-sheet-result-layout';
import type { FieldSheetResultSection } from '@/src/types/lab-work-order';

const temperatureLike: FieldSheetResultSection = {
  key: 'temperature_results',
  title: 'Resultados',
  rows: 10,
  columns: [
    { key: 'ibc', label: 'Valores medidos' },
    { key: 'pattern_1', label: '1' },
    { key: 'pattern_2', label: '2' },
    { key: 'pattern_3', label: '3' },
  ],
  header_rows: [
    {
      cells: [
        { label: 'No.', column_key: '__row_number__', rowspan: 2 },
        { label: 'Valores medidos (IBC)', column_key: 'ibc', rowspan: 2 },
        { label: 'Patrón', colspan: 3 },
      ],
    },
    {
      cells: [
        { label: '1', column_key: 'pattern_1' },
        { label: '2', column_key: 'pattern_2' },
        { label: '3', column_key: 'pattern_3' },
      ],
    },
  ],
  row_labels: ['0 %', '10 %', '20 %', '30 %', '40 %', '50 %', '60 %', '70 %', '80 %', '100 %'],
};

test('calcula un rowspan real de dos filas sin agregar una tercera altura', () => {
  const layout = buildGroupedHeaderLayout(temperatureLike, [32, 96, 96, 96, 96]);
  assert.ok(layout);
  assert.equal(layout.columnCount, 5);
  assert.equal(layout.rowCount, 2);
  assert.equal(layout.totalHeight, 64);

  const [number, ibc, pattern, pattern1, pattern2, pattern3] = layout.cells;
  assert.deepEqual(
    { row: number.row, column: number.column, rowspan: number.rowspan, height: number.height },
    { row: 0, column: 0, rowspan: 2, height: 64 },
  );
  assert.deepEqual(
    { row: ibc.row, column: ibc.column, rowspan: ibc.rowspan, height: ibc.height },
    { row: 0, column: 1, rowspan: 2, height: 64 },
  );
  assert.deepEqual(
    { row: pattern.row, column: pattern.column, colspan: pattern.colspan, width: pattern.width },
    { row: 0, column: 2, colspan: 3, width: 288 },
  );
  assert.deepEqual(
    [pattern1, pattern2, pattern3].map((cell) => ({ row: cell.row, column: cell.column, top: cell.top })),
    [
      { row: 1, column: 2, top: 32 },
      { row: 1, column: 3, top: 32 },
      { row: 1, column: 4, top: 32 },
    ],
  );
});

test('mantiene fallback plano cuando no existe header_rows', () => {
  assert.equal(buildGroupedHeaderLayout({ ...temperatureLike, header_rows: [] }, [32, 96, 96, 96, 96]), null);
});

test('resuelve row_labels sin reemplazar la identidad técnica row_number', () => {
  assert.equal(rowLabel(temperatureLike, 1), '0 %');
  assert.equal(rowLabel(temperatureLike, 6), '50 %');
  assert.equal(rowLabel({ ...temperatureLike, row_labels: [] }, 6), '6');
});

test('interpreta widths declarativos seguros y conserva fallback ante valores desconocidos', () => {
  assert.equal(declaredWidth('25%', 400, 96), 100);
  assert.equal(declaredWidth('48px', 400, 96), 48);
  assert.equal(declaredWidth('url(example)', 400, 96), 96);
});
