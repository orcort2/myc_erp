import type { CommunicationConversation, CommunicationMessage, MessageDeliveryState } from '@/src/types/communication';

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

/**
 * Applies a confirmed message (own POST response or realtime message.created)
 * to the conversation list's preview fields and re-sorts by recency. Shared
 * by both call sites so the own-sender's preview updates immediately after
 * sending, without waiting for the realtime echo of that same message.
 *
 * Idempotent by `sequence`: a message whose sequence has already been
 * reflected in `latest_sequence` (e.g. the realtime echo arriving after the
 * POST response already applied it) is a no-op — this is what lets the echo
 * land safely without double-counting unread_count or regressing the
 * preview. Optimistic messages (sequence 0) are never applied here; only
 * confirmed/server messages carry a real sequence.
 */
export function applyMessageToConversations(
  conversations: CommunicationConversation[],
  message: CommunicationMessage,
  currentUserId: number | undefined,
  activeConversationId: number | null,
): CommunicationConversation[] {
  const next = conversations.map((conversation) => {
    if (conversation.id !== message.conversation_id) return conversation;
    if (message.sequence > 0 && message.sequence <= conversation.latest_sequence) return conversation;

    const isOwnMessage = message.sender.id === currentUserId;
    const isActiveConversation = conversation.id === activeConversationId;
    return {
      ...conversation,
      last_message: message,
      last_message_at: message.created_at,
      latest_sequence: Math.max(conversation.latest_sequence, message.sequence),
      unread_count: !isOwnMessage && !isActiveConversation
        ? conversation.unread_count + 1
        : conversation.unread_count,
    };
  });
  return next.sort((left, right) => (right.last_message_at ?? '').localeCompare(left.last_message_at ?? ''));
}
