import assert from 'node:assert/strict';
import test from 'node:test';

import { normalizeFieldSheetPayload } from './field-sheet-payload';
import type { LabFieldSheet } from '@/src/types/lab-work-order';

function sheet(overrides: Partial<LabFieldSheet> = {}): LabFieldSheet {
  return {
    id: 1,
    status: 'draft',
    template_key: 'vernier',
    template_definition: { template_key: 'vernier', name: 'Vernier', version: 1, blocks: [], result_sections: [] },
    capture_values: { instrument: 'Vernier 1' },
    work_order_number: 6400,
    reserved_certificate_folio: null,
    attention: 'Ing. Responsable',
    company: 'Cliente LAB',
    address: 'Av. Prueba 123',
    reception_date: '2026-08-13',
    calibration_date: null,
    next_calibration_date: null,
    calibration_place: null,
    minimum_division: null,
    location: null,
    units: null,
    method: null,
    environment_humidity_start: null,
    environment_humidity_end: null,
    environment_temperature_start: null,
    environment_temperature_end: null,
    equipment_general_condition: true,
    calibrated_by: null,
    reviewed_by: null,
    report_made_by: null,
    purchase_order_or_quotation: null,
    initial_condition: 'BUENA',
    final_condition: null,
    observations: null,
    evidence_notes: null,
    results_rows: [],
    ...overrides,
  };
}

test('fecha previamente capturada y luego vaciada en el formulario se normaliza a null, no a string vacío', () => {
  const original = sheet({ calibration_date: '2026-08-14', next_calibration_date: '2027-08-14' });
  const values = { ...original, calibration_date: '', next_calibration_date: '' };
  const { direct } = normalizeFieldSheetPayload(values, original);
  assert.equal(direct.calibration_date, null);
  assert.equal(direct.next_calibration_date, null);
});

test('fecha que ya era null y sigue vacía en el formulario no se reenvía (sin cambio real)', () => {
  const original = sheet({ calibration_date: null });
  const values = { ...original, calibration_date: '' };
  const { direct } = normalizeFieldSheetPayload(values, original);
  assert.equal('calibration_date' in direct, false);
});

test('boolean vaciado en el formulario se normaliza a null, no a string vacío', () => {
  const original = sheet({ equipment_general_condition: true });
  const values = { ...original, equipment_general_condition: '' };
  const { direct } = normalizeFieldSheetPayload(values, original);
  assert.equal(direct.equipment_general_condition, null);
});

test('un campo string vacío se preserva tal cual (vacío es válido para str | None)', () => {
  const original = sheet({ observations: 'algo' });
  const values = { ...original, observations: '' };
  const { direct } = normalizeFieldSheetPayload(values, original);
  assert.equal(direct.observations, '');
});

test('los campos directos sin cambios respecto al original se omiten del payload', () => {
  const original = sheet({ company: 'Cliente LAB', units: 'mm' });
  const values = { ...original };
  const { direct } = normalizeFieldSheetPayload(values, original);
  assert.equal('company' in direct, false);
  assert.equal('units' in direct, false);
});

test('un campo directo sí modificado se incluye con su nuevo valor', () => {
  const original = sheet({ units: 'mm' });
  const values = { ...original, units: 'in' };
  const { direct } = normalizeFieldSheetPayload(values, original);
  assert.equal(direct.units, 'in');
});

test('las claves que no son columnas directas van a capture_values sin tocar', () => {
  const original = sheet();
  const values = { ...original, instrument: 'Vernier actualizado', brand: 'Mitutoyo' };
  const { captureValues } = normalizeFieldSheetPayload(values, original);
  assert.equal(captureValues.instrument, 'Vernier actualizado');
  assert.equal(captureValues.brand, 'Mitutoyo');
});

test('sin hoja original (primer guardado tras crear) ningún campo directo se omite por diff', () => {
  const values = { calibration_date: '', units: 'mm' };
  const { direct } = normalizeFieldSheetPayload(values, null);
  assert.equal(direct.calibration_date, null);
  assert.equal(direct.units, 'mm');
});
