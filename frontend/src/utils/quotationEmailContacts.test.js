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
  canSendEmail,
  createVersionGate,
  isValidEmail,
  selectInCc,
  selectInTo,
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
const css = source('../styles/global.css');

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
  assert.match(quotationsPage, /onResend=\{\(delivery\) => setEmailModal\(\{ initialTo: delivery\.to, initialCc: delivery\.cc \}\)\}/);
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

// ---- preview consistency (race + stale preview) --------------------------------
test('an older preview answer never overwrites the newest one', async () => {
  const gate = createVersionGate();
  let shown = null;
  const answer = (label, version, delay) =>
    new Promise((resolve) => setTimeout(resolve, delay)).then(() => {
      if (gate.isCurrent(version)) shown = label;
    });
  const a = gate.next(); // TO = Ana (slow)
  const b = gate.next(); // TO = Luis (fast, finishes first)
  await Promise.all([answer('Ana', a, 20), answer('Luis', b, 1)]);
  assert.equal(shown, 'Luis');
  gate.invalidate(); // modal closed / selection emptied
  assert.equal(gate.isCurrent(b), false);
  assert.match(modal, /if \(!gate\.current\.isCurrent\(version\)\) return;/);
  assert.match(modal, /useRef\(createVersionGate\(\)\)/);
});

test('Enviar is disabled while loading, refreshing, sending, stale or without TO', () => {
  const ok = { isLoading: false, isSending: false, isRefreshingPreview: false, previewCurrent: true, to: ['a@x.com'] };
  assert.equal(canSendEmail(ok), true);
  for (const patch of [{ isLoading: true }, { isSending: true }, { isRefreshingPreview: true }, { previewCurrent: false }, { to: [] }]) {
    assert.equal(canSendEmail({ ...ok, ...patch }), false, JSON.stringify(patch));
  }
});

test('a failed preview refresh keeps the old preview unsendable and states are separated', () => {
  const refresh = modal.slice(modal.indexOf('async function refreshPreview'), modal.indexOf('function changeSelection'));
  assert.match(refresh, /setPreviewCurrent\(false\)/);
  const catchBlock = refresh.slice(refresh.indexOf('catch'));
  assert.doesNotMatch(catchBlock.slice(0, catchBlock.indexOf('finally')), /setPreviewCurrent\(true\)/);
  assert.match(modal, /const \[isLoading, setIsLoading\]/);
  assert.match(modal, /const \[isRefreshingPreview, setIsRefreshingPreview\]/);
  assert.match(modal, /const \[isSending, setIsSending\]/);
  assert.match(modal, /disabled=\{isSending\} onClick=\{onClose\}/); // closing is only blocked while sending
  assert.match(modal, /disabled=\{!canSend\}/);
});

test('an address is never selected in TO and CC at once', () => {
  assert.deepEqual(selectInTo(['a@x.com'], ['b@x.com', 'C@x.com'], 'c@x.com'), { to: ['a@x.com', 'c@x.com'], cc: ['b@x.com'] });
  assert.deepEqual(selectInCc(['a@x.com'], [], 'A@x.com'), { to: ['a@x.com'], cc: [] });
  assert.deepEqual(selectInCc(['a@x.com'], [], 'z@x.com'), { to: ['a@x.com'], cc: ['z@x.com'] });
  assert.match(modal, /blocked=\{to\}/);
});

test('loading states: contacts and email history do not flash their empty states', () => {
  assert.match(panel, /const \[isLoading, setIsLoading\] = useState\(true\)/);
  assert.match(panel, /isLoading \? \(\s*<div className="clients-empty">Cargando contactos/);
  assert.match(history, /const \[isLoading, setIsLoading\] = useState\(true\)/);
  assert.match(history, /!isLoading && deliveries\.length === 0 && !error/);
});

test('Reenviar keeps the previous recipients but still regenerates everything (new delivery)', () => {
  assert.match(history, /onResend\(delivery\)/);
  assert.match(quotationsPage, /initialTo=\{emailModal\.initialTo \?\? null\}/);
  assert.match(modal, /initialTo\?\.length \? \{ to: initialTo, cc: initialCc \?\? \[\] \}/);
  assert.match(modal, /previewQuotationEmail\(quotationId, request\)/);
});

test('email modal is a sibling of the quotation detail modal, not nested in it', () => {
  const detailStart = quotationsPage.indexOf('{isDetailOpen && selectedQuotation ? (');
  const modalStart = quotationsPage.indexOf('<QuotationEmailModal');
  const closing = quotationsPage.indexOf('      ) : null}\n\n      {emailModal && selectedQuotation ? (');
  assert.ok(detailStart > 0 && closing > detailStart && modalStart > closing);
});

test('layout: contacts fill the modal width, document flow in the email modal, wide commercial cells', () => {
  assert.match(css, /\.client-contacts-panel \{[^}]*grid-column: 1 \/ -1;/);
  assert.doesNotMatch(css, /quotation-email__layout|quotation-email__column|5fr\) minmax\(0, 7fr/);
  assert.match(css, /\.quotation-email__recipients-grid \{[^}]*repeat\(2, minmax\(0, 1fr\)\)/);
  assert.match(css, /\.quotation-commercial-grid__wide \{\s*grid-column: span 2;/);
  assert.match(css, /\.quotation-commercial-grid select,\s*\.quotation-notes-field textarea/);
  assert.match(quotationsPage, /quotation-client-card quotation-commercial-grid__wide/);
  assert.match(css, /height: clamp\(360px, 46vh, 520px\)/);
  assert.match(css, /\.quotation-email__subject \{\s*margin: 0;/);
  assert.doesNotMatch(panel, /✉|☎/);
});

test('preview stays sandboxed and read-only', () => {
  assert.match(modal, /<iframe[^>]*sandbox=""/);
  assert.doesNotMatch(modal, /dangerouslySetInnerHTML/);
});
