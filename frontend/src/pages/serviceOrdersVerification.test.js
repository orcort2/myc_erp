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

test('una sola partida se autoasigna y el selector sólo aparece con ambigüedad', () => {
  assert.match(source, /defaultMetrologicalItem = metrologicalOrderItems\.length === 1/);
  assert.match(source, /metrologicalOrderItems\.length > 1 \? <label>[\s\S]*Proceso metrológico/);
  assert.match(source, /service_order_item_id: equipmentForm\.serviceOrderItemId/);
});

test('el encabezado identifica categorías y las métricas separan Verificación de Calibración', () => {
  assert.match(source, /Categorías operacionales del ETS/);
  assert.match(source, /label\.toUpperCase\(\)/);
  assert.match(source, /selectedOrderHasDirectCalibration \? \['traceable'/);
  assert.match(source, /selectedOrderHasVerification \? \(/);
  assert.match(source, /Verificaciones · \{selectedVerificationMetrics\.certificates\} certificados/);
  assert.match(source, /sourceItem\?\.operational_category !== 'calibration'/);
});

test('un ETS legacy sin Master muestra advertencia antes de Captura', () => {
  assert.match(source, /selectedOrderHasIncompleteVerificationMaster/);
  assert.match(source, /ETS histórico contiene Verificación sin Master genérico/);
  assert.match(source, /antes de iniciar Captura/);
});
