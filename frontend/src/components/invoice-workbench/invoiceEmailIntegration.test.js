import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const read = (path) => readFileSync(
  new URL(path, import.meta.url),
  'utf8'
);

test('invoice email permission reaches the invoice detail', () => {
  const billing = read('../../pages/BillingPage.jsx');
  const dialog = read('./InvoiceWorkbenchDialog.jsx');
  const detail = read('./InvoiceDetailView.jsx');

  assert.match(billing, /hasPermission\(user, 'invoices\.email\.send'\)/);
  assert.match(billing, /canEmailInvoices=\{canEmailInvoices\}/);
  assert.match(dialog, /canEmailInvoices=\{canEmailInvoices\}/);
  assert.match(detail, /canEmailInvoices &&/);
});

test('invoice email modal opens with the selected invoice', () => {
  const detail = read('./InvoiceDetailView.jsx');

  assert.match(detail, /<InvoiceEmailModal/);
  assert.match(detail, /invoiceId=\{invoice\.id\}/);
  assert.match(detail, /setEmailModalOpen\(true\)/);
});

test('invoice email uses contextual API endpoints', () => {
  const api = read('../../services/api.js');

  for (const endpoint of ['preview', 'send', 'deliveries']) {
    assert.ok(
      api.includes('/email/' + endpoint),
      'Missing endpoint: ' + endpoint
    );
  }
});

test('invoice email requires current preview before sending', () => {
  const modal = read('./InvoiceEmailModal.jsx');

  assert.match(modal, /useRef\(createVersionGate\(\)\)/);
  assert.match(modal, /previewCurrent/);
  assert.match(modal, /canSendEmail\(/);
  assert.match(modal, /sandbox=""/);
  assert.match(modal, /sendInvoiceEmail\(invoiceId, payload\)/);
});

test('invoice email distinguishes draft and fiscal attachments', () => {
  const modal = read('./InvoiceEmailModal.jsx');

  assert.match(modal, /document_mode === 'draft'/);
  assert.match(modal, /application\/xml/);
  assert.match(modal, /application\/pdf/);
});


test('invoice email ignores obsolete send responses', () => {
  const modal = read('./InvoiceEmailModal.jsx');

  const sendStart = modal.indexOf('  async function send() {');
  const sendEnd = modal.indexOf('\n  const suggestions =', sendStart);

  assert.ok(sendStart >= 0);
  assert.ok(sendEnd > sendStart);

  const sendHandler = modal.slice(sendStart, sendEnd);

  assert.match(sendHandler, /const version = gate\.current\.next\(\)/);
  assert.match(sendHandler, /await sendInvoiceEmail\(invoiceId, payload\)/);

  assert.match(
    sendHandler,
    /if \(!gate\.current\.isCurrent\(version\)\) return;\s*setResult\(outcome\)/
  );

  assert.match(
    sendHandler,
    /if \(!gate\.current\.isCurrent\(version\)\) return;\s*setError\(requestError\.message\)/
  );

  assert.match(
    sendHandler,
    /finally\s*\{\s*if \(gate\.current\.isCurrent\(version\)\)\s*\{\s*setIsSending\(false\)/
  );
});

test('changing invoices resets sending state and invalidates requests', () => {
  const modal = read('./InvoiceEmailModal.jsx');

  const effectStart = modal.indexOf('  useEffect(() => {');
  const effectEnd = modal.indexOf('  }, [invoiceId]);', effectStart);

  assert.ok(effectStart >= 0);
  assert.ok(effectEnd > effectStart);

  const effect = modal.slice(effectStart, effectEnd);

  assert.match(effect, /gate\.current\.next\(\)/);
  assert.match(effect, /setIsSending\(false\)/);
  assert.match(effect, /gate\.current\.invalidate\(\)/);
});
