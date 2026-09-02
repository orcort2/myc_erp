import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

import type { LabWorkOrder } from '../types/lab-work-order';
import { deriveLabClosureOptions, labClosureContextId } from './lab-work-order-closure';

function workOrder(): LabWorkOrder {
  return {
    id: 1,
    status: 'draft',
    signature_session_id: null,
    equipment: [{ id: 1 }],
    related_work_orders: [
      { id: 1, status: 'draft', equipment_count: 1, signature_session_id: null },
      { id: 2, status: 'draft', equipment_count: 0, signature_session_id: null },
      { id: 3, status: 'draft', equipment_count: 0, signature_session_id: null },
    ],
  } as LabWorkOrder;
}

test('a partially filled historical group keeps individual closure enabled', () => {
  assert.deepEqual(deriveLabClosureOptions(workOrder()), {
    activeCohortSize: 0,
    canFinalizeGroup: false,
    canFinalizeIndividual: true,
    groupMissingEquipmentCount: 2,
    groupParticipantCount: 3,
    hasHistoricalSiblings: true,
    hasEligiblePartialCloseCohort: true,
    isSingleOtSignatureSession: true,
  });
});

test('a lone OT with no live siblings does not offer the partial-close exception', () => {
  const value = workOrder();
  value.related_work_orders = [
    { id: 1, status: 'draft', equipment_count: 1, signature_session_id: null },
  ] as LabWorkOrder['related_work_orders'];
  const options = deriveLabClosureOptions(value);
  assert.equal(options.groupParticipantCount, 1);
  assert.equal(options.hasEligiblePartialCloseCohort, false);
});

test('fully-historical (already closed) siblings do not make a solo OT eligible for partial close', () => {
  const value = workOrder();
  value.related_work_orders = [
    { id: 1, status: 'draft', equipment_count: 1, signature_session_id: null },
    { id: 2, status: 'completed', equipment_count: 1, signature_session_id: 10 },
    { id: 3, status: 'cancelled', equipment_count: 1, signature_session_id: null },
  ] as LabWorkOrder['related_work_orders'];
  const options = deriveLabClosureOptions(value);
  // hasHistoricalSiblings is true (3 all-time siblings), but none of them are
  // currently open/eligible -- the exception must stay hidden regardless.
  assert.equal(options.hasHistoricalSiblings, true);
  assert.equal(options.hasEligiblePartialCloseCohort, false);
});

test('a real multi-OT signature session is not presented as a single-OT closure', () => {
  const value = workOrder();
  value.signature_session_id = 42;
  value.related_work_orders = [
    { id: 1, status: 'ready_for_signatures', equipment_count: 1, signature_session_id: 42 },
    { id: 2, status: 'ready_for_signatures', equipment_count: 1, signature_session_id: 42 },
  ] as LabWorkOrder['related_work_orders'];
  const options = deriveLabClosureOptions(value);
  assert.equal(options.activeCohortSize, 2);
  assert.equal(options.isSingleOtSignatureSession, false);
});

test('a single-OT signature session is presented with the short copy', () => {
  const value = workOrder();
  value.signature_session_id = 42;
  value.related_work_orders = [
    { id: 1, status: 'ready_for_signatures', equipment_count: 1, signature_session_id: 42 },
  ] as LabWorkOrder['related_work_orders'];
  const options = deriveLabClosureOptions(value);
  assert.equal(options.activeCohortSize, 1);
  assert.equal(options.isSingleOtSignatureSession, true);
});

test('completed members are excluded from the next group closure cohort', () => {
  const value = workOrder();
  value.id = 2;
  value.equipment = [{ id: 2 }] as LabWorkOrder['equipment'];
  value.related_work_orders = [
    { id: 1, status: 'completed', equipment_count: 1, signature_session_id: 10 },
    { id: 2, status: 'draft', equipment_count: 1, signature_session_id: null },
    { id: 3, status: 'draft', equipment_count: 1, signature_session_id: null },
  ] as LabWorkOrder['related_work_orders'];

  const options = deriveLabClosureOptions(value);
  assert.equal(options.canFinalizeGroup, true);
  assert.equal(options.groupParticipantCount, 2);
  assert.equal(options.groupMissingEquipmentCount, 0);
});

test('individual and group signature capture use distinct cohort contexts', () => {
  const value = { id: 9, root_work_order_id: 4 } as LabWorkOrder;
  assert.equal(labClosureContextId(value, 'individual'), 9);
  assert.equal(labClosureContextId(value, 'group'), 4);
});

test('the screen exposes explicit group and individual actions', () => {
  // Fase 3: firmar la recepción (grupo/individual) ya no ocurre en el paso
  // de cierre -- el botón real ahora vive en el paso 'signatures' (revisión
  // de recepción) y se llama "Firmar recepción...", no "Finalizar...". El
  // paso 'review' (cierre) sigue distinguiendo grupo/individual, pero para
  // CERRAR, no para firmar (ver work-orders.tsx: `Cerrar grupo activo` /
  // `Cerrar OT ${workOrder.folio}`).
  const source = readFileSync(
    resolve(dirname(fileURLToPath(import.meta.url)), '../../app/(technician)/work-orders.tsx'),
    'utf8',
  );
  const serviceSource = readFileSync(
    resolve(dirname(fileURLToPath(import.meta.url)), './lab-work-order-signature-submission.ts'),
    'utf8',
  );
  assert.match(source, /Firmar recepción del grupo/);
  assert.match(source, /Firmar sólo OT \$\{workOrder\.folio\}/);
  assert.match(source, /Cerrar OT \$\{workOrder\.folio\}/);
  assert.match(source, /groupMissingEquipmentCount/);
  assert.match(serviceSource, /signatures\/individual/);
  assert.match(serviceSource, /complete\/individual/);
  assert.match(source, /inferStepForStatus/);
});

test('the partial-close exception is gated on a real multi-OT cohort, not just permission', () => {
  const source = readFileSync(
    resolve(dirname(fileURLToPath(import.meta.url)), '../../app/(technician)/work-orders.tsx'),
    'utf8',
  );
  assert.match(source, /canCreateTickets && closureOptions\?\.hasEligiblePartialCloseCohort/);
});

test('the post-signature copy shows the short single-OT presentation by default', () => {
  const source = readFileSync(
    resolve(dirname(fileURLToPath(import.meta.url)), '../../app/(technician)/work-orders.tsx'),
    'utf8',
  );
  assert.match(source, /isSingleOtSignatureSession/);
  assert.match(source, /Firma completada/);
  assert.match(source, /Cerrar y generar PDFs/);
});
