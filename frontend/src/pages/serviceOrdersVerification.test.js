import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const source = readFileSync(new URL('./ServiceOrdersPage.jsx', import.meta.url), 'utf8');

test('ETS detecta Verificación y habilita el pipeline metrológico compartido', () => {
  assert.match(source, /operational_category === 'verification'/);
  assert.match(source, /selectedOrderHasDirectCalibration \|\| selectedOrderHasVerification/);
  for (const tab of ['Hojas de Campo', 'Captura', 'Calidad', 'Certificados']) {
    assert.match(source, new RegExp(`'${tab}'`));
  }
});

test('el alta asocia cada equipo a una partida y el Master final se identifica en Captura', () => {
  assert.match(source, /service_order_item_id: equipmentForm\.serviceOrderItemId/);
  assert.match(source, /serviceItem\?\.operational_category === 'verification'/);
  assert.match(source, /Certificado de Verificación/);
  assert.match(source, /certificate_master_document_id/);
  assert.match(source, /Master vigente identificado/);
  assert.match(source, /Master genérico inicial/);
  assert.match(source, /Captura sustituye el Master genérico dentro del bonche/);
  assert.match(source, /identifica el Master técnico registrado por estructura/);
});

test('el contexto por equipo distingue Calibración de Verificación', () => {
  assert.match(source, /key: 'calibration',[\s\S]*label: 'Calibración'/);
  assert.match(source, /key: 'verification',[\s\S]*label: 'Verificación'/);
  assert.match(source, /sourceItem\?\.operational_category/);
});
