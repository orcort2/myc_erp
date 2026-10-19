import assert from 'node:assert/strict';
import test from 'node:test';

import { buildQuotationContact, communicationsConversationPath, phoneHref, validEmail } from './quotationContact.js';

test('there is no contact unless the quotation has contact_id', () => {
  assert.equal(buildQuotationContact({ contact_id: null, contact_name: 'Ignorado' }, null), null);
  assert.equal(buildQuotationContact({}, { commercial_name: 'X' }), null);
});

test('contact exposes call and mail actions only for valid data', () => {
  const contact = buildQuotationContact(
    {
      contact_id: 4,
      contact_name: 'Luis Pérez',
      contact_position: 'Mantenimiento',
      contact_email: 'luis.perez@xyz.com',
      contact_phone: '(33) 1234-5678',
    },
    { commercial_name: 'XYZ' },
  );
  assert.equal(contact.company, 'XYZ');
  assert.equal(contact.mailto, 'mailto:luis.perez@xyz.com');
  assert.equal(contact.tel, 'tel:3312345678');

  const incomplete = buildQuotationContact(
    { contact_id: 4, contact_name: 'Ana', contact_email: 'no-es-correo', contact_phone: '12' },
    null,
  );
  assert.equal(incomplete.mailto, null);
  assert.equal(incomplete.tel, null);
});

test('phone and email validators', () => {
  assert.equal(phoneHref('+52 33 1234 5678'), 'tel:+523312345678');
  assert.equal(phoneHref(''), null);
  assert.equal(validEmail(' a@b.co '), 'a@b.co');
  assert.equal(validEmail('a@b'), null);
});

test('communications path uses the real conversation_id contract', () => {
  assert.equal(communicationsConversationPath({ id: 9 }), '/communications?conversation_id=9');
  assert.equal(communicationsConversationPath(null), null);
});
