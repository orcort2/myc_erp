import assert from 'node:assert/strict';
import test from 'node:test';

import { SignatureSubmissionLock, type SignatureCapture } from '@/src/components/signatures/signature-flow-state';
import {
  buildDeliveryPayload,
  createDeliveryWizardState,
  goToStep,
  validateContinueFromDeliveredBySignature,
  validateContinueFromRecipient,
  validateSubmitDelivery,
  type DeliveryWizardState,
} from './lab-delivery-flow-state';

const drawn = (): SignatureCapture => ({
  dataUrl: 'data:image/png;base64,valid-capture',
  hasDrawing: true,
  strokes: [[{ x: 0.1, y: 0.2 }, { x: 0.7, y: 0.8 }]],
});

function readyForDeliveredBySignature(overrides: Partial<DeliveryWizardState> = {}): DeliveryWizardState {
  return { ...goToStep(createDeliveryWizardState('María'), 'delivered_by_signature'), ...overrides };
}

function readyForSubmit(overrides: Partial<DeliveryWizardState> = {}): DeliveryWizardState {
  return {
    ...goToStep(createDeliveryWizardState('María'), 'recipient_signature'),
    deliveredByCapture: drawn(),
    recipientCapture: drawn(),
    ...overrides,
  };
}

test('el wizard siempre inicia en review', () => {
  assert.equal(createDeliveryWizardState('María').step, 'review');
});

test('review -> recipient no requiere validación (el método ya trae un default)', () => {
  const afterReview = goToStep(createDeliveryWizardState(''), 'recipient');
  assert.equal(afterReview.step, 'recipient');
  assert.equal(afterReview.deliveryMethod, 'direct');
});

test('recipient exige nombre no vacío para continuar', () => {
  const empty = createDeliveryWizardState('   ');
  assert.equal(validateContinueFromRecipient(empty), 'Escribe el nombre de quien recibe.');
  const withName = createDeliveryWizardState('María Receptora');
  assert.equal(validateContinueFromRecipient(withName), null);
});

test('recipient -> delivered_by_signature sólo avanza cuando el nombre es válido', () => {
  const next = goToStep(createDeliveryWizardState('María'), 'delivered_by_signature');
  assert.equal(next.step, 'delivered_by_signature');
});

test('la firma de quien entrega es obligatoria antes de avanzar al receptor', () => {
  const withoutSignature = readyForDeliveredBySignature();
  assert.equal(validateContinueFromDeliveredBySignature(withoutSignature), 'Captura la firma de quien entrega.');
  const withSignature = readyForDeliveredBySignature({ deliveredByCapture: drawn() });
  assert.equal(validateContinueFromDeliveredBySignature(withSignature), null);
});

test('delivered_by_signature -> recipient_signature tras firmar', () => {
  const next = goToStep(readyForDeliveredBySignature({ deliveredByCapture: drawn() }), 'recipient_signature');
  assert.equal(next.step, 'recipient_signature');
});

test('la firma del receptor es obligatoria para confirmar', () => {
  const missing = readyForSubmit({ recipientCapture: { dataUrl: '', hasDrawing: false, strokes: [] } });
  assert.equal(validateSubmitDelivery(missing), 'Captura la firma de quien recibe.');
  assert.equal(validateSubmitDelivery(readyForSubmit()), null);
});

test('volver conserva valores y capturas ya hechas (no hay reset implícito)', () => {
  const captured = readyForSubmit({ recipientName: 'Ana', notes: 'Entrega en recepción' });
  const back = goToStep(captured, 'delivered_by_signature');
  assert.equal(back.recipientName, 'Ana');
  assert.equal(back.notes, 'Entrega en recepción');
  assert.deepEqual(back.deliveredByCapture, captured.deliveredByCapture);
  assert.deepEqual(back.recipientCapture, captured.recipientCapture);
  const forwardAgain = goToStep(back, 'recipient_signature');
  assert.deepEqual(forwardAgain.recipientCapture, captured.recipientCapture);
});

test('submit sólo es válido desde el último paso (recipient_signature)', () => {
  const tooEarly = { ...createDeliveryWizardState('María'), deliveredByCapture: drawn(), recipientCapture: drawn() };
  assert.equal(validateSubmitDelivery(tooEarly), 'Completa los pasos anteriores antes de confirmar.');
  assert.equal(validateSubmitDelivery(readyForSubmit()), null);
});

test('double submit queda bloqueado por SignatureSubmissionLock hasta liberarse', () => {
  const lock = new SignatureSubmissionLock();
  assert.equal(lock.begin(), true);
  assert.equal(lock.begin(), false, 'un segundo submit concurrente debe rechazarse');
  lock.finish();
  assert.equal(lock.begin(), true, 'tras liberar, un nuevo submit sí es válido');
});

test('el payload construido usa exactamente las capturas/valores del wizard, recortando espacios', () => {
  const state = readyForSubmit({ recipientName: '  Ana López  ', notes: '  Entregado en recepción  ', deliveryMethod: 'client_pickup' });
  assert.deepEqual(buildDeliveryPayload(state), {
    delivery_method: 'client_pickup',
    delivered_by_signature_data_url: drawn().dataUrl,
    recipient_name: 'Ana López',
    recipient_signature_data_url: drawn().dataUrl,
    notes: 'Entregado en recepción',
  });
});

test('observaciones vacías se envían como null, no como cadena vacía', () => {
  const state = readyForSubmit({ notes: '   ' });
  assert.equal(buildDeliveryPayload(state).notes, null);
});
