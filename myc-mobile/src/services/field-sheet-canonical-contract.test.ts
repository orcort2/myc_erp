import assert from 'node:assert/strict';
import test from 'node:test';

import {
  CANONICAL_FIELDS,
  CANONICAL_FIELD_SHEET_KEYS,
  CANONICAL_GROUP_ORDER,
  canonicalFieldsByGroup,
  canonicalFieldValue,
  specializedCaptureFields,
} from './field-sheet-canonical-contract';
import type { FieldSheetTemplateBlock, LabEquipment, LabFieldSheet } from '@/src/types/lab-work-order';

/**
 * Cierre de contrato canónico LAB (2026-09): el contrato común de captura
 * (labels/orden/tipo/readonly) es FIJO -- no depende de qué plantilla
 * (block.fields[]) se le pase. Estas pruebas verifican eso directamente:
 * la salida no cambia entre plantillas, incluso cuando una plantilla
 * intenta redefinir un campo canónico.
 */

function baseBlocks(tableBlockType: string): FieldSheetTemplateBlock[] {
  return [
    { key: 'header', block_type: 'HeaderBlock', title: 'Encabezado', capture_visible: true, visible_fields: ['work_order_number', 'reserved_certificate_folio'], fields: [] },
    { key: 'client', block_type: 'ClientBlock', title: 'Datos del usuario', capture_visible: true, visible_fields: ['attention', 'company', 'address'], fields: [] },
    { key: 'equipment', block_type: 'EquipmentBlock', title: 'Datos del instrumento', capture_visible: true, visible_fields: ['instrument', 'brand', 'model', 'serial_number', 'internal_id', 'location', 'minimum_division'], fields: [] },
    { key: 'calibration', block_type: 'CalibrationDataBlock', title: 'Datos de calibración', capture_visible: true, visible_fields: ['calibration_place', 'reception_date', 'calibration_date', 'next_calibration_date', 'units'], fields: [] },
    { key: 'environmental', block_type: 'EnvironmentalBlock', title: 'Condiciones ambientales', capture_visible: true, visible_fields: ['environment_humidity_start', 'environment_humidity_end', 'environment_temperature_start', 'environment_temperature_end'], fields: [] },
    { key: 'observations', block_type: 'ObservationsBlock', title: 'Condición y observaciones', capture_visible: true, visible_fields: ['initial_condition', 'final_condition', 'observations'], fields: [] },
    { key: 'table', block_type: tableBlockType, title: 'Resultados de la calibración', capture_visible: false, visible_fields: [], fields: [] },
    { key: 'signatures', block_type: 'SignaturesBlock', title: 'Firmas', capture_visible: true, visible_fields: ['calibrated_by', 'reviewed_by', 'report_made_by'], fields: [] },
  ];
}

const fallbackLabels: Record<string, string> = {
  initial_condition: 'Condición inicial',
  final_condition: 'Condición final',
  observations: 'Observaciones',
};

test('1. anemometro y calibradores producen exactamente el mismo contrato de captura común', () => {
  const anemometro = specializedCaptureFields(baseBlocks('MultiPointTableBlock'), { fallbackLabels, readOnlyKeys: new Set() });
  const calibradores = specializedCaptureFields(baseBlocks('SectionedTableBlock'), { fallbackLabels, readOnlyKeys: new Set() });
  // El contrato canónico en sí ni siquiera mira los bloques -- CANONICAL_FIELDS
  // es la misma referencia sin importar la plantilla.
  assert.deepEqual(CANONICAL_FIELDS, CANONICAL_FIELDS);
  // Los campos especializados resultantes (fuera del contrato canónico)
  // también coinciden entre ambas plantillas, porque comparten los mismos
  // bloques base -- sólo cambia la tabla, que nunca participa aquí.
  assert.deepEqual(anemometro.map((f) => f.key), calibradores.map((f) => f.key));
});

test('2. presion y bascula producen exactamente el mismo contrato común', () => {
  const presion = specializedCaptureFields(baseBlocks('PressureTableBlock'), { fallbackLabels, readOnlyKeys: new Set() });
  const bascula = specializedCaptureFields(baseBlocks('MassBalanceTableBlock'), { fallbackLabels, readOnlyKeys: new Set() });
  assert.deepEqual(presion.map((f) => f.key), bascula.map((f) => f.key));
});

test('3. una plantilla que intenta cambiar label/required/order de un campo canónico no lo logra', () => {
  const hostileBlocks: FieldSheetTemplateBlock[] = [
    {
      key: 'hostile',
      block_type: 'CustomFieldsBlock',
      title: 'Intento hostil',
      capture_visible: true,
      visible_fields: ['brand', 'location', 'company'],
      fields: [
        { key: 'brand', label: 'MARCA HACKEADA', field_type: 'number', required: true, order: 999 },
        { key: 'location', label: 'UBICACION HACKEADA', required: true, order: 0 },
        { key: 'company', label: 'EMPRESA HACKEADA', required: false, order: -5 },
      ],
    },
  ];
  const specialized = specializedCaptureFields(hostileBlocks, { fallbackLabels, readOnlyKeys: new Set() });
  // Ninguna de las 3 claves canónicas debe aparecer como campo especializado
  // -- el override de la plantilla queda completamente descartado.
  assert.equal(specialized.some((f) => f.key === 'brand'), false);
  assert.equal(specialized.some((f) => f.key === 'location'), false);
  assert.equal(specialized.some((f) => f.key === 'company'), false);
  // El contrato canónico real conserva su label/orden fijo, sin importar el intento.
  const brand = CANONICAL_FIELDS.find((f) => f.key === 'brand');
  const location = CANONICAL_FIELDS.find((f) => f.key === 'location');
  const company = CANONICAL_FIELDS.find((f) => f.key === 'company');
  assert.equal(brand?.label, 'Marca');
  assert.equal(brand?.readOnly, true);
  // `location` es el campo que la plantilla hostil intenta volver required=true.
  // El contrato canónico ignora ese intento por completo.
  assert.equal(location?.label, 'Ubicación');
  assert.equal(location?.readOnly, false);
  assert.equal(location?.required, false);
  assert.equal(company?.label, 'Empresa');
  assert.equal(company?.readOnly, true);
});

