import assert from 'node:assert/strict';
import test from 'node:test';

import {
  buildInvoiceWorkbenchPath,
  normalizeInvoiceWorkbenchContext,
  readInvoiceWorkbenchContext,
} from './invoiceWorkbenchContext.js';

test('normalizes explicit invoice context with precedence', () => {
  assert.deepEqual(
    normalizeInvoiceWorkbenchContext({ invoice_id: '7', service_order_id: '4' }),
    { invoice_id: 7 }
  );
});

test('builds and reads service order context without local storage', () => {
  const path = buildInvoiceWorkbenchPath({ service_order_id: 12 });
  assert.equal(path, '/dashboard?service_order_id=12#facturacion');
  assert.deepEqual(
    readInvoiceWorkbenchContext({ search: '?service_order_id=12' }),
    { service_order_id: 12 }
  );
});

test('rejects invalid context values', () => {
  assert.equal(normalizeInvoiceWorkbenchContext({ invoice_id: '0' }), null);
  assert.equal(buildInvoiceWorkbenchPath({ invoice_id: 'invalid' }), '/dashboard#facturacion');
});
