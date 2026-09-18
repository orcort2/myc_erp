import assert from 'node:assert/strict';
import test from 'node:test';

import { describePendingSignatureReviewFields, describeSensitiveField } from './lab-pending-signature-review';

test('un campo general se traduce a su etiqueta de formulario', () => {
  assert.equal(describeSensitiveField('reception_date', []), 'Fecha de recepción');
  assert.equal(describeSensitiveField('client_name', []), 'Cliente');
  assert.equal(describeSensitiveField('address', []), 'Domicilio');
});

test('un campo de equipo resuelve la posición del equipo activo', () => {
  const equipment = [{ id: 42, position: 3 }];
  assert.equal(describeSensitiveField('equipment:42:instrument', equipment), 'Equipo 3 — Instrumento');
  assert.equal(describeSensitiveField('equipment:42:is_good_condition', equipment), 'Equipo 3 — Estado físico');
});

test('un campo de equipo cuyo id ya no está activo cae de vuelta a la etiqueta sin posición (nunca fabrica un dato inexistente)', () => {
  assert.equal(describeSensitiveField('equipment:999:brand', []), 'Marca');
});

test('un campo desconocido (fuera de las listas críticas actuales) se muestra tal cual, nunca se descarta en silencio', () => {
  assert.equal(describeSensitiveField('algo_nuevo', []), 'algo_nuevo');
});

test('describePendingSignatureReviewFields traduce la lista completa en el mismo orden que backend la envía', () => {
  const equipment = [{ id: 1, position: 1 }, { id: 2, position: 2 }];
  const review = { sensitive_fields: ['address', 'equipment:2:serial_number'], requires_new_signature: true };
  assert.deepEqual(describePendingSignatureReviewFields(review, equipment), ['Domicilio', 'Equipo 2 — Serie']);
});

test('sin campos sensibles, la lista sale vacía', () => {
  const review = { sensitive_fields: [], requires_new_signature: false };
  assert.deepEqual(describePendingSignatureReviewFields(review, []), []);
});
