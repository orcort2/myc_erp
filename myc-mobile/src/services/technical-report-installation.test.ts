import assert from 'node:assert/strict';
import test from 'node:test';

import {
  applyInstallationChange,
  emptyInstallationCapture,
  installationCaptureFromServer,
  INSTALLATION_V1_FIELDS,
  SECTION_EVIDENCE_TYPE,
  showsEffectivenessFields,
  showsIncidentFields,
  textOrNull,
} from './technical-report-installation';
import { buildEvidenceFormData, EVIDENCE_IMAGE_POLICY, planEvidenceResize } from './technical-report-media';
import { createTechnicalReportApi } from './technical-report-api';

test('el contrato v1 es la lista cerrada de 13 campos acordada con backend (sin snapshot)', () => {
  assert.deepEqual([...INSTALLATION_V1_FIELDS], [
    'installation_date', 'installation_location', 'initial_condition', 'installation_description',
    'activities_performed', 'has_incidents', 'incident_description', 'corrective_action',
    'functional_test_performed', 'effectiveness_result', 'effectiveness_description',
    'effectiveness_notes', 'final_observations',
  ]);
  assert.deepEqual(Object.keys(emptyInstallationCapture()), [...INSTALLATION_V1_FIELDS]);
  for (const forbidden of ['client', 'folio', 'serial_number', 'brand', 'model', 'identification', 'work_order']) {
    assert.ok(!(INSTALLATION_V1_FIELDS as readonly string[]).includes(forbidden), forbidden);
  }
});

test('hidratar ignora lo ausente y respeta lo guardado', () => {
  const values = installationCaptureFromServer({ installation_location: 'Planta', has_incidents: false });
  assert.equal(values.installation_location, 'Planta');
  assert.equal(values.has_incidents, false);
  assert.equal(values.final_observations, null);
});

test('reglas condicionales: incidencias, efectividad y sin resultado inventado', () => {
  let values = emptyInstallationCapture();
  assert.equal(showsIncidentFields(values), false);
  values = applyInstallationChange(values, 'has_incidents', true);
  assert.equal(showsIncidentFields(values), true);
  values = applyInstallationChange(values, 'has_incidents', false);
  assert.equal(showsIncidentFields(values), false);
  values = applyInstallationChange(values, 'functional_test_performed', true);
  values = applyInstallationChange(values, 'effectiveness_result', 'unsatisfactory');
  assert.equal(showsEffectivenessFields(values), true);
  values = applyInstallationChange(values, 'functional_test_performed', false);
  assert.equal(values.effectiveness_result, null);
});

test('texto en blanco se envía como null; la sección determina el tipo de foto', () => {
  assert.equal(textOrNull('   '), null);
  assert.equal(textOrNull('Planta'), 'Planta');
  assert.equal(SECTION_EVIDENCE_TYPE.initial_condition, 'before');
  assert.equal(SECTION_EVIDENCE_TYPE.incidents, 'incident');
  assert.equal(SECTION_EVIDENCE_TYPE.functional_verification, 'after');
  assert.equal(SECTION_EVIDENCE_TYPE.work_performed, 'during');
});

test('política de compresión: lado mayor <= 1800 px, nunca se amplía, proporción conservada', () => {
  assert.equal(EVIDENCE_IMAGE_POLICY.maxLongEdgePx, 1800);
  assert.equal(EVIDENCE_IMAGE_POLICY.jpegQuality, 0.75);
  assert.equal(EVIDENCE_IMAGE_POLICY.targetMaxBytes, 500 * 1024);
  assert.equal(EVIDENCE_IMAGE_POLICY.hardMaxBytes, 5 * 1024 * 1024);
  assert.deepEqual(planEvidenceResize(4032, 3024), { width: 1800, height: 1350 });
  assert.deepEqual(planEvidenceResize(3024, 4032), { width: 1350, height: 1800 });
  assert.deepEqual(planEvidenceResize(1200, 800), { width: 1200, height: 800 });
});

test('el cliente HTTP arma rutas, PATCH sólo con capture_values y multipart con evidence_type', async () => {
  const calls: { path: string; init?: RequestInit }[] = [];
  const api = createTechnicalReportApi({
    accessToken: 'tok', apiUrl: (path) => `https://erp.test${path}`, equipmentId: 289, workOrderId: 72,
    request: async <T,>(path: string, init?: RequestInit) => { calls.push({ path, init }); return {} as T; },
  });
  const base = '/mobile/v1/technician/lab-work-orders/72/equipment/289/technical-report';
  await api.load();
  await api.saveCapture({ capture_values: emptyInstallationCapture() });
  await api.uploadEvidence({ uri: 'file:///a.jpg', width: 10, height: 10, mimeType: 'image/jpeg', fileName: 'a.jpg', sizeBytes: 1 }, 'incident');
  await api.deleteEvidence(7);
  assert.deepEqual(calls.map((call) => [call.init?.method ?? 'GET', call.path]), [
    ['GET', base], ['PATCH', base], ['POST', `${base}/evidence`], ['DELETE', `${base}/evidence/7`],
  ]);
  assert.deepEqual(Object.keys(JSON.parse(calls[1].init!.body as string)), ['capture_values']);
  const form = calls[2].init!.body as FormData;
  assert.equal(form.get('evidence_type'), 'incident');
  assert.deepEqual(api.evidenceImageSource(7), { uri: `https://erp.test${base}/evidence/7/file`, headers: { Authorization: 'Bearer tok' } });
  assert.ok(buildEvidenceFormData({ uri: 'x', width: 1, height: 1, mimeType: 'image/jpeg', fileName: 'x.jpg', sizeBytes: null }, 'before') instanceof FormData);
});