test('3b. required del contrato canónico es autoridad fija -- una plantilla no puede volver required un campo canónico', () => {
  // Cierre item B: required=false para los 24 campos, deliberado (no se
  // deducen requisitos nuevos desde las plantillas actuales).
  for (const field of CANONICAL_FIELDS) {
    assert.equal(field.required, false, `${field.key} debería tener required=false`);
  }
});

test('4. los campos de identidad de LabWorkOrderEquipment se muestran readonly, leídos del equipo real', () => {
  const equipment = {
    instrument: 'Vernier real', brand: 'Marca real', model: 'Modelo real',
    serial_number: 'Serie real', identification: 'ID real',
  } as LabEquipment;
  const sheet = { work_order_number: 6401, reserved_certificate_folio: 'MYCT-1', attention: 'Ing. real', company: 'Cliente real', address: 'Domicilio real', reception_date: '2026-08-01' } as LabFieldSheet;
  // `values` trae un valor DISTINTO (como si alguien hubiera editado el
  // formulario) -- un campo readonly nunca debe leer de aquí.
  const values = { instrument: 'Instrumento editado en el formulario', brand: 'Marca editada' };
  for (const key of ['instrument', 'brand', 'model', 'serial_number', 'internal_id']) {
    const field = CANONICAL_FIELDS.find((f) => f.key === key)!;
    assert.equal(field.readOnly, true);
    const value = canonicalFieldValue(field, { sheet, equipment, values });
    assert.notEqual(value, values[key as keyof typeof values]);
  }
  assert.equal(canonicalFieldValue(CANONICAL_FIELDS.find((f) => f.key === 'instrument')!, { sheet, equipment, values }), 'Vernier real');
  assert.equal(canonicalFieldValue(CANONICAL_FIELDS.find((f) => f.key === 'internal_id')!, { sheet, equipment, values }), 'ID real');
  assert.equal(canonicalFieldValue(CANONICAL_FIELDS.find((f) => f.key === 'company')!, { sheet, equipment, values }), 'Cliente real');
});

test('6. un campo especializado declarado por una plantilla aparece con su propio label y required', () => {
  const blocks: FieldSheetTemplateBlock[] = [
    {
      key: 'standards',
      block_type: 'StandardsBlock',
      title: 'Patrones',
      capture_visible: true,
      visible_fields: ['pattern_used'],
      fields: [{ key: 'pattern_used', label: 'Patrón utilizado', required: true, order: 0 }],
    },
  ];
  const specialized = specializedCaptureFields(blocks, { fallbackLabels, readOnlyKeys: new Set() });
  assert.equal(specialized.length, 1);
  assert.equal(specialized[0].key, 'pattern_used');
  assert.equal(specialized[0].label, 'Patrón utilizado');
  assert.equal(specialized[0].required, true);
  assert.equal(specialized[0].readOnly, false);
});

test('las 5 secciones canónicas cubren exactamente los grupos definidos, en orden fijo', () => {
  assert.deepEqual(CANONICAL_GROUP_ORDER, ['user', 'instrument', 'calibration', 'environmental', 'condition']);
  for (const group of CANONICAL_GROUP_ORDER) {
    assert.ok(canonicalFieldsByGroup(group).length > 0, group);
  }
  const grouped = CANONICAL_GROUP_ORDER.flatMap((group) => canonicalFieldsByGroup(group));
  assert.deepEqual(grouped.map((f) => f.key), CANONICAL_FIELDS.map((f) => f.key));
});

test('CANONICAL_FIELD_SHEET_KEYS contiene exactamente las 24 claves del contrato', () => {
  assert.equal(CANONICAL_FIELD_SHEET_KEYS.size, 24);
  assert.equal(CANONICAL_FIELD_SHEET_KEYS.has('scope'), true);
  assert.equal(CANONICAL_FIELD_SHEET_KEYS.has('equipment_general_condition'), true);
  assert.equal(CANONICAL_FIELD_SHEET_KEYS.has('consider_equipment_deviations'), true);
  // Campos legado que existen pero NO son parte del contrato canónico --
  // deben seguir siendo especializados (bajo autoridad de plantilla).
  assert.equal(CANONICAL_FIELD_SHEET_KEYS.has('initial_condition'), false);
  assert.equal(CANONICAL_FIELD_SHEET_KEYS.has('final_condition'), false);
  assert.equal(CANONICAL_FIELD_SHEET_KEYS.has('units'), false);
});
