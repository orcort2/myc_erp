import test from 'node:test';
import assert from 'node:assert/strict';

import {
  canShowQuotationServiceException,
  formatQuotationServiceOption,
  hasQuotationExceptionPermission
} from './quotationServiceExceptions.js';


test('exception action requires an accepted quotation and explicit permission', () => {
  const user = {
    permissions: ['quotations.exceptions.request_change_service']
  };
  assert.equal(canShowQuotationServiceException({ status: 'accepted' }, user), true);
  assert.equal(canShowQuotationServiceException({ status: 'sent' }, user), false);
  assert.equal(canShowQuotationServiceException({ status: 'accepted' }, { permissions: [] }), false);
});

test('wildcard permission is accepted without exposing a technical id', () => {
  assert.equal(
    hasQuotationExceptionPermission(
      { permissions: ['*'] },
      'quotations.exceptions.authorize_change_service'
    ),
    true
  );
  assert.equal(
    formatQuotationServiceOption({
      id: 19,
      internalKey: 'SRV-CAL-002',
      name: 'Calibración trazable'
    }),
    'SRV-CAL-002 · Calibración trazable'
  );
});
