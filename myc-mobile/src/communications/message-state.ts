import type { CommunicationMessage, MessageDeliveryState } from '@/src/types/communication';

function key(message: CommunicationMessage): string {
  return message.client_message_id
    ? `client:${message.client_message_id}`
    : `server:${message.id}`;
}

export function deliveryState(
  message: CommunicationMessage,
  currentUserId: number,
): MessageDeliveryState {
  if (message.delivery_state === 'sending' || message.delivery_state === 'failed') {
    return message.delivery_state;
  }
  if (message.sender.id !== currentUserId) return 'read';
  const recipients = message.receipts.filter((receipt) => receipt.user_id !== currentUserId);
  if (recipients.some((receipt) => receipt.read_at)) return 'read';
  if (recipients.some((receipt) => receipt.delivered_at)) return 'delivered';
  return 'sent';
}

export function reconcileMessages(
  current: CommunicationMessage[],
  incoming: CommunicationMessage[],
): CommunicationMessage[] {
  const byKey = new Map(current.map((message) => [key(message), message]));
  for (const message of incoming) {
    const existing = byKey.get(key(message));
    byKey.set(key(message), {
      ...existing,
      ...message,
      delivery_state: message.delivery_state ?? 'sent',
    });
  }
  return [...byKey.values()].sort((left, right) => {
    if (left.sequence === 0 || right.sequence === 0) {
      return left.created_at.localeCompare(right.created_at);
    }
    return left.sequence - right.sequence;
  });
}

export function markMessageFailed(
  messages: CommunicationMessage[], clientMessageId: string,
): CommunicationMessage[] {
  return messages.map((message) => message.client_message_id === clientMessageId
    ? { ...message, delivery_state: 'failed' }
    : message);
}
