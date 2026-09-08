import assert from 'node:assert/strict';
import test from 'node:test';

import { canSkipSignaturesAfterReopen } from './lab-work-order-signature-policy';

function base() {
  return {
    signature_preserved: true,
    signature_required: false,
    signature_session_id: 5,
  };
}

test('a preserved reopening with its valid historical session skips signature capture', () => {
  assert.equal(canSkipSignaturesAfterReopen(base()), true);
});

// Corrección 2026-09-08: la reapertura directa de Admin (reopen_work_order_directly,
// sin ticket) deja reopen_ticket_id en null a propósito -- este predicado ya
// no depende de ese campo, así que el mismo estado que produce una
// reapertura directa (signature_preserved/required/session_id idénticos a
// una mediada por ticket, pero sin ticket) debe poder saltar la captura
// igual de bien.
test('a directly-reopened work order (no ticket) with a preserved signature also skips signature capture', () => {
  const directlyReopened: { reopen_ticket_id: number | null } & ReturnType<typeof base> = { ...base(), reopen_ticket_id: null };
  assert.equal(canSkipSignaturesAfterReopen(directlyReopened), true);
});

test('a later backend invalidation restores the normal signature flow automatically', () => {
  const initiallyPreserved = base();
  assert.equal(canSkipSignaturesAfterReopen(initiallyPreserved), true);
  assert.equal(canSkipSignaturesAfterReopen({ ...initiallyPreserved, signature_required: true }), false);
});

test('signature_preserved false (e.g. a "discard" reopening) always needs new signatures', () => {
  assert.equal(canSkipSignaturesAfterReopen({ ...base(), signature_preserved: false }), false);
});

test('a structural change that invalidated the session (no signature_session_id) needs new signatures', () => {
  assert.equal(canSkipSignaturesAfterReopen({ ...base(), signature_session_id: null }), false);
});
