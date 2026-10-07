import assert from 'node:assert/strict';
import test from 'node:test';

import {
  buildCreateTechnicalReportRequest,
  describeTechnicalReportCard,
  isReportTypeEnabled,
  TECHNICAL_REPORT_TYPE_OPTIONS,
  technicalReportAction,
} from './technical-report';

const noReport = { technical_report_id: null, technical_report_type: null, technical_report_folio: null, technical_report_status: null } as const;
const withReport = { technical_report_id: 5, technical_report_type: 'installation', technical_report_folio: 'MYC-IN10-26-0001', technical_report_status: 'draft' } as const;

test('sólo Instalación está habilitada; los demás tipos aparecen como próximamente', () => {
  assert.deepEqual(TECHNICAL_REPORT_TYPE_OPTIONS.map((o) => [o.value, o.enabled]), [
    ['installation', true], ['verification', false], ['repair', false], ['maintenance', false], ['sale', false],
  ]);
  for (const option of TECHNICAL_REPORT_TYPE_OPTIONS.filter((o) => !o.enabled)) {
    assert.equal(option.description, 'Próximamente');
  }
  assert.equal(isReportTypeEnabled('installation'), true);
});

test('crear Instalación arma el POST exacto al endpoint technical-report', () => {
  const call = buildCreateTechnicalReportRequest(72, 289, 'installation');
  assert.ok(call);
  assert.equal(call.path, '/mobile/v1/technician/lab-work-orders/72/equipment/289/technical-report');
  assert.equal(call.init.method, 'POST');
  assert.deepEqual(JSON.parse(call.init.body), { report_type: 'installation' });
});

test('los tipos no habilitados no producen petición', () => {
  for (const type of ['verification', 'repair', 'maintenance', 'sale'] as const) {
    assert.equal(buildCreateTechnicalReportRequest(72, 289, type), null);
  }
});

test('tarjeta sin reporte: SIN REPORTE + Seleccionar reporte', () => {
  const state = describeTechnicalReportCard(noReport);
  assert.equal(state.hasReport, false);
  assert.equal(state.badgeLabel, 'SIN REPORTE');
  assert.equal(state.actionLabel, 'Seleccionar reporte');
  assert.equal(state.folio, null);
});

test('tarjeta con reporte: estado, folio MYC-IN y Abrir reporte', () => {
  const state = describeTechnicalReportCard(withReport);
  assert.equal(state.badgeLabel, 'BORRADOR');
  assert.equal(state.folio, 'MYC-IN10-26-0001');
  assert.equal(state.typeLabel, 'Instalación');
  assert.equal(state.actionLabel, 'Abrir reporte');
});

test('estados visuales del reporte', () => {
  const label = (status: 'ready_for_signatures' | 'completed') => describeTechnicalReportCard({ ...withReport, technical_report_status: status }).badgeLabel;
  assert.equal(label('ready_for_signatures'), 'LISTO PARA FIRMAS');
  assert.equal(label('completed'), 'COMPLETADO');
});

test('permisos: capture habilita crear; lectura sólo abre; sin permisos no hay acción', () => {
  assert.equal(technicalReportAction(noReport, { canRead: true, canCapture: true }), 'select');
  assert.equal(technicalReportAction(noReport, { canRead: true, canCapture: false }), null);
  assert.equal(technicalReportAction(noReport, { canRead: false, canCapture: false }), null);
  assert.equal(technicalReportAction(withReport, { canRead: true, canCapture: false }), 'open');
  assert.equal(technicalReportAction(withReport, { canRead: false, canCapture: false }), null);
});
