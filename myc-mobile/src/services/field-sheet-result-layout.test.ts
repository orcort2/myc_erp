import assert from 'node:assert/strict';
import test from 'node:test';

import {
  buildGroupedHeaderRows,
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

test('interpreta header multinivel con colspan y espacios derivados de rowspan', () => {
  const rows = buildGroupedHeaderRows(temperatureLike);
  assert.equal(rows.length, 2);
  assert.deepEqual(rows[0].map((segment) => segment.span), [1, 1, 3]);
  assert.equal(rows[1][0].kind, 'spacer');
  assert.equal(rows[1][0].span, 2);
  assert.deepEqual(rows[1].slice(1).map((segment) => segment.span), [1, 1, 1]);
});

test('mantiene fallback plano cuando no existe header_rows', () => {
  assert.deepEqual(buildGroupedHeaderRows({ ...temperatureLike, header_rows: [] }), []);
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
