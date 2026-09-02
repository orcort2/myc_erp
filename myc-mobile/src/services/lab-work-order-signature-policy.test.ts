import assert from 'node:assert/strict';
import test from 'node:test';

import { canSkipSignaturesAfterReopen } from './lab-work-order-signature-policy';

function base() {
  return {
    reopen_ticket_id: 9,
    signature_preserved: true,
    signature_required: false,
    signature_session_id: 5,
  };
}

test('a preserved reopening with its valid historical session skips signature capture', () => {
  assert.equal(canSkipSignaturesAfterReopen(base()), true);
});

test('a brand-new (non-reopened) work order always needs signatures', () => {
  assert.equal(canSkipSignaturesAfterReopen({ ...base(), reopen_ticket_id: null }), false);
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
