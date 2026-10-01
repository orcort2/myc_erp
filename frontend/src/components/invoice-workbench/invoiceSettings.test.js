import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import { toInvoiceSettingsPayload } from './invoiceSettings.js';

test('settings payload omits operational numbering and response metadata', () => {
  const editable = {
    default_tax_rate: 16, default_currency: 'USD', default_credit_days: 30,
    emitter_data: { legal_name: 'MYC' }, billing_emails: { items: ['billing@example.test'] },
  };
  assert.deepEqual(toInvoiceSettingsPayload({
    ...editable, id: 1, key: 'default', default_series: 'F', next_sequence: 8,
    reset_annually: true, allow_manual_folio: true,
  }), editable);
});

test('BillingPage exposes numbering as read-only and controller uses the write payload', () => {
  const page = readFileSync(new URL('../../pages/BillingPage.jsx', import.meta.url), 'utf8');
  for (const field of ['default_series', 'next_sequence']) {
    const input = page.match(new RegExp(`<input[^>]*settings\\.${field}[^>]*>`))?.[0];
    assert.ok(input, field);
    assert.match(input, /readOnly/);
    assert.doesNotMatch(input, /onChange/);
    assert.doesNotMatch(page, new RegExp(`${field}:\\s*event`));
  }
  const controller = readFileSync(new URL('./useInvoiceWorkbenchController.js', import.meta.url), 'utf8');
  assert.match(controller, /updateInvoiceSettings\(toInvoiceSettingsPayload\(settings\)\)/);
});
