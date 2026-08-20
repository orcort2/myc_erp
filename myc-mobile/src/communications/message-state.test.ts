import assert from 'node:assert/strict';
import test from 'node:test';

import { applyMessageToConversations, deliveryState, markMessageFailed, reconcileMessages } from './message-state';
import type { CommunicationConversation, CommunicationMessage } from '@/src/types/communication';

function message(values: Partial<CommunicationMessage> = {}): CommunicationMessage {
  return {
    id: 0,
    conversation_id: 3,
    client_message_id: 'client-12345678',
    sequence: 0,
    body: 'Hola',
    message_type: 'text',
    created_at: '2026-08-17T12:00:00Z',
    edited_at: null,
    sender: { id: 1, full_name: 'Ana', email: null },
    receipts: [],
    mentions: [],
    delivery_state: 'sending',
    ...values,
  };
}

test('optimistic, REST and realtime copies reconcile into one server message', () => {
  const optimistic = message();
  const confirmed = message({ id: 50, sequence: 8, delivery_state: 'sent' });
  const result = reconcileMessages([optimistic], [confirmed, confirmed]);
  assert.equal(result.length, 1);
  assert.equal(result[0].id, 50);
  assert.equal(result[0].sequence, 8);
  assert.equal(result[0].delivery_state, 'sent');
});

test('failed messages remain retryable and receipts derive delivered/read', () => {
  const failed = markMessageFailed([message()], 'client-12345678')[0];
  assert.equal(deliveryState(failed, 1), 'failed');
  const delivered = message({
    delivery_state: 'sent',
    receipts: [{ user_id: 2, delivered_at: '2026-08-17T12:01:00Z', read_at: null }],
  });
  assert.equal(deliveryState(delivered, 1), 'delivered');
  assert.equal(deliveryState({
    ...delivered,
    receipts: [{ user_id: 2, delivered_at: '2026-08-17T12:01:00Z', read_at: '2026-08-17T12:02:00Z' }],
  }, 1), 'read');
});

function conversation(values: Partial<CommunicationConversation> = {}): CommunicationConversation {
  return {
    id: 3,
    conversation_type: 'internal',
    title: 'Ana',
    ticket_id: null,
    participants: [],
    last_message: message({ id: 40, sequence: 5, body: 'Hola' }),
    last_message_at: '2026-08-17T12:00:00Z',
    latest_sequence: 5,
    unread_count: 0,
    created_at: '2026-08-01T00:00:00Z',
    ...values,
  };
}

// BUG 1: the own sender's conversation preview used to only update once the
// realtime echo of message.created arrived. applyMessageToConversations is
// the shared helper now used both right after a successful POST (so the
// sender sees their own preview update immediately) and by the realtime
// listener (so a remote sender's preview still updates as before).
test('a confirmed own message updates last_message/last_message_at/latest_sequence without touching unread', () => {
  const sent = message({ id: 41, sequence: 6, body: 'Mensaje nuevo', sender: { id: 1, full_name: 'Ana', email: null } });
  const [updated] = applyMessageToConversations([conversation({ unread_count: 2 })], sent, 1, 3);
  assert.equal(updated.last_message?.body, 'Mensaje nuevo');
  assert.equal(updated.last_message_at, sent.created_at);
  assert.equal(updated.latest_sequence, 6);
  assert.equal(updated.unread_count, 2);
});

test('a remote message outside the active conversation increments unread', () => {
  const remote = message({ id: 42, sequence: 6, sender: { id: 2, full_name: 'Luis', email: null } });
  const [updated] = applyMessageToConversations([conversation({ unread_count: 1 })], remote, 1, null);
  assert.equal(updated.unread_count, 2);
});

test('a remote message inside the currently open conversation does not increment unread', () => {
  const remote = message({ id: 43, sequence: 6, sender: { id: 2, full_name: 'Luis', email: null } });
  const [updated] = applyMessageToConversations([conversation({ unread_count: 0 })], remote, 1, 3);
  assert.equal(updated.unread_count, 0);
});

test('conversations re-sort by last_message_at descending after the update', () => {
  const older = conversation({ id: 3, last_message_at: '2026-08-17T09:00:00Z', latest_sequence: 1 });
  const other = conversation({ id: 9, last_message_at: '2026-08-17T10:00:00Z', latest_sequence: 1 });
  const incoming = message({ id: 44, conversation_id: 3, sequence: 2, created_at: '2026-08-17T11:00:00Z' });
  const result = applyMessageToConversations([older, other], incoming, 1, null);
  assert.deepEqual(result.map((item) => item.id), [3, 9]);
});

test('re-applying the same (already-reflected) message is a safe no-op — the realtime echo case', () => {
  const sent = message({ id: 41, sequence: 6, body: 'Mensaje nuevo', sender: { id: 1, full_name: 'Ana', email: null } });
  const afterPost = applyMessageToConversations([conversation({ unread_count: 0 })], sent, 1, 3);
  // The realtime echo of the very same message arrives later, once the
  // technician has already navigated away from the conversation.
  const echo = applyMessageToConversations(afterPost, sent, 1, null);
  assert.equal(echo[0].unread_count, 0);
  assert.equal(echo[0].last_message?.body, 'Mensaje nuevo');
  assert.equal(echo[0].latest_sequence, 6);
});

test('a stale/out-of-order message does not regress an already-newer preview', () => {
  const current = [conversation({ last_message_at: '2026-08-17T12:00:00Z', latest_sequence: 8 })];
  const stale = message({ id: 39, sequence: 5, body: 'Mensaje anterior', created_at: '2026-08-17T11:00:00Z' });
  const [updated] = applyMessageToConversations(current, stale, 1, null);
  assert.equal(updated.latest_sequence, 8);
  assert.equal(updated.last_message?.body, 'Hola');
});

test('a message for a conversation not in the current list is a no-op (list unchanged)', () => {
  const current = [conversation({ id: 3 })];
  const elsewhere = message({ id: 45, conversation_id: 999, sequence: 1 });
  const result = applyMessageToConversations(current, elsewhere, 1, null);
  assert.deepEqual(result, current);
});
