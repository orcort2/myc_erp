import assert from 'node:assert/strict';
import test from 'node:test';

import {
  buildLabExternalStructurePayload,
  buildLabExternalValuesPatch,
  cellValue,
  emptyColumn,
  emptyGroup,
  emptyTable,
  findRow,
  generateUniqueId,
  isLabExternalEquipment,
  readLabExternalDefinition,
  validateLabExternalStructure,
  type LabExternalGroup,
  type LabExternalRow,
} from './lab-field-sheet-external';

test('isLabExternalEquipment sólo es true para service_type=linked', () => {
  assert.equal(isLabExternalEquipment({ service_type: 'linked' }), true);
  assert.equal(isLabExternalEquipment({ service_type: 'accredited' }), false);
  assert.equal(isLabExternalEquipment({ service_type: 'traceable' }), false);
  assert.equal(isLabExternalEquipment({ service_type: null }), false);
});

test('generateUniqueId produce un slug legible y nunca choca con ids existentes', () => {
  assert.equal(generateUniqueId('Grupo 1', []), 'grupo_1');
  assert.equal(generateUniqueId('Grupo 1', ['grupo_1']), 'grupo_1_2');
  assert.equal(generateUniqueId('Grupo 1', ['grupo_1', 'grupo_1_2']), 'grupo_1_3');
  assert.equal(generateUniqueId('Ñañez Ácido!!', []), 'nanez_acido');
});

test('emptyGroup/emptyTable/emptyColumn arrancan con una tabla/columna/fila mínima válida', () => {
  const group = emptyGroup([], 1);
  assert.equal(group.orientation, 'pattern_to_ibc');
  assert.equal(group.tables.length, 1);
  assert.equal(group.tables[0].row_count, 1);
  assert.equal(group.tables[0].columns.length, 1);

  const table = emptyTable(['grupo_1'], 2);
  assert.notEqual(table.id, 'grupo_1');

  const column = emptyColumn([{ key: 'c1', label: 'Columna 1' }]);
  assert.equal(column.key, 'col_2');
});

test('validateLabExternalStructure detecta ids de grupo repetidos', () => {
  const groups: LabExternalGroup[] = [
    { id: 'g1', title: 'G1', orientation: 'pattern_to_ibc', tables: [{ id: 't1', title: 'T', columns: [{ key: 'c1', label: 'C' }], row_count: 1 }] },
    { id: 'g1', title: 'G1 bis', orientation: 'ibc_to_pattern', tables: [{ id: 't2', title: 'T', columns: [{ key: 'c1', label: 'C' }], row_count: 1 }] },
  ];
  const issues = validateLabExternalStructure(groups);
  assert.ok(issues.some((issue) => issue.includes('mismo id')));
});

test('validateLabExternalStructure detecta ids de tabla repetidos entre grupos distintos', () => {
  const groups: LabExternalGroup[] = [
    { id: 'g1', title: 'G1', orientation: 'pattern_to_ibc', tables: [{ id: 'same', title: 'T', columns: [{ key: 'c1', label: 'C' }], row_count: 1 }] },
    { id: 'g2', title: 'G2', orientation: 'ibc_to_pattern', tables: [{ id: 'same', title: 'T', columns: [{ key: 'c1', label: 'C' }], row_count: 1 }] },
  ];
  const issues = validateLabExternalStructure(groups);
  assert.ok(issues.some((issue) => issue.includes('tablas con el mismo id')));
});

test('validateLabExternalStructure exige al menos una tabla por grupo y una columna por tabla', () => {
  const noTables: LabExternalGroup[] = [{ id: 'g1', title: 'G1', orientation: 'pattern_to_ibc', tables: [] }];
  assert.ok(validateLabExternalStructure(noTables).some((issue) => issue.includes('al menos una tabla')));

  const noColumns: LabExternalGroup[] = [
    { id: 'g1', title: 'G1', orientation: 'pattern_to_ibc', tables: [{ id: 't1', title: 'T', columns: [], row_count: 1 }] },
  ];
  assert.ok(validateLabExternalStructure(noColumns).some((issue) => issue.includes('al menos una columna')));
});

test('una estructura válida no produce issues', () => {
  const groups: LabExternalGroup[] = [
    { id: 'g1', title: 'G1', orientation: 'pattern_to_ibc', tables: [{ id: 't1', title: 'T', columns: [{ key: 'c1', label: 'C' }], row_count: 3 }] },
  ];
  assert.deepEqual(validateLabExternalStructure(groups), []);
});

test('buildLabExternalStructurePayload envía exactamente {groups}', () => {
  const groups: LabExternalGroup[] = [];
  assert.deepEqual(buildLabExternalStructurePayload(groups), { groups: [] });
});

test('readLabExternalDefinition nunca asume blocks/result_sections -- siempre trae groups', () => {
  assert.deepEqual(readLabExternalDefinition({ kind: 'lab_externo', groups: [] }), { kind: 'lab_externo', groups: [] });
  assert.deepEqual(readLabExternalDefinition(null), { kind: 'lab_externo', groups: [] });
  assert.deepEqual(readLabExternalDefinition(undefined), { kind: 'lab_externo', groups: [] });
});

test('findRow/cellValue localizan por (table.id, row_number) y nunca fabrican un valor', () => {
  const rows: LabExternalRow[] = [
    { id: 1, section_key: 'g1_t1', row_number: 1, row_data: { c1: '12.3' } },
    { id: 2, section_key: 'g1_t1', row_number: 2, row_data: {} },
  ];
  assert.equal(cellValue(rows, 'g1_t1', 1, 'c1'), '12.3');
  assert.equal(cellValue(rows, 'g1_t1', 2, 'c1'), '');
  assert.equal(cellValue(rows, 'g1_t1', 99, 'c1'), '');
  assert.equal(findRow(rows, 'g1_t1', 1)?.id, 1);
});

test('buildLabExternalValuesPatch reutiliza el PATCH existente -- sólo results_rows, sin endpoint nuevo', () => {
  const rows = [{ id: 1, section_key: 'g1_t1', row_number: 1, row_data: { c1: '1' } }];
  assert.deepEqual(buildLabExternalValuesPatch(rows), { results_rows: rows });
});
