import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

import {
  buildServiceOrderTabs,
  describeMobileExecution,
  getWorkOrderLabel,
  isMobileCalibrationOrder,
} from './serviceOrderTechnicalFlow.js';

const page = readFileSync(new URL('../pages/ServiceOrdersPage.jsx', import.meta.url), 'utf8');

const calibration = {
  hasSale: false, hasMaintenance: false, hasRepair: false,
  hasDirectCalibration: true, hasVerification: false, managedByMobileCalibration: false,
};
const keys = (tabs) => tabs.map(([key]) => key);

test('ETS calibración MYC Mobile: sin Equipos/Hojas ERP; conserva Captura→Historial', () => {
  const tabs = keys(buildServiceOrderTabs({ ...calibration, managedByMobileCalibration: true }));
  assert.ok(!tabs.includes('equipment'));
  assert.ok(!tabs.includes('field-sheet'));
  assert.deepEqual(tabs, [
    'info', 'capture', 'quality', 'certificates', 'billing', 'documents', 'notes', 'history',
  ]);
});

test('calibración histórica conserva la UI anterior', () => {
  assert.deepEqual(keys(buildServiceOrderTabs(calibration)), [
    'info', 'equipment', 'field-sheet', 'capture', 'quality', 'certificates',
    'billing', 'documents', 'notes', 'history',
  ]);
});

test('ETS mixto conserva la UI anterior (el backend nunca lo marca Mobile)', () => {
  const tabs = keys(buildServiceOrderTabs({ ...calibration, hasMaintenance: true }));
  assert.ok(tabs.includes('maintenance') && tabs.includes('equipment') && tabs.includes('field-sheet'));
});

test('work_order_number null nunca se presenta como OT ficticia', () => {
  const mobile = { work_order_number: null, calibration_flow_managed_by_mobile: true };
  for (const order of [mobile, { work_order_number: null }, {}, null]) {
    assert.doesNotMatch(getWorkOrderLabel(order), /null|undefined|OT -|OT-/);
  }
  assert.equal(getWorkOrderLabel(mobile), 'OT MYC Mobile');
  assert.equal(getWorkOrderLabel({ work_order_number: 7123 }), 'OT 7123');
  assert.equal(isMobileCalibrationOrder(mobile), true);
});

test('Resumen muestra el estado del vínculo LAB', () => {
  assert.deepEqual(describeMobileExecution({ status: 'none', link: null }), {
    title: 'Esperando OT MYC Mobile', detail: null,
  });
  assert.deepEqual(
    describeMobileExecution({ status: 'linked', link: { root_folio: 6412, group_work_order_count: 3 } }),
    { title: 'OT MYC Mobile 6412', detail: '3 OT en el grupo · Vínculo activo' },
  );
  assert.equal(describeMobileExecution({ status: 'error' }).title, 'No fue posible consultar el vínculo');
});

test('página: sin firma técnica ni PDF OT ERP para ETS Mobile; consulta el bridge', () => {
  assert.match(page, /!selectedOrder\.calibration_flow_managed_by_mobile &&\n\s*\(selectedOrder\.has_pending_signature_work_orders/);
  assert.match(page, /\{!selectedOrderManagedByMobile \? \(\n\s*<>\n\s*<button className="table-button" onClick=\{\(\) => openWorkOrderPdf\('view'\)\}/);
  assert.match(page, /getServiceOrderLabLink\(mobileLinkOrderId\)/);
  assert.match(page, /Ejecución técnica MYC Mobile/);
  assert.match(page, /\.\.\.\(managedByMobile \? \[\] : \[\n\s*equipmentStage\.status === 'done',\n\s*fieldSheetStage\.status === 'done',/);
  assert.doesNotMatch(page, /OT \{order\.work_order_number \?\? '-'\}/);
});
