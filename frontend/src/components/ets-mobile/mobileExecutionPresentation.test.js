import assert from 'node:assert/strict';
import test from 'node:test';

import { getMobileCaptureStageStatus } from '../../utils/etsStages.js';
import {
  captureGroupDocuments,
  countCaptureDocuments,
  describeWorkOrderHeader,
  captureStateLabel,
  correctionModeFor,
  describeCaptureValues,
  describeDocumentaryClient,
  describeEquipmentReadOnly,
  describeFieldSheetSections,
  describeResultSections,
  formatReadOnlyValue,
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
    'LAB_FINAL_PDF_MISSING', 'LAB_WORK_ORDER_NOT_FINAL', 'LAB_WORK_ORDER_FINAL_PDF_MISSING',
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

test('pestaña Captura Mobile: VALIDANDO sin resumen, LISTA si LAB está listo, BLOQUEADA si no', () => {
  assert.deepEqual(
    [getMobileCaptureStageStatus(null).label, getMobileCaptureStageStatus(null).status],
    ['VALIDANDO', 'pending'],
  );
  const ready = getMobileCaptureStageStatus({ ready: true, ready_total: 1, pending_total: 0 });
  assert.deepEqual([ready.label, ready.status, ready.ready], ['LISTA', 'done', true]);
  assert.deepEqual(ready.metrics, { ready: 1, pending: 0 });
  const blocked = getMobileCaptureStageStatus({ ready: false, ready_total: 1, pending_total: 1 });
  assert.deepEqual([blocked.label, blocked.status, blocked.ready], ['BLOQUEADA', 'blocked', false]);
  // Un refresh que entrega un resumen nuevo cambia el estado derivado (misma función, misma autoridad).
  assert.notEqual(getMobileCaptureStageStatus({ ready: false }).label, getMobileCaptureStageStatus({ ready: true }).label);
});

test('enviar a corrección desde el detalle: admin + OT cerrada + hoja completada; nunca sin permiso o con hoja editable', () => {
  const admin = getMobileExecutionPermissions(user('*'));
  const noReopen = getMobileExecutionPermissions(user('service_orders.read', 'field_sheets.read'));
  const visible = (permissions, status, sheetStatus) =>
    permissions.canRequestCorrection && Boolean(correctionModeFor({ status }, { field_sheet: { status: sheetStatus } }));
  assert.equal(visible(admin, 'completed', 'completed'), true);
  assert.equal(visible(admin, 'partially_closed', 'completed'), true);
  assert.equal(visible(noReopen, 'completed', 'completed'), false);
  assert.equal(visible(admin, 'completed', 'draft'), false);
  assert.equal(visible(admin, 'completed', 'in_progress'), false);
});

test('detalle de equipo: identidad, reporte, condición, observaciones y cliente documental', () => {
  const equipment = {
    instrument: 'BÁSCULA', brand: 'Ohaus', model: 'R31', serial_number: 'S1', identification: 'BAS-01',
    report_number: 'REP-7', is_good_condition: false, observations: 'Plato rayado', service_type: 'accredited',
    certificate_folio: 'MYCA-09-26-4721', folio_status: 'reserved', certificate_client_mode: 'different',
    final_client_company_snapshot: 'Planta Norte SA', final_client_address_snapshot: 'Av. 1', final_client_attention_snapshot: null,
  };
  const rows = Object.fromEntries(describeEquipmentReadOnly(equipment));
  assert.equal(rows['Número de reporte'], 'REP-7');
  assert.equal(rows['Condición al recibir'], 'Con observaciones');
  assert.equal(rows['Observaciones del técnico'], 'Plato rayado');
  assert.equal(rows['Tipo de servicio'], 'Acreditado');
  assert.equal(rows['Estado del folio'], 'Reservado');
  assert.deepEqual(describeDocumentaryClient(equipment), [
    ['Cliente documental', 'Diferente al de la OT'], ['Empresa', 'Planta Norte SA'], ['Dirección', 'Av. 1'],
  ]);
  assert.deepEqual(describeDocumentaryClient({ certificate_client_mode: 'order' }), [['Cliente documental', 'Mismo cliente de la OT']]);
});

test('detalle de hoja: todos los datos técnicos persistidos relevantes', () => {
  const sheet = {
    status: 'completed', revision_number: 2, template_key: 'balanzas', calibration_date: '2026-09-28',
    next_calibration_date: '2027-09-28', calibration_place: 'Laboratorio', location: 'Área 2', units: 'g',
    method: 'PT-01', minimum_division: '0.01 g', environment_temperature_start: '20.1', environment_temperature_end: '20.4',
    environment_humidity_start: '45', environment_humidity_end: '47', equipment_general_condition: true,
    consider_equipment_deviations: false, calibrated_by: 'Técnico A', reviewed_by: 'Revisor B', report_made_by: 'Elaboró C',
    observations: 'Sin ajuste', evidence_notes: 'Foto 1',
  };
  const all = Object.fromEntries(describeFieldSheetSections(sheet).flatMap((section) => section.rows));
  for (const [label, value] of [
    ['Fecha de calibración', '2026-09-28'], ['Próxima calibración', '2027-09-28'], ['Lugar de calibración', 'Laboratorio'],
    ['Ubicación', 'Área 2'], ['Unidades', 'g'], ['Método', 'PT-01'], ['División mínima', '0.01 g'],
    ['Temperatura inicio', '20.1'], ['Temperatura fin', '20.4'], ['Humedad inicio', '45'], ['Humedad fin', '47'],
    ['Condición general', 'Buena'], ['Considera desviaciones', 'No'], ['Calibró', 'Técnico A'], ['Revisó', 'Revisor B'],
    ['Elaboró', 'Elaboró C'], ['Observaciones', 'Sin ajuste'], ['Notas de evidencia', 'Foto 1'],
  ]) {
    assert.equal(all[label], value, label);
  }
});

test('capture_values usa labels de la plantilla y no repite la identidad del equipo', () => {
  const sheet = {
    capture_values: { instrument: 'BÁSCULA', capacity: '3100 g', leveling: true, extra_key: ['a', 'b'] },
    template_definition: { blocks: [{ fields: [{ key: 'capacity', label: 'Capacidad máxima' }, { key: 'leveling', label: 'Nivelada' }] }] },
  };
  assert.deepEqual(describeCaptureValues(sheet), [
    ['Capacidad máxima', '3100 g'], ['Nivelada', 'Sí'], ['Extra key', 'a, b'],
  ]);
  assert.equal(formatReadOnlyValue({ nominal: 100, unit: 'g' }), 'Nominal: 100 · Unit: g');
});

test('results_rows: columnas de plantilla, row_data dinámico y columnas estándar sin JSON crudo', () => {
  const sheet = {
    template_definition: {
      result_sections: [{
        key: 'repeatability', title: 'Repetibilidad', row_labels: ['Carga 1', 'Carga 2'],
        columns: [{ key: 'nominal', label: 'Valor nominal' }, { key: 'reading', label: 'Lectura', source: 'ibc_value_1' }],
      }],
    },
    results_rows: [
      { id: 2, section_key: 'repeatability', row_number: 2, ibc_value_1: '200.01', row_data: { nominal: '200', error: '0.01' } },
      { id: 1, section_key: 'repeatability', row_number: 1, ibc_value_1: '100.00', row_data: { nominal: '100' } },
      { id: 3, section_key: 'libre', row_number: 1, pattern_value: 'P1', unit: 'g', row_data: { temp: '20' } },
    ],
  };
  const [repeatability, free] = describeResultSections(sheet);
  assert.equal(repeatability.title, 'Repetibilidad');
  assert.deepEqual(repeatability.columns.map((column) => column.label), ['Valor nominal', 'Lectura', 'Error']);
  assert.deepEqual(repeatability.rows.map((row) => [row.label, ...row.cells]), [
    ['Carga 1', '100', '100.00', ''], ['Carga 2', '200', '200.01', '0.01'],
  ]);
  assert.equal(free.title, 'Libre');
  assert.deepEqual(free.columns.map((column) => column.label), ['Patrón', 'Unidad', 'Temp']);
  assert.deepEqual(free.rows[0].cells, ['P1', 'g', '20']);
  const cells = describeResultSections(sheet).flatMap((section) => section.rows.flatMap((row) => row.cells));
  assert.ok(cells.every((cell) => typeof cell === 'string' && !cell.startsWith('{')));
});

test('cabecera de OT y documentos de Captura (OT final + hojas)', () => {
  const header = describeWorkOrderHeader({
    is_root: true, status: 'completed', reception_date: '2026-09-01', departure_date: null, has_final_pdf: true,
    equipment: [{ field_sheet: { status: 'completed', has_final_pdf: true } }, { field_sheet: { status: 'draft', has_final_pdf: false } }],
  });
  assert.deepEqual(header, {
    role: 'OT raíz', statusLabel: 'Cerrada', receptionDate: '2026-09-01', departureDate: null,
    equipmentCount: 2, completedSheets: 1, finalSheetPdfs: 1, hasFinalPdf: true,
  });
  assert.equal(describeWorkOrderHeader({ status: 'in_progress', equipment: [] }).hasFinalPdf, false);
  const group = {
    work_order_id: 9, work_order_folio: 6438, has_final_pdf: true,
    equipment: [
      { equipment_id: 1, position: 1, certificate_folio: 'MYCA-09-26-4721', field_sheet_id: 5, field_sheet_has_final_pdf: true },
      { equipment_id: 2, position: 2, certificate_folio: null, field_sheet_id: null, field_sheet_has_final_pdf: false },
    ],
  };
  assert.deepEqual(captureGroupDocuments(group).map((doc) => [doc.kind, doc.label, doc.available]), [
    ['work_order', 'OT final 6438', true],
    ['field_sheet', 'Hoja de Campo MYCA-09-26-4721', true],
    ['field_sheet', 'Hoja de Campo equipo 2', false],
  ]);
  assert.equal(countCaptureDocuments({ groups: [group, { ...group, has_final_pdf: false, equipment: [] }] }), 2);
  assert.equal(describeCaptureBlocker({ code: 'LAB_WORK_ORDER_FINAL_PDF_MISSING', work_order_folio: 6439 }),
    'OT 6439: OT cerrada sin PDF final oficial');
});
