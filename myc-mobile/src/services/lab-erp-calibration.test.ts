import assert from 'node:assert/strict';
import test from 'node:test';

import { readApiErrorDetail } from '../api/error-detail';
import {
  buildErpCandidateQuery,
  canAttachErpLink,
  describeErpCandidate,
  erpClientMismatchWarning,
  shouldSearchErpCandidates,
  withErpLink,
  type ErpCalibrationCandidate,
} from './lab-erp-calibration';

const candidate: ErpCalibrationCandidate = {
  service_order_id: 41,
  service_order_folio: 'OSMYC-26-09-0041',
  quotation_id: 9,
  quotation_folio: 'COT-26-0009',
  client_id: 3,
  client_name: 'MetroInd',
  calibration_item_count: 1,
  calibration_quantity: 3,
  calibration_items: [{ service_name: 'Calibración manómetros', quantity: 3 }],
  active_lab_root_id: null,
  active_lab_root_folio: null,
  available: true,
};
const base = { client_name: 'MetroInd', purchase_order: 'OC-DOC-7' };

test('búsqueda server-side: mínimo 2 caracteres y query acotada', () => {
  assert.equal(shouldSearchErpCandidates(' c '), false);
  assert.equal(shouldSearchErpCandidates('co'), true);
  assert.equal(buildErpCandidateQuery('  COT 26 '), 'q=COT+26&limit=20');
});

test('sin selección el payload es exactamente el legacy', () => {
  assert.deepEqual(withErpLink(base, null, 'none', false), base);
  assert.deepEqual(withErpLink(base, null, 'direct', false), base);
});

test('OT individual y grupo directo nuevos envían service_order_id', () => {
  assert.deepEqual(withErpLink(base, candidate, 'none', false), { ...base, service_order_id: 41 });
  assert.deepEqual(withErpLink({ ...base, quantity: 3 }, candidate, 'direct', false), {
    ...base, quantity: 3, service_order_id: 41,
  });
});

test('la solicitud externa de grupo nunca envía service_order_id', () => {
  assert.equal(canAttachErpLink('request', false), false);
  assert.deepEqual(withErpLink(base, candidate, 'request', false), base);
});

test('editar una OT existente no puede cambiar el vínculo ERP', () => {
  assert.equal(canAttachErpLink('none', true), false);
  assert.deepEqual(withErpLink(base, candidate, 'none', true), base);
});

test('purchase_order se conserva como texto documental independiente', () => {
  assert.equal(withErpLink(base, candidate, 'none', false).purchase_order, 'OC-DOC-7');
});

test('el resumen muestra Cotización, ETS y Cliente; uno ya vinculado lo indica', () => {
  assert.deepEqual(describeErpCandidate(candidate), {
    quotation: 'Cotización COT-26-0009',
    serviceOrder: 'ETS OSMYC-26-09-0041',
    client: 'MetroInd',
    detail: 'Calibración · 3 equipos',
  });
  const linked = { ...candidate, available: false, active_lab_root_id: 7, active_lab_root_folio: 6412 };
  assert.equal(describeErpCandidate(linked).detail, 'Ya vinculada a OT 6412');
});

test('los 409 estructurados del vínculo conservan mensaje y code', async () => {
  const detail = await readApiErrorDetail({
    status: 409,
    json: async () => ({ detail: {
      code: 'SERVICE_ORDER_ALREADY_LINKED_TO_LAB',
      message: 'El ETS ya está vinculado a otra OT MYC Mobile.',
    } }),
  } as Response);
  assert.equal(detail.code, 'SERVICE_ORDER_ALREADY_LINKED_TO_LAB');
  assert.equal(detail.message, 'El ETS ya está vinculado a otra OT MYC Mobile.');
});

test('advertencia no bloqueante cuando el cliente LAB difiere del cliente ERP', () => {
  assert.equal(erpClientMismatchWarning('MetroInd', null), null);
  assert.equal(erpClientMismatchWarning('', candidate), null);
  // Mayúsculas, acentos y espacios no son discrepancia.
  assert.equal(erpClientMismatchWarning('  metroind ', candidate), null);
  assert.equal(erpClientMismatchWarning('Métroínd', candidate), null);
  const warning = erpClientMismatchWarning('Otra Empresa SA', candidate);
  assert.match(warning ?? '', /Otra Empresa SA/);
  assert.match(warning ?? '', /MetroInd/);
  assert.match(warning ?? '', /no se cambiará automáticamente/);
});
