import assert from 'node:assert/strict';
import test from 'node:test';

import {
  canIssueInvoiceAfterPayment,
  createInvoicePaymentDraft,
  toInvoicePaymentPayload,
  validateInvoicePaymentDraft,
} from './invoicePaymentForm.js';

test('inicializa el importe con el saldo pendiente', () => {
  const draft = createInvoicePaymentDraft(
    { balance_due: '125.40', payment_method: 'PUE', payment_form: '03' },
    new Date('2026-07-29T12:00:00Z')
  );
  assert.equal(draft.amount, '125.40');
  assert.equal(draft.paid_on, '2026-07-29');
});

test('rechaza cero, negativos y pagos mayores al saldo', () => {
  assert.match(validateInvoicePaymentDraft({ paid_on: '2026-07-29', amount: 0 }, 100), /mayor que cero/);
  assert.match(validateInvoicePaymentDraft({ paid_on: '2026-07-29', amount: -1 }, 100), /mayor que cero/);
  assert.match(validateInvoicePaymentDraft({ paid_on: '2026-07-29', amount: 101 }, 100), /saldo pendiente/);
});

test('crea únicamente el payload aceptado por InvoicePaymentCreate', () => {
  const payload = toInvoicePaymentPayload({
    paid_on: '2026-07-29',
    amount: '80.50',
    bank_name: ' Banco ',
    bank_account: '',
    reference: 'ABC',
    payment_method: 'PUE',
    payment_form: '03',
    notes: '',
  });
  assert.deepEqual(payload, {
    paid_on: '2026-07-29',
    amount: 80.5,
    bank_name: 'Banco',
    bank_account: null,
    reference: 'ABC',
    payment_method: 'PUE',
    payment_form: '03',
    notes: null,
  });
});

test('mantiene habilitable el timbrado tras un pago previo', () => {
  assert.equal(canIssueInvoiceAfterPayment({ status: 'partially_paid' }), true);
  assert.equal(canIssueInvoiceAfterPayment({ status: 'paid' }), true);
  assert.equal(canIssueInvoiceAfterPayment({ status: 'paid', cfdi_uuid: 'uuid' }), false);
  assert.equal(canIssueInvoiceAfterPayment({ status: 'cancelled' }), false);
});
