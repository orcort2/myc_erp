import assert from 'node:assert/strict';
import test from 'node:test';
import { validateFieldSheetContext } from './field-sheet-context';

const equipment = [{ id: 10, field_sheet_id: 91 }, { id: 11, field_sheet_id: null }];

test('D. hoja 91 y backend sigue en 91: se confirma y se conserva', () => {
  assert.equal(validateFieldSheetContext(equipment, { equipmentId: 10, sheetId: 91 }), 'confirmed');
});

test('equipo ausente en el detalle refrescado invalida el contexto', () => {
  assert.equal(validateFieldSheetContext(equipment, { equipmentId: 99, sheetId: 91 }), 'equipment_removed');
});

test('C. hoja 91 y backend ya apunta a la 92: invalida', () => {
  assert.equal(validateFieldSheetContext([{ id: 10, field_sheet_id: 92 }], { equipmentId: 10, sheetId: 91 }), 'sheet_replaced');
});

test('A. creación local sin confirmar + snapshot null anterior: no invalida', () => {
  assert.equal(validateFieldSheetContext(equipment, { equipmentId: 11, sheetId: 120, pendingLocalSheetId: 120 }), 'valid');
});

test('A2. desbloqueo local sin confirmar + snapshot con la revisión previa: no invalida', () => {
  assert.equal(
    validateFieldSheetContext([{ id: 10, field_sheet_id: 91 }], { equipmentId: 10, sheetId: 92, pendingLocalSheetId: 92 }),
    'valid',
  );
});

test('B. creación ya confirmada + snapshot null posterior: la hoja ya no existe en backend', () => {
  assert.equal(validateFieldSheetContext(equipment, { equipmentId: 11, sheetId: 120, pendingLocalSheetId: null }), 'sheet_removed');
});

test('una hoja pendiente distinta de la abierta no protege a la abierta', () => {
  assert.equal(validateFieldSheetContext(equipment, { equipmentId: 11, sheetId: 120, pendingLocalSheetId: 130 }), 'sheet_removed');
});

test('el detalle que menciona la hoja local la confirma', () => {
  assert.equal(validateFieldSheetContext([{ id: 11, field_sheet_id: 120 }], { equipmentId: 11, sheetId: 120, pendingLocalSheetId: 120 }), 'confirmed');
});

test('selector sin hoja (sheetId null) sólo exige que el equipo exista', () => {
  assert.equal(validateFieldSheetContext(equipment, { equipmentId: 11, sheetId: null }), 'valid');
  assert.equal(validateFieldSheetContext(equipment, { equipmentId: 10, sheetId: null }), 'valid');
});
