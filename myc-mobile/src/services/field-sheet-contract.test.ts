import assert from 'node:assert/strict';
import test from 'node:test';

import { keyboardTypeForFieldType, resolveBlockFields } from './field-sheet-contract';
import type { FieldSheetTemplateBlock } from '@/src/types/lab-work-order';

const FALLBACK = { instrument: 'Instrumento', brand: 'Marca', unknown_key: undefined as unknown as string };

test('sin fields[] rico, usa el fallback legacy (FIELD_LABELS) en el orden de visible_fields', () => {
  const block: FieldSheetTemplateBlock = {
    key: 'EquipmentBlock', title: 'Equipo', block_type: 'EquipmentBlock',
    visible_fields: ['instrument', 'brand'], fields: [],
  };
  const resolved = resolveBlockFields(block, { fallbackLabels: FALLBACK, readOnlyKeys: new Set() });
  assert.deepEqual(resolved.map((item) => item.key), ['instrument', 'brand']);
  assert.equal(resolved[0].label, 'Instrumento');
  assert.equal(resolved[0].fieldType, 'text');
  assert.equal(resolved[0].required, false);
});

test('con fields[] rico, la autoridad es el snapshot -- label/tipo/requerido/orden ganan sobre el fallback', () => {
  const block: FieldSheetTemplateBlock = {
    key: 'EquipmentDataBlock', title: 'Datos del equipo', block_type: 'EquipmentDataBlock',
    visible_fields: ['instrument', 'scope'],
    fields: [
      { key: 'scope', label: 'Alcance de calibración', field_type: 'text', required: true, order: 0 },
      { key: 'instrument', label: 'Instrumento (snapshot)', field_type: 'text', required: false, order: 1 },
    ],
  };
  const resolved = resolveBlockFields(block, { fallbackLabels: FALLBACK, readOnlyKeys: new Set() });
  // order del snapshot manda: scope (order 0) antes que instrument (order 1),
  // aunque visible_fields los liste en el orden opuesto.
  assert.deepEqual(resolved.map((item) => item.key), ['scope', 'instrument']);
  assert.equal(resolved[0].label, 'Alcance de calibración');
  assert.equal(resolved[0].required, true);
  assert.equal(resolved[1].label, 'Instrumento (snapshot)');
});

test('readOnlyKeys marca readOnly sin alterar label/tipo', () => {
  const block: FieldSheetTemplateBlock = {
    key: 'HeaderBlock', title: 'Encabezado', block_type: 'HeaderBlock',
    visible_fields: ['work_order_number'], fields: [],
  };
  const resolved = resolveBlockFields(block, {
    fallbackLabels: { work_order_number: 'No. de orden' },
    readOnlyKeys: new Set(['work_order_number']),
  });
  assert.equal(resolved[0].readOnly, true);
});

test('sin label en ningún lado, usa la clave cruda en vez de string vacío', () => {
  const block: FieldSheetTemplateBlock = {
    key: 'CustomBlock', title: 'Custom', block_type: 'CustomFieldsBlock',
    visible_fields: ['campo_sin_mapear'], fields: [],
  };
  const resolved = resolveBlockFields(block, { fallbackLabels: {}, readOnlyKeys: new Set() });
  assert.equal(resolved[0].label, 'campo_sin_mapear');
});

test('keyboardTypeForFieldType mapea field_type a teclado RN', () => {
  assert.equal(keyboardTypeForFieldType('integer'), 'numeric');
  assert.equal(keyboardTypeForFieldType('number'), 'decimal-pad');
  assert.equal(keyboardTypeForFieldType('decimal'), 'decimal-pad');
  assert.equal(keyboardTypeForFieldType('email'), 'email-address');
  assert.equal(keyboardTypeForFieldType('phone'), 'phone-pad');
  assert.equal(keyboardTypeForFieldType('text'), 'default');
  assert.equal(keyboardTypeForFieldType(undefined), 'default');
});
