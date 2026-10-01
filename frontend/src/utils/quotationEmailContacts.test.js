import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

import { clientModalTabs } from '../constants/templates.js';
import { hasPermission } from './accessControl.js';
import { toClientCreatePayload, toClientPayload } from './clients.js';
import { emptyClientForm } from '../constants/forms.js';
import { contactIdAfterClientChange, contactIdPayload, contactOptionsForClient } from './quotationContacts.js';
import {
  addManualRecipient,
  buildSendPayload,
  isValidEmail,
  sendResultMessage,
  toggleRecipient
} from './quotationEmail.js';

const source = (relative) => readFileSync(new URL(relative, import.meta.url), 'utf8');
const clientsPage = source('../pages/ClientsPage.jsx');
const quotationsPage = source('../pages/QuotationsPage.jsx');
const panel = source('../components/ClientContactsPanel.jsx');
const modal = source('../components/QuotationEmailModal.jsx');
const history = source('../components/QuotationEmailHistory.jsx');
const api = source('../services/api.js');

const xyz = {
  id: 1,
  contacts: [
    { id: 10, name: 'Luis Pérez', position: 'Mantenimiento', email: 'luis@xyz.com', is_active: true },
    { id: 11, name: 'Ana López', email: 'ana@xyz.com', is_active: true },
    { id: 12, name: 'Baja', email: 'baja@xyz.com', is_active: false }
  ]
};

// ---- clients -------------------------------------------------------------
test('client modal has a Contactos tab next to Datos generales', () => {
  assert.deepEqual(clientModalTabs.slice(0, 2).map((tab) => tab.key), ['general', 'contacts']);
  assert.match(clientsPage, /clientModalTab === 'contacts'/);
  assert.match(clientsPage, /<ClientContactsPanel/);
});

