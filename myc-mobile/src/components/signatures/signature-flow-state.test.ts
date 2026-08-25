import assert from 'node:assert/strict';
import test from 'node:test';

import {
  canContinueSignature,
  createSignatureFlowState,
  createSignaturePayload,
  emptySignatureCapture,
  reconcileSignatureFlowState,
  SignatureSubmissionLock,
  type SignatureCapture,
  type SignatureFlowState,
  validateSignatureSubmission,
} from './signature-flow-state';

const drawn = (): SignatureCapture => ({
  dataUrl: 'data:image/png;base64,valid-capture',
  hasDrawing: true,
  strokes: [[{ x: 0.1, y: 0.2 }, { x: 0.7, y: 0.8 }]],
});

function validSubmission(overrides: Record<string, unknown> = {}) {
  return {
    capturedContextId: 10,
    clientCapture: drawn(),
    clientName: 'Cliente',
    currentContextId: 10,
    isSubmitting: false,
    technicianCapture: drawn(),
    technicianName: 'Técnico',
    ...overrides,
  };
}

function capturedFlow(rootWorkOrderId = 6419): SignatureFlowState {
  return {
    clientCapture: drawn(),
    clientName: 'Cliente capturado',
    rootWorkOrderId,
    step: 'technician',
    technicianCapture: drawn(),
    technicianName: 'Técnico capturado',
  };
}

const context = (rootWorkOrderId: number) => ({
  clientName: 'Nombre nuevo del backend',
  rootWorkOrderId,
  technicianName: 'Técnico nuevo',
});

test('same work order plus refetch preserves the complete signature draft', () => {
  const captured = capturedFlow();
  const refetchedWorkOrder = { id: 6419, root_work_order_id: 6419, edit_version: 22 };

  assert.strictEqual(
    reconcileSignatureFlowState(captured, context(refetchedWorkOrder.root_work_order_id)),
    captured,
  );
});

test('a sister work order under the same root preserves the complete signature draft', () => {
  const captured = capturedFlow();
  const sisterWorkOrder = { id: 6422, root_work_order_id: 6419 };

  assert.strictEqual(
    reconcileSignatureFlowState(captured, context(sisterWorkOrder.root_work_order_id)),
    captured,
  );
});

test('a new work-order object with the same root preserves the signature draft', () => {
  const captured = capturedFlow();
  const firstObject = { id: 6420, root_work_order_id: 6419 };
  const replacementObject = { ...firstObject };

  assert.notStrictEqual(replacementObject, firstObject);
  assert.strictEqual(
    reconcileSignatureFlowState(captured, context(replacementObject.root_work_order_id)),
    captured,
  );
});

test('a rerender reconciliation under the same root preserves the same signature state', () => {
  const captured = capturedFlow();
  const firstRender = reconcileSignatureFlowState(captured, context(6419));
  const secondRender = reconcileSignatureFlowState(firstRender, context(6419));

  assert.strictEqual(firstRender, captured);
  assert.strictEqual(secondRender, captured);
});

test('a different root discards names, strokes, hasDrawing and local step', () => {
  const next = reconcileSignatureFlowState(capturedFlow(6419), context(6430));

  assert.equal(next.rootWorkOrderId, 6430);
  assert.equal(next.step, 'client');
  assert.equal(next.clientName, context(6430).clientName);
  assert.equal(next.technicianName, context(6430).technicianName);
  assert.deepEqual(next.clientCapture, emptySignatureCapture());
  assert.deepEqual(next.technicianCapture, emptySignatureCapture());
});

test('group A to group B never reuses either signature from group A', () => {
  const groupA = capturedFlow(6419);
  const groupB = reconcileSignatureFlowState(groupA, context(6430));

  assert.notStrictEqual(groupB, groupA);
  assert.notEqual(groupB.clientCapture.dataUrl, groupA.clientCapture.dataUrl);
  assert.notEqual(groupB.technicianCapture.dataUrl, groupA.technicianCapture.dataUrl);
  assert.equal(groupB.clientCapture.hasDrawing, false);
  assert.equal(groupB.technicianCapture.hasDrawing, false);
});

