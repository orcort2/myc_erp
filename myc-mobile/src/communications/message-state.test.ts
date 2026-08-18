import assert from 'node:assert/strict';
import test from 'node:test';

import { deliveryState, markMessageFailed, reconcileMessages } from './message-state';
import type { CommunicationMessage } from '@/src/types/communication';

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
