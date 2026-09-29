import assert from 'node:assert/strict';
import test from 'node:test';

import {
  captureStateLabel,
  correctionModeFor,
  describeCaptureBlocker,
  describeFieldSheetReadOnly,
  getMobileExecutionPermissions,
  summarizeMobileExecution,
} from './mobileExecutionPresentation.js';

const user = (...permissions) => ({ permissions });

test('permisos: vínculo exige create+update; técnico puro no administra ni corrige', () => {
  assert.deepEqual(getMobileExecutionPermissions(user('*')), {
    canManageLink: true, canReadFieldSheets: true, canRequestCorrection: true, canCancelWorkOrders: true,
  });
  const technician = getMobileExecutionPermissions(user('service_orders.read', 'service_orders.update', 'field_sheets.read'));
  assert.equal(technician.canManageLink, false);
  assert.equal(technician.canRequestCorrection, false);
  assert.equal(technician.canCancelWorkOrders, false);
  assert.equal(technician.canReadFieldSheets, true);
  const quality = getMobileExecutionPermissions(user('service_orders.read', 'field_sheets.read', 'work_orders.reopen'));
  assert.equal(quality.canRequestCorrection, true);
  assert.equal(quality.canManageLink, false);
  assert.equal(getMobileExecutionPermissions(user('service_orders.read')).canReadFieldSheets, false);
});

test('enviar a corrección sólo aplica a hojas completadas en estados admitidos por el dominio', () => {
  const completed = { field_sheet: { status: 'completed' } };
  assert.equal(correctionModeFor({ status: 'in_progress' }, completed), 'field_sheet_reopen');
  assert.equal(correctionModeFor({ status: 'ready_to_close' }, completed), 'field_sheet_reopen');
  assert.equal(correctionModeFor({ status: 'completed' }, completed), 'work_order_reopen');
  assert.equal(correctionModeFor({ status: 'draft' }, completed), null);
  assert.equal(correctionModeFor({ status: 'cancelled' }, completed), null);
  assert.equal(correctionModeFor({ status: 'completed' }, { field_sheet: { status: 'draft' } }), null);
  assert.equal(correctionModeFor({ status: 'completed' }, { field_sheet: null }), null);
});

test('Captura LAB: LISTA/BLOQUEADA y bloqueos estructurados legibles', () => {
  assert.equal(captureStateLabel({ ready: true }), 'LISTA');
  assert.equal(captureStateLabel({ ready: false }), 'BLOQUEADA');
  assert.equal(describeCaptureBlocker({ code: 'LAB_LINK_REQUIRED' }), 'Vincula el servicio MYC Mobile del ETS');
  assert.equal(
    describeCaptureBlocker({
      code: 'LAB_FIELD_SHEET_NOT_COMPLETED', work_order_folio: 6439, position: 1,
      instrument: 'Termómetro', certificate_folio: 'MYCT-1',
    }),
    'OT 6439 · Equipo 1 · Termómetro · MYCT-1: Hoja de Campo no completada',
  );
  for (const code of [
    'LAB_CERTIFICATE_FOLIO_MISSING', 'LAB_CERTIFICATE_FOLIO_NOT_READY', 'LAB_FIELD_SHEET_MISSING',
    'LAB_FINAL_PDF_MISSING', 'LAB_WORK_ORDER_NOT_FINAL',
  ]) {
    assert.notEqual(describeCaptureBlocker({ code }), code);
  }
});

test('proyección: totales por grupo y lectura de hoja como pares etiqueta/valor', () => {
  assert.deepEqual(summarizeMobileExecution({
    work_orders: [
      { equipment: [{ field_sheet: { status: 'completed', has_final_pdf: true } }] },
      { equipment: [{ field_sheet: { status: 'draft', has_final_pdf: false } }, { field_sheet: null }] },
    ],
  }), { workOrders: 2, equipment: 3, completedSheets: 1, finalPdfs: 1 });
  const rows = describeFieldSheetReadOnly({ status: 'completed', revision_number: 2, template_key: 'general', results: '1.00', units: '' });
  assert.deepEqual(rows.map(([label]) => label), ['Estado', 'Revisión', 'Plantilla', 'Resultados']);
});