test('returning to group A after group B creates an empty state instead of recovering the old capture', () => {
  const oldGroupA = capturedFlow(6419);
  const groupB = reconcileSignatureFlowState(oldGroupA, context(6430));
  const newGroupA = reconcileSignatureFlowState(groupB, context(6419));

  assert.notStrictEqual(newGroupA, oldGroupA);
  assert.deepEqual(newGroupA.clientCapture, emptySignatureCapture());
  assert.deepEqual(newGroupA.technicianCapture, emptySignatureCapture());
  assert.equal(newGroupA.step, 'client');
});

test('all sister work orders share one unique group signature state', () => {
  const groupSession = createSignatureFlowState(context(6419));
  const relatedWorkOrders = [6419, 6420, 6421, 6422].map((id) => ({
    id,
    root_work_order_id: 6419,
  }));
  const sessions = relatedWorkOrders.map((item) => (
    reconcileSignatureFlowState(groupSession, context(item.root_work_order_id))
  ));

  assert.equal(new Set(sessions).size, 1);
  assert.ok(sessions.every((session) => session.rootWorkOrderId === 6419));
});

test('an empty canvas cannot continue even if it can serialize a PNG', () => {
  assert.equal(canContinueSignature('Cliente', {
    ...emptySignatureCapture(),
    dataUrl: 'data:image/png;base64,empty-bitmap',
  }), false);
});

test('a tap or negligible movement does not count as a signature', () => {
  assert.equal(canContinueSignature('Cliente', {
    dataUrl: 'data:image/png;base64,tap',
    hasDrawing: true,
    strokes: [[{ x: 0.5, y: 0.5 }]],
  }), false);
  assert.equal(canContinueSignature('Cliente', {
    dataUrl: 'data:image/png;base64,tiny',
    hasDrawing: true,
    strokes: [[{ x: 0.5, y: 0.5 }, { x: 0.502, y: 0.502 }]],
  }), false);
  assert.equal(canContinueSignature('Cliente', drawn()), true);
});

test('clearing invalidates drawing, strokes and data URL', () => {
  assert.deepEqual(emptySignatureCapture(), { dataUrl: '', hasDrawing: false, strokes: [] });
  assert.equal(canContinueSignature('Cliente', emptySignatureCapture()), false);
});

test('a whitespace-only signer name is invalid', () => {
  assert.equal(canContinueSignature('   ', drawn()), false);
  assert.equal(validateSignatureSubmission(validSubmission({ clientName: '   ' })), 'Escribe el nombre del cliente.');
});

test('a trimmed name and a real stroke allow progression', () => {
  assert.equal(canContinueSignature('  Cliente  ', drawn()), true);
});

test('a capture from work-order group A is rejected for group B', () => {
  assert.equal(
    validateSignatureSubmission(validSubmission({ capturedContextId: 10, currentContextId: 20 })),
    'El grupo activo cambió. Captura nuevamente las firmas.',
  );
});

test('a missing active context rejects a stale capture after close or reopen', () => {
  assert.equal(
    validateSignatureSubmission(validSubmission({ currentContextId: null })),
    'El grupo activo cambió. Captura nuevamente las firmas.',
  );
});

test('both client and technician require an explicit real drawing', () => {
  assert.equal(
    validateSignatureSubmission(validSubmission({ clientCapture: emptySignatureCapture() })),
    'Captura la firma del cliente.',
  );
  assert.equal(
    validateSignatureSubmission(validSubmission({ technicianCapture: emptySignatureCapture() })),
    'Captura la firma del técnico.',
  );
});

test('payload keeps the LAB contract and trims both signer names', () => {
  assert.deepEqual(createSignaturePayload('  Cliente ', drawn(), ' Técnico  ', drawn()), {
    client: { signer_name: 'Cliente', signature_data_url: drawn().dataUrl },
    technician: { signer_name: 'Técnico', signature_data_url: drawn().dataUrl },
  });
});

test('submission lock rejects a double tap and can be released for retry', () => {
  const lock = new SignatureSubmissionLock();
  assert.equal(lock.begin(), true);
  assert.equal(lock.begin(), false);
  assert.equal(lock.isSubmitting, true);
  lock.finish();
  assert.equal(lock.begin(), true);
});

test('logical submitting state blocks validation before a second POST', () => {
  assert.equal(
    validateSignatureSubmission(validSubmission({ isSubmitting: true })),
    'Las firmas ya se están guardando.',
  );
});

test('a complete capture in the same group passes final validation', () => {
  assert.equal(validateSignatureSubmission(validSubmission()), null);
});
