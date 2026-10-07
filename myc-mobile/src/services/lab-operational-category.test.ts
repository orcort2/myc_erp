import assert from 'node:assert/strict';
import test from 'node:test';

import {
  canChooseOperationalCategory,
  categoryAllowsErpLink,
  DEFAULT_OPERATIONAL_CATEGORY,
  equipmentFormProfile,
  isGeneralService,
  OPERATIONAL_CATEGORY_OPTIONS,
  withOperationalCategory,
} from './lab-operational-category';

test('la categoría por defecto es calibración y el selector ofrece exactamente dos opciones', () => {
  assert.equal(DEFAULT_OPERATIONAL_CATEGORY, 'calibration');
  assert.deepEqual(OPERATIONAL_CATEGORY_OPTIONS.map((option) => [option.value, option.title]), [
    ['calibration', 'Calibración'],
    ['general_service', 'Servicio general'],
  ]);
});

test('la creación envía operational_category (calibration o general_service) en OT individual y grupo directo', () => {
  assert.deepEqual(withOperationalCategory({ a: 1 }, 'calibration', 'none', false), { a: 1, operational_category: 'calibration' });
  assert.deepEqual(withOperationalCategory({ a: 1 }, 'general_service', 'none', false), { a: 1, operational_category: 'general_service' });
  assert.deepEqual(withOperationalCategory({ a: 1 }, 'general_service', 'direct', false), { a: 1, operational_category: 'general_service' });
});

test('la solicitud externa de grupo y la edición conservan el payload histórico (sin operational_category)', () => {
  assert.deepEqual(withOperationalCategory({ a: 1 }, 'general_service', 'request', false), { a: 1 });
  assert.deepEqual(withOperationalCategory({ a: 1 }, 'general_service', 'none', true), { a: 1 });
});

test('Servicio General nunca envía service_order_id aunque quedara residual; calibración lo conserva', () => {
  const withBridge = { a: 1, service_order_id: 9 };
  assert.equal('service_order_id' in withOperationalCategory(withBridge, 'general_service', 'none', false), false);
  assert.equal(withOperationalCategory(withBridge, 'calibration', 'none', false).service_order_id, 9);
});

test('el puente ERP sólo está disponible para calibración', () => {
  assert.equal(categoryAllowsErpLink('calibration'), true);
  assert.equal(categoryAllowsErpLink('general_service'), false);
});

test('el selector de categoría exige actor interno con captura de reportes, creación y no solicitud externa', () => {
  assert.equal(canChooseOperationalCategory('none', false, true, true), true);
  assert.equal(canChooseOperationalCategory('direct', false, true, true), true);
  assert.equal(canChooseOperationalCategory('request', false, true, true), false);
  assert.equal(canChooseOperationalCategory('none', true, true, true), false);
  assert.equal(canChooseOperationalCategory('none', false, false, true), false);
  assert.equal(canChooseOperationalCategory('none', false, true, false), false);
});

test('isGeneralService distingue la categoría y tolera OT sin categoría (histórica)', () => {
  assert.equal(isGeneralService({ operational_category: 'general_service' }), true);
  assert.equal(isGeneralService({ operational_category: 'calibration' }), false);
  assert.equal(isGeneralService({}), false);
  assert.equal(isGeneralService(null), false);
});

test('perfil del formulario: calibración conserva la configuración metrológica; Servicio General la oculta', () => {
  const calibration = equipmentFormProfile('calibration');
  assert.equal(calibration.showsMetrologicalConfiguration, true);
  assert.equal(calibration.instrumentLabel, 'Instrumento');
  assert.equal(calibration.conditionLabel, 'Estado físico');
  assert.equal(calibration.showsReportNumberField, false);

  const general = equipmentFormProfile('general_service');
  assert.equal(general.showsMetrologicalConfiguration, false);
  assert.equal(general.instrumentLabel, 'Equipo / producto');
  assert.equal(general.showsReportNumberField, true);
});
