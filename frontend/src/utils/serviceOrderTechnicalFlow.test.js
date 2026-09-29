import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

import {
  buildServiceOrderTabs,
  canOpenServiceOrderTab,
  describeMobileExecution,
  getServiceOrderCapabilities,
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

const mobileOrder = {
  calibration_flow_managed_by_mobile: true,
  work_order_number: null,
  items: [
    { operational_category: 'calibration', is_active: true },
    { operational_category: 'maintenance', is_active: false },
  ],
};

test('capacidades sólo con partidas activas, alineadas con is_calibration_only backend', () => {
  const capabilities = getServiceOrderCapabilities(mobileOrder);
  assert.equal(capabilities.hasMaintenance, false);
  assert.equal(capabilities.hasDirectCalibration, true);
  assert.equal(capabilities.managedByMobileCalibration, true);
  const tabs = keys(buildServiceOrderTabs(capabilities));
  for (const hidden of ['maintenance', 'equipment', 'field-sheet']) {
    assert.ok(!tabs.includes(hidden), hidden);
  }
  // Sin is_active explícito la partida sigue contando (compatibilidad).
  assert.equal(getServiceOrderCapabilities({ items: [{ operational_category: 'maintenance' }] }).hasMaintenance, true);
});

test('desde un ETS Mobile no se puede navegar a equipment/field-sheet', () => {
  const tabs = buildServiceOrderTabs(getServiceOrderCapabilities(mobileOrder));
  assert.equal(canOpenServiceOrderTab(tabs, 'equipment'), false);
  assert.equal(canOpenServiceOrderTab(tabs, 'field-sheet'), false);
  for (const allowed of ['info', 'capture', 'quality', 'certificates', 'billing', 'documents', 'notes', 'history']) {
    assert.equal(canOpenServiceOrderTab(tabs, allowed), true, allowed);
  }
  const historical = buildServiceOrderTabs(calibration);
  assert.equal(canOpenServiceOrderTab(historical, 'field-sheet'), true);
});

test('página: toda acción del Resumen pasa por el guard y no expone métricas ERP en Mobile', () => {
  assert.match(page, /function openTabFromSummary\(tab, options = \{\}\) \{\n(?:\s*\/\/.*\n)*\s*if \(!canOpenServiceOrderTab\(visibleEtsTabs, tab\)\) \{\n\s*return;/);
  assert.match(page, /selectedOrderManagedByMobile &&\n\s*!canOpenServiceOrderTab\(visibleEtsTabs, activeTab\)\n\s*\) \{\n\s*setActiveTab\('info'\);/);
  const summary = page.slice(page.indexOf('<span>Total de equipos</span>') - 400, page.indexOf('<span>Certificados esperados</span>'));
  assert.match(summary, /\{!selectedOrderManagedByMobile \? \(/);
  for (const erpMetric of ['Total de equipos', 'Equipos completados', 'Hojas creadas', 'Hojas completadas']) {
    const index = summary.indexOf(erpMetric);
    assert.ok(index > summary.indexOf('{!selectedOrderManagedByMobile ? ('), erpMetric);
    assert.ok(index < summary.indexOf(') : ('), erpMetric);
  }
  // Setters directos a equipment/field-sheet sólo existen en superficies ocultas para Mobile.
  assert.equal((page.match(/setActiveTab\('field-sheet'\)/g) || []).length, 1);
  assert.match(page, /\) : \(\n\s*<>\n\s*<article className="glass-card-mini">\n\s*<strong>Orden de trabajo<\/strong>[\s\S]*?setActiveTab\('field-sheet'\)/);
});