test('contacts panel lists, creates, edits and toggles active state through contact endpoints', () => {
  for (const fn of ['listClientContacts', 'createClientContact', 'updateClientContact', 'deactivateClientContact', 'restoreClientContact']) {
    assert.match(panel, new RegExp(fn));
    assert.match(api, new RegExp(`export function ${fn}`));
  }
  assert.match(panel, /Nuevo contacto/);
  assert.match(panel, /Editar/);
  assert.match(panel, /'Activo' : 'Inactivo'/);
  assert.match(panel, /Desactivar/);
  assert.match(panel, /Reactivar/);
  assert.match(api, /\/clients\/\$\{clientId\}\/contacts\/\$\{contactId\}`, \{ method: 'DELETE' \}/);
});

test('editing a client never resends the contacts list and never mixes the general email into a contact', () => {
  const form = { ...emptyClientForm, legalName: 'XYZ', commercialName: 'XYZ', email: 'general@xyz.com', phone: '33', contactName: 'Ana' };
  assert.equal('contacts' in toClientPayload(form, { includeContacts: false }), false);
  const created = toClientCreatePayload(form);
  assert.deepEqual(created.contacts, [{ name: 'Ana', email: null, phone: null, position: null }]);
  assert.equal(created.email, 'general@xyz.com');
  assert.match(clientsPage, /toClientPayload\(form, \{ includeContacts: false \}\)/);
});

// ---- quotation contact ----------------------------------------------------
test('contact selector shows only the client contacts and keeps an inactive assigned one readable', () => {
  const options = contactOptionsForClient(xyz, '');
  assert.deepEqual(options.map((o) => o.value), ['10', '11']);
  assert.equal(options[0].label, 'Luis Pérez · Mantenimiento · luis@xyz.com');
  assert.deepEqual(contactOptionsForClient(xyz, '12').map((o) => o.value), ['10', '11', '12']);
  assert.match(contactOptionsForClient(xyz, '12')[2].label, /\(inactivo\)/);
  assert.deepEqual(contactOptionsForClient(null, ''), []);
  assert.match(quotationsPage, /Sin contacto específico/);
  assert.match(quotationsPage, /contactOptionsForClient\(/);
});

test('changing client clears a stale contact; payload sends null for "no contact"', () => {
  const other = { id: 2, contacts: [{ id: 20, name: 'Otro', is_active: true }] };
  assert.equal(contactIdAfterClientChange(other, '10'), '');
  assert.equal(contactIdAfterClientChange(xyz, '10'), '10');
  assert.equal(contactIdAfterClientChange(xyz, '12'), '');
  assert.equal(contactIdPayload(''), null);
  assert.equal(contactIdPayload('10'), 10);
  assert.match(quotationsPage, /contact_id: contactIdPayload\(detailForm\.contactId\)/);
  assert.match(quotationsPage, /contactId: String\(updated\.contact_id \?\? ''\)/);
});

// ---- email modal -----------------------------------------------------------
test('send button and Correos tab depend on permissions', () => {
  const comercial = { permissions: ['quotations.email.send', 'email.deliveries.read', 'quotations.read'] };
  assert.equal(hasPermission(comercial, 'quotations.email.send'), true);
  assert.equal(hasPermission({ permissions: ['quotations.read'] }, 'quotations.email.send'), false);
  assert.match(quotationsPage, /canEmailQuotations = hasPermission\(effectiveUser, 'quotations\.email\.send'\)/);
  assert.match(quotationsPage, /\{canEmailQuotations \? \([\s\S]{0,200}?Enviar por correo/);
});

test('manual TO/CC recipients: validation, multiple entries and case-insensitive dedupe', () => {
  assert.equal(isValidEmail('otro@empresa.com'), true);
  assert.equal(isValidEmail('no-valido'), false);
  assert.equal(isValidEmail('a@b.com\r\nBcc: x@y.com'), false);
  let list = [];
  list = addManualRecipient(list, 'uno@empresa.com').list;
  list = addManualRecipient(list, 'DOS@empresa.com').list;
  list = addManualRecipient(list, 'UNO@empresa.com').list;
  assert.deepEqual(list, ['uno@empresa.com', 'DOS@empresa.com']);
  assert.match(addManualRecipient(list, 'mal').error, /válida/);
  assert.deepEqual(toggleRecipient(list, 'UNO@empresa.com'), ['DOS@empresa.com']);
  assert.match(modal, /aria-label=\{inputLabel\}/);
  assert.match(modal, /label="Para"/);
  assert.match(modal, /label="CC"/);
});

test('send payload carries only recipients, TO wins over CC and nothing is duplicated', () => {
  assert.deepEqual(
    buildSendPayload(['a@x.com', 'A@x.com', 'b@x.com'], ['b@x.com', 'c@x.com', 'C@x.com']),
    { to: ['a@x.com', 'b@x.com'], cc: ['c@x.com'] }
  );
  assert.match(api, /JSON\.stringify\(\{ to, cc \}\)/);
  const sendFn = api.slice(api.indexOf('export function sendQuotationEmail'), api.indexOf('export function listQuotationEmailDeliveries'));
  assert.doesNotMatch(sendFn, /subject|body_html|attachments/);
});

test('modal previews backend subject/message/PDF read-only and never claims delivery', () => {
  assert.match(modal, /preview\.subject/);
  assert.match(modal, /srcDoc=\{preview\.body_html\}/);
  assert.match(modal, /sandbox=""/);
  assert.match(modal, /PDF oficial/);
  assert.doesNotMatch(modal, /<textarea|contentEditable/);
  assert.equal(sendResultMessage({ sent: true }), 'El relay aceptó el correo para envío.');
  assert.equal(sendResultMessage({ sent: false }), 'No fue posible enviar el correo.');
  assert.doesNotMatch(modal + history, /recibi[óo] el correo|entregado|le[ií]do/i);
});

test('history is contextual and "Reenviar" re-runs the contextual flow (no generic retry)', () => {
  assert.match(api, /\/quotations\/\$\{quotationId\}\/email\/deliveries/);
  assert.match(history, /delivery\.status === 'failed' && canResend/);
  assert.match(history, /Reenviar/);
  assert.match(quotationsPage, /onResend=\{\(\) => setIsEmailModalOpen\(true\)\}/);
  assert.doesNotMatch(history + modal + api, /\/email\/deliveries\/\$\{[^}]+\}\/retry/);
  assert.match(quotationsPage, /\['emails', 'Correos'\]/);
});

test('Correos tab depends only on email.deliveries.read; Enviar por correo only on quotations.email.send', () => {
  assert.match(quotationsPage, /\.\.\.\(canReadQuotationEmails \? \[\['emails', 'Correos'\]\] : \[\]\)/);
  assert.doesNotMatch(quotationsPage, /canReadQuotationEmails \|\| canEmailQuotations/);
  assert.match(quotationsPage, /canReadQuotationEmails =\s*hasPermission\(effectiveUser, 'email\.deliveries\.read'\)/);
  const sender = { permissions: ['quotations.email.send', 'quotations.read'] };
  assert.equal(hasPermission(sender, 'quotations.email.send'), true);
  assert.equal(hasPermission(sender, 'email.deliveries.read'), false);
  // resend inside the history still needs the send permission
  assert.match(quotationsPage, /canResend=\{canEmailQuotations\}/);
});

test('quotation contact is labelled as the quotation contact and the client picker falls back coherently', () => {
  assert.match(quotationsPage, /Contacto de la cotización/);
  assert.doesNotMatch(quotationsPage, /Contacto principal/);
  assert.match(quotationsPage, /Sin contacto específico/);
  assert.match(quotationsPage, /contact\?\.name \|\| contact\?\.email \|\| client\.email \|\| 'Sin contacto registrado'/);
  assert.doesNotMatch(quotationsPage, /Sin contacto principal/);
});

test('manual recipients, read-only sandboxed preview and non-delivery wording survive the redesign', () => {
  assert.match(modal, /addManualRecipient/);
  assert.match(modal, /event\.key === 'Enter'/);
  assert.match(modal, /<iframe[^>]*sandbox=""/);
  assert.doesNotMatch(modal, /dangerouslySetInnerHTML|<textarea/);
  assert.match(modal, /Vista previa/);
  assert.match(modal, /PDF oficial/);
  assert.equal(sendResultMessage({ sent: true }), 'El relay aceptó el correo para envío.');
  assert.doesNotMatch(modal + history, /cliente recibi[óo]|entregado|le[ií]do/i);
});
