import assert from 'node:assert/strict';
import test from 'node:test';

import { clearQuotationDeepLink, findDeepLinkedQuotation, readQuotationDeepLink } from './quotationDeepLink.js';

test('reads quotation id or folio from the query string', () => {
  assert.deepEqual(readQuotationDeepLink('?quotation_id=123'), { id: 123, folio: null });
  assert.deepEqual(readQuotationDeepLink('?quotation_folio=MYC-07-26-0125&exception_folio=EXV-2026-00001'), { id: null, folio: 'MYC-07-26-0125' });
  assert.equal(readQuotationDeepLink('?quotation_id=abc'), null);
  assert.equal(readQuotationDeepLink(''), null);
});

test('finds the quotation by id first and by folio otherwise', () => {
  const rows = [{ id: 1, folio: 'A' }, { id: 2, folio: 'B' }];
  assert.equal(findDeepLinkedQuotation(rows, { id: 2, folio: null }).folio, 'B');
  assert.equal(findDeepLinkedQuotation(rows, { id: null, folio: 'A' }).id, 1);
  assert.equal(findDeepLinkedQuotation(rows, { id: 9, folio: null }), null);
});

test('clearing the deep link keeps unrelated params and the hash', () => {
  assert.equal(
    clearQuotationDeepLink('/dashboard?quotation_id=5&acceptance_id=3&tab=x#cotizaciones'),
    '/dashboard?tab=x#cotizaciones',
  );
});
