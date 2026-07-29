import test from 'node:test';
import assert from 'node:assert/strict';

import {
  canShowQuotationServiceException,
  formatQuotationServiceOption,
  hasQuotationExceptionPermission,
  normalizeLinkedCertificatePrefix,
  serviceTypeLabel,
  validateLinkedServiceFields
} from './quotationServiceExceptions.js';


test('exception action requires an accepted quotation and explicit permission', () => {
  const user = {
    permissions: ['quotations.exceptions.request_unlock']
  };
  assert.equal(canShowQuotationServiceException({ status: 'accepted' }, user), true);
  assert.equal(canShowQuotationServiceException({ status: 'sent' }, user), false);
  assert.equal(canShowQuotationServiceException({ status: 'accepted' }, { permissions: [] }), false);
});

test('wildcard permission is accepted without exposing a technical id', () => {
  assert.equal(
    hasQuotationExceptionPermission(
      { permissions: ['*'] },
      'quotations.exceptions.authorize_unlock'
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

test('formal service types have the three institutional labels', () => {
  assert.equal(serviceTypeLabel('accredited'), 'Acreditado');
  assert.equal(serviceTypeLabel('traceable'), 'Trazable');
  assert.equal(serviceTypeLabel('linked'), 'Vinculado');
});

test('linked fields are conditional and prefix validation matches backend', () => {
  assert.equal(
    validateLinkedServiceFields({
      serviceType: 'accredited',
      linkedCompanyId: '',
      linkedCompanyName: '',
      linkedCertificatePrefix: ''
    }),
    null
  );
  assert.match(
    validateLinkedServiceFields({
      serviceType: 'linked',
      linkedCompanyId: '',
      linkedCompanyName: '',
      linkedCertificatePrefix: ''
    }),
    /empresa/
  );
  assert.match(
    validateLinkedServiceFields({
      serviceType: 'linked',
      linkedCompanyId: 'other',
      linkedCompanyName: '',
      linkedCertificatePrefix: 'CMVG'
    }),
    /nombre/
  );
  assert.equal(normalizeLinkedCertificatePrefix(' cmvg '), 'CMVG');
  assert.equal(
    validateLinkedServiceFields({
      serviceType: 'linked',
      linkedCompanyId: '12',
      linkedCompanyName: '',
      linkedCertificatePrefix: 'cmvg'
    }),
    null
  );
  assert.match(
    validateLinkedServiceFields({
      serviceType: 'linked',
      linkedCompanyId: '12',
      linkedCompanyName: '',
      linkedCertificatePrefix: 'CM-VG'
    }),
    /alfanuméricos/
  );
});
