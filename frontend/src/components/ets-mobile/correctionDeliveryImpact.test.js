import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

import {
  DELIVERY_IMPACT_OPTIONS,
  buildCorrectionPayload,
  deliveryImpactError,
  isEquipmentDelivered,
} from './correctionDeliveryImpact.js';

const dialog = readFileSync(new URL('./EtsMobileCorrectionDialog.jsx', import.meta.url), 'utf8');
const delivered = { id: 1, delivery: { delivered: true } };
const notDelivered = { id: 2, delivery: { delivered: false } };
const legacy = { id: 3 };

test('equipo no entregado no muestra selector ni envía delivery_impact', () => {
  for (const equipment of [notDelivered, legacy]) {
    assert.equal(isEquipmentDelivered(equipment), false);
    assert.equal(deliveryImpactError(equipment, ''), '');
    const payload = buildCorrectionPayload({ reason: ' x ', signaturePolicy: 'preserve', equipment, deliveryImpact: 'delivery_invalidated' });
    assert.deepEqual(payload, { reason: 'x', signature_policy: 'preserve' });
  }
  assert.match(dialog, /\{delivered \? \(/);
});

test('equipo entregado exige elegir una opción', () => {
  assert.equal(isEquipmentDelivered(delivered), true);
  assert.match(deliveryImpactError(delivered, ''), /Indica cómo afecta/);
  assert.match(dialog, /disabled=\{busy \|\| !reason\.trim\(\) \|\| impactMissing\}/);
});

test('las tres opciones viajan como delivery_impact', () => {
  assert.deepEqual(DELIVERY_IMPACT_OPTIONS.map((o) => o.value), ['none', 'documentation_reissue', 'delivery_invalidated']);
  for (const value of ['none', 'documentation_reissue', 'delivery_invalidated']) {
    assert.equal(deliveryImpactError(delivered, value), '');
    assert.deepEqual(
      buildCorrectionPayload({ reason: 'Error', signaturePolicy: 'invalidate', equipment: delivered, deliveryImpact: value }),
      { reason: 'Error', signature_policy: 'invalidate', delivery_impact: value },
    );
  }
});

test('textos de consecuencia claros, sin minor/major', () => {
  const labels = DELIVERY_IMPACT_OPTIONS.map((o) => o.label);
  assert.deepEqual(labels, [
    'La corrección no afecta la entrega',
    'Requiere reemisión documental',
    'La entrega de este equipo queda invalidada',
  ]);
  assert.doesNotMatch(dialog + JSON.stringify(DELIVERY_IMPACT_OPTIONS), /\bminor\b|\bmajor\b/i);
});

test('el diálogo envía expected_cohort_revision recibido del backend, sin calcularlo', () => {
  const payload = buildCorrectionPayload({ reason: 'x', signaturePolicy: 'preserve', equipment: notDelivered, cohortRevision: 'abc123' });
  assert.equal(payload.expected_cohort_revision, 'abc123');
  assert.equal('expected_cohort_revision' in buildCorrectionPayload({ reason: 'x', signaturePolicy: 'preserve', equipment: notDelivered }), false);
  assert.match(dialog, /cohortRevision: target\.cohortRevision/);
  const panel = readFileSync(new URL('./EtsMobileExecutionPanel.jsx', import.meta.url), 'utf8');
  const detail = readFileSync(new URL('./EtsMobileEquipmentDetail.jsx', import.meta.url), 'utf8');
  assert.match(panel, /cohortRevision: projection\.cohort_revision/);
  assert.match(detail, /cohortRevision: detail\.cohort_revision/);
  assert.doesNotMatch(panel + detail + dialog, /Math\.max|edit_version/);
});

test('el diálogo ERP no edita valores técnicos', () => {
  assert.doesNotMatch(dialog, /results|capture_values|<input[^>]*type="(text|number)"/);
  assert.match(dialog, /requestServiceOrderMobileCorrection/);
});
