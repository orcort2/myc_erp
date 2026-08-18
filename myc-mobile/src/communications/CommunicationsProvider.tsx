import {
  createContext,
  PropsWithChildren,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';

import { useAuth } from '@/src/auth/AuthProvider';
import { markMessageFailed, reconcileMessages } from '@/src/communications/message-state';
import { useRealtime } from '@/src/realtime/RealtimeProvider';
import {
  fetchConversation,
  fetchConversations,
  fetchOlderMessages,
  markMessages,
  sendMessage as sendMessageRequest,
  syncConversation,
} from '@/src/services/communications';
import type {
  CommunicationConversation,
  CommunicationMessage,
  MentionDraft,
} from '@/src/types/communication';

type CommunicationsValue = {
  conversations: CommunicationConversation[];
  messagesByConversation: Record<number, CommunicationMessage[]>;
  beforeCursorByConversation: Record<number, number | null>;
  typingByConversation: Record<number, { user_id: number; full_name: string }[]>;
  isLoading: boolean;
  error: string | null;
  unreadCount: number;
  refreshConversations(): Promise<void>;
  openConversation(id: number): Promise<void>;
  closeConversation(id: number): void;
  loadOlder(id: number): Promise<void>;
  sendMessage(id: number, body: string, mentions?: MentionDraft[]): Promise<void>;
  retryMessage(id: number, clientMessageId: string): Promise<void>;
  notifyTyping(id: number): void;
};

const CommunicationsContext = createContext<CommunicationsValue | null>(null);

function isMessage(value: Record<string, unknown>): value is unknown & CommunicationMessage {
  return typeof value.id === 'number'
    && typeof value.conversation_id === 'number'
    && typeof value.sequence === 'number'
    && typeof value.body === 'string';
}

export function CommunicationsProvider({ children }: PropsWithChildren) {
  const { authorizedFetch, user } = useAuth();
  const { registerResynchronizer, sendCommand, subscribe } = useRealtime();
  const [conversations, setConversations] = useState<CommunicationConversation[]>([]);
  const [messagesByConversation, setMessagesByConversation] = useState<Record<number, CommunicationMessage[]>>({});
  const [beforeCursorByConversation, setBeforeCursorByConversation] = useState<Record<number, number | null>>({});
  const [typingByConversation, setTypingByConversation] = useState<Record<number, { user_id: number; full_name: string }[]>>({});
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const activeConversation = useRef<number | null>(null);
  const messagesRef = useRef(messagesByConversation);
  const processedEvents = useRef(new Set<string>());
  const typingExpiry = useRef(new Map<string, ReturnType<typeof setTimeout>>());
  const typingStop = useRef(new Map<number, ReturnType<typeof setTimeout>>());
  const typingLastSent = useRef(new Map<number, number>());
  messagesRef.current = messagesByConversation;

  const refreshConversations = useCallback(async () => {
    if (!user) return;
    try {
      const next = await fetchConversations(authorizedFetch);
      setConversations(next);
      setError(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'No fue posible actualizar Comunicaciones');
    }
  }, [authorizedFetch, user]);

  const acknowledge = useCallback(async (
    conversationId: number, messages: CommunicationMessage[], read: boolean,
  ) => {
    if (!user) return;
    const ids = messages
      .filter((message) => message.id > 0 && message.sender.id !== user.id)
      .map((message) => message.id);
    if (!ids.length) return;
    await markMessages(authorizedFetch, conversationId, ids, read ? 'read' : 'delivered');
  }, [authorizedFetch, user]);

  const openConversation = useCallback(async (id: number) => {
    setIsLoading(true);
    activeConversation.current = id;
    try {
      const detail = await fetchConversation(authorizedFetch, id);
      setMessagesByConversation((current) => ({
        ...current,
        [id]: reconcileMessages(current[id] ?? [], detail.messages),
      }));
      setBeforeCursorByConversation((current) => ({ ...current, [id]: detail.next_before_sequence }));
      setConversations((current) => {
        const without = current.filter((item) => item.id !== id);
        return [{ ...detail, unread_count: 0 }, ...without];
      });
      sendCommand('conversation.subscribe', { conversation_id: id });
      await acknowledge(id, detail.messages, true);
      setError(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'No fue posible abrir la conversación');
    } finally {
      setIsLoading(false);
    }
  }, [acknowledge, authorizedFetch, sendCommand]);

  const closeConversation = useCallback((id: number) => {
    if (activeConversation.current === id) activeConversation.current = null;
    sendCommand('typing.stopped', { conversation_id: id });
    sendCommand('conversation.unsubscribe', { conversation_id: id });
    const timer = typingStop.current.get(id);
    if (timer) clearTimeout(timer);
    typingStop.current.delete(id);
  }, [sendCommand]);

  const loadOlder = useCallback(async (id: number) => {
    const cursor = beforeCursorByConversation[id];
    if (!cursor) return;
    const page = await fetchOlderMessages(authorizedFetch, id, cursor);
    setMessagesByConversation((current) => ({
      ...current,
      [id]: reconcileMessages(page.items, current[id] ?? []),
    }));
    setBeforeCursorByConversation((current) => ({ ...current, [id]: page.next_before_sequence }));
  }, [authorizedFetch, beforeCursorByConversation]);

  const sendWithClientId = useCallback(async (
    id: number, body: string, clientMessageId: string, mentions: MentionDraft[], optimistic = true,
  ) => {
    if (!user) return;
    if (optimistic) {
      const pending: CommunicationMessage = {
        id: 0,
        conversation_id: id,
        client_message_id: clientMessageId,
        sequence: 0,
        body,
        message_type: 'text',
        created_at: new Date().toISOString(),
        edited_at: null,
        sender: { id: user.id, full_name: user.full_name, email: user.email },
        receipts: [],
        mentions: [],
        delivery_state: 'sending',
      };
      setMessagesByConversation((current) => ({
        ...current, [id]: reconcileMessages(current[id] ?? [], [pending]),
      }));
    }
    try {
      const confirmed = await sendMessageRequest(
        authorizedFetch, id, body, clientMessageId, mentions,
      );
      setMessagesByConversation((current) => ({
        ...current, [id]: reconcileMessages(current[id] ?? [], [confirmed]),
      }));
      setError(null);
    } catch (caught) {
      setMessagesByConversation((current) => ({
        ...current, [id]: markMessageFailed(current[id] ?? [], clientMessageId),
      }));
      setError(caught instanceof Error ? caught.message : 'No fue posible enviar el mensaje');
    }
  }, [authorizedFetch, user]);

  const sendMessage = useCallback(async (
    id: number, body: string, mentions: MentionDraft[] = [],
  ) => {
    if (!user || !body.trim()) return;
    const clientMessageId = `${user.id}-${Date.now()}-${Math.random().toString(36).slice(2)}`;
    await sendWithClientId(id, body.trim(), clientMessageId, mentions);
  }, [sendWithClientId, user]);

  const retryMessage = useCallback(async (id: number, clientMessageId: string) => {
    const failed = messagesRef.current[id]?.find((item) => item.client_message_id === clientMessageId);
    if (!failed) return;
    await sendWithClientId(id, failed.body, clientMessageId, [], false);
  }, [sendWithClientId]);

  const notifyTyping = useCallback((id: number) => {
    const now = Date.now();
    if (now - (typingLastSent.current.get(id) ?? 0) >= 3_000) {
      sendCommand('typing.started', { conversation_id: id });
      typingLastSent.current.set(id, now);
    }
    const previous = typingStop.current.get(id);
    if (previous) clearTimeout(previous);
    typingStop.current.set(id, setTimeout(() => {
      sendCommand('typing.stopped', { conversation_id: id });
      typingStop.current.delete(id);
    }, 2_000));
  }, [sendCommand]);

  useEffect(() => subscribe((envelope) => {
    if (processedEvents.current.has(envelope.event_id)) return;
    processedEvents.current.add(envelope.event_id);
    if (processedEvents.current.size > 500) {
      const first = processedEvents.current.values().next().value;
      if (first) processedEvents.current.delete(first);
    }
    if (envelope.event === 'realtime.connected' && activeConversation.current) {
      sendCommand('conversation.subscribe', { conversation_id: activeConversation.current });
      return;
    }
    if (envelope.event === 'message.created' && isMessage(envelope.data)) {
      const message = envelope.data as CommunicationMessage;
      setMessagesByConversation((current) => ({
        ...current,
        [message.conversation_id]: reconcileMessages(
          current[message.conversation_id] ?? [], [message],
        ),
      }));
      setConversations((current) => current.map((conversation) => (
        conversation.id === message.conversation_id
          ? {
            ...conversation,
            last_message: message,
            last_message_at: message.created_at,
            latest_sequence: Math.max(conversation.latest_sequence, message.sequence),
            unread_count: message.sender.id !== user?.id && activeConversation.current !== message.conversation_id
              ? conversation.unread_count + 1
              : conversation.unread_count,
          }
          : conversation
      )).sort((left, right) => (right.last_message_at ?? '').localeCompare(left.last_message_at ?? '')));
      const shouldRead = activeConversation.current === message.conversation_id;
      acknowledge(message.conversation_id, [message], shouldRead).catch(() => undefined);
      return;
    }
    if ((envelope.event === 'message.read' || envelope.event === 'message.delivered')
      && typeof envelope.data.user_id === 'number'
      && Array.isArray(envelope.data.message_ids)) {
      const conversationId = Number(envelope.data.conversation_id);
      const messageIds = new Set(envelope.data.message_ids.map(Number));
      const userId = envelope.data.user_id;
      const occurredAt = String(envelope.data.occurred_at ?? envelope.occurred_at);
      setMessagesByConversation((current) => ({
        ...current,
        [conversationId]: (current[conversationId] ?? []).map((message) => {
          if (!messageIds.has(message.id)) return message;
          const receipts = message.receipts.map((receipt) => receipt.user_id === userId
            ? {
              ...receipt,
              delivered_at: receipt.delivered_at ?? occurredAt,
              read_at: envelope.event === 'message.read' ? receipt.read_at ?? occurredAt : receipt.read_at,
            }
            : receipt);
          return { ...message, receipts };
        }),
      }));
      return;
    }
    if ((envelope.event === 'typing.started' || envelope.event === 'typing.stopped')
      && typeof envelope.data.conversation_id === 'number'
      && typeof envelope.data.user_id === 'number'
      && envelope.data.user_id !== user?.id) {
      const conversationId = envelope.data.conversation_id;
      const typingUser = {
        user_id: envelope.data.user_id,
        full_name: String(envelope.data.full_name ?? 'Alguien'),
      };
      const expiryKey = `${conversationId}:${typingUser.user_id}`;
      const remove = () => setTypingByConversation((current) => ({
        ...current,
        [conversationId]: (current[conversationId] ?? []).filter(
          (item) => item.user_id !== typingUser.user_id,
        ),
      }));
      const prior = typingExpiry.current.get(expiryKey);
      if (prior) clearTimeout(prior);
      if (envelope.event === 'typing.stopped') {
        remove();
        typingExpiry.current.delete(expiryKey);
        return;
      }
      setTypingByConversation((current) => ({
        ...current,
        [conversationId]: [
          ...(current[conversationId] ?? []).filter((item) => item.user_id !== typingUser.user_id),
          typingUser,
        ],
      }));
      typingExpiry.current.set(expiryKey, setTimeout(remove, 5_000));
    }
  }), [acknowledge, sendCommand, subscribe, user?.id]);

  useEffect(() => registerResynchronizer(async () => {
    await refreshConversations();
    const loaded = Object.entries(messagesRef.current);
    await Promise.all(loaded.map(async ([rawId, messages]) => {
      const id = Number(rawId);
      let cursor = messages.reduce((maximum, message) => Math.max(maximum, message.sequence), 0);
      const recoveredMessages: CommunicationMessage[] = [];
      for (;;) {
        const recovered = await syncConversation(authorizedFetch, id, cursor);
        recoveredMessages.push(...recovered.items);
        if (!recovered.has_more || !recovered.items.length) break;
        cursor = recovered.items.reduce(
          (maximum, message) => Math.max(maximum, message.sequence), cursor,
        );
      }
      setMessagesByConversation((current) => ({
        ...current, [id]: reconcileMessages(current[id] ?? [], recoveredMessages),
      }));
    }));
  }), [authorizedFetch, refreshConversations, registerResynchronizer]);

  useEffect(() => {
    if (user) refreshConversations().catch(() => undefined);
    else {
      setConversations([]);
      setMessagesByConversation({});
      activeConversation.current = null;
    }
  }, [refreshConversations, user]);

  useEffect(() => () => {
    typingExpiry.current.forEach(clearTimeout);
    typingStop.current.forEach(clearTimeout);
  }, []);

  const unreadCount = conversations.reduce((total, item) => total + item.unread_count, 0);
  const value = useMemo<CommunicationsValue>(() => ({
    conversations,
    messagesByConversation,
    beforeCursorByConversation,
    typingByConversation,
    isLoading,
    error,
    unreadCount,
    refreshConversations,
    openConversation,
    closeConversation,
    loadOlder,
    sendMessage,
    retryMessage,
    notifyTyping,
  }), [
    beforeCursorByConversation, closeConversation, conversations, error, isLoading,
    loadOlder, messagesByConversation, notifyTyping, openConversation,
    refreshConversations, retryMessage, sendMessage, typingByConversation, unreadCount,
  ]);

  return <CommunicationsContext.Provider value={value}>{children}</CommunicationsContext.Provider>;
}

export function useCommunications(): CommunicationsValue {
  const value = useContext(CommunicationsContext);
  if (!value) throw new Error('useCommunications requiere CommunicationsProvider');
  return value;
}
