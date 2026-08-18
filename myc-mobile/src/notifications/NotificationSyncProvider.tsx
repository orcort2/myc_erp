import * as Notifications from 'expo-notifications';
import { Href, router } from 'expo-router';
import { createContext, PropsWithChildren, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { AppState } from 'react-native';

import { apiUrl } from '@/src/api/client';
import { useAuth } from '@/src/auth/AuthProvider';
import { useRealtime } from '@/src/realtime/RealtimeProvider';
import { registerCurrentDevice } from '@/src/services/push-notifications';
import type { NotificationSyncEvent } from '@/src/types/notification';
import { NotificationEventDeduper } from '@/src/notifications/refresh-policy';

type Listener = (event: NotificationSyncEvent) => void;
type NotificationSyncValue = {
  unreadCount: number;
  refreshUnread(): Promise<void>;
  publishLocalChange(event: Omit<NotificationSyncEvent, 'source'>): void;
  subscribe(listener: Listener): () => void;
};

const NotificationSyncContext = createContext<NotificationSyncValue | null>(null);

Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldPlaySound: false,
    shouldSetBadge: true,
    shouldShowBanner: true,
    shouldShowList: true,
  }),
});

function numberValue(value: unknown): number | undefined {
  return typeof value === 'number' ? value : typeof value === 'string' ? Number(value) : undefined;
}

function eventFromData(data: Record<string, unknown>, source: NotificationSyncEvent['source'], key?: string): NotificationSyncEvent {
  return {
    event_type: typeof data.event_type === 'string' ? data.event_type : 'notification.received',
    entity_type: typeof data.entity_type === 'string' ? data.entity_type : null,
    entity_id: numberValue(data.entity_id),
    ticket_id: numberValue(data.ticket_id),
    work_order_id: numberValue(data.work_order_id),
    conversation_id: numberValue(data.conversation_id),
    source,
    dedupe_key: key,
  };
}

function targetFor(event: NotificationSyncEvent): Href | null {
  if (event.conversation_id || event.entity_type === 'communication') {
    const id = event.conversation_id ?? event.entity_id;
    return id
      ? { pathname: '/(technician)/communications/[id]', params: { id: String(id) } }
      : '/(technician)/communications';
  }
  if (event.ticket_id || event.entity_type === 'ticket') {
    const id = event.ticket_id ?? event.entity_id;
    return { pathname: '/(technician)/tickets', params: id ? { ticketId: String(id) } : {} };
  }
  if (event.work_order_id) {
    return { pathname: '/(technician)/work-orders', params: { workOrderId: String(event.work_order_id) } };
  }
  return null;
}

export function NotificationSyncProvider({ children }: PropsWithChildren) {
  const { authorizedFetch, user } = useAuth();
  const [unreadCount, setUnreadCount] = useState(0);
  const { subscribe: subscribeRealtime } = useRealtime();
  const listeners = useRef(new Set<Listener>());
  const processed = useRef(new NotificationEventDeduper());
  const pendingTarget = useRef<Href | null>(null);

  const subscribe = useCallback((listener: Listener) => {
    listeners.current.add(listener);
    return () => listeners.current.delete(listener);
  }, []);

  const emit = useCallback((event: NotificationSyncEvent) => {
    if (!processed.current.accept(event.dedupe_key)) return false;
    listeners.current.forEach((listener) => listener(event));
    return true;
  }, []);

  const refreshUnread = useCallback(async () => {
    if (!user) return;
    const response = await authorizedFetch(apiUrl('/notifications/unread-count'));
    if (!response.ok) return;
    const payload = await response.json() as { count: number };
    setUnreadCount(payload.count);
    await Notifications.setBadgeCountAsync(payload.count).catch(() => undefined);
  }, [authorizedFetch, user]);

  const handleResponse = useCallback((response: Notifications.NotificationResponse) => {
    const data = response.notification.request.content.data as Record<string, unknown>;
    const event = eventFromData(data, 'push', response.notification.request.identifier);
    if (!emit(event)) return;
    const target = targetFor(event);
    if (!target) return;
    if (user) router.push(target);
    else pendingTarget.current = target;
  }, [emit, user]);

  useEffect(() => {
    if (!user) {
      setUnreadCount(0);
      return;
    }
    registerCurrentDevice(authorizedFetch).catch(() => undefined);
    refreshUnread().catch(() => undefined);
    if (pendingTarget.current) {
      router.push(pendingTarget.current);
      pendingTarget.current = null;
    }
  }, [authorizedFetch, refreshUnread, user]);

  useEffect(() => {
    const received = Notifications.addNotificationReceivedListener((notification) => {
      const data = notification.request.content.data as Record<string, unknown>;
      emit(eventFromData(data, 'push', notification.request.identifier));
      refreshUnread().catch(() => undefined);
    });
    const responded = Notifications.addNotificationResponseReceivedListener(handleResponse);
    Notifications.getLastNotificationResponseAsync().then((response) => {
      if (response) handleResponse(response);
    }).catch(() => undefined);
    const appState = AppState.addEventListener('change', (state) => {
      if (state !== 'active' || !user) return;
      emit({ event_type: 'app.foreground', source: 'foreground' });
      refreshUnread().catch(() => undefined);
    });
    return () => {
      received.remove();
      responded.remove();
      appState.remove();
    };
  }, [emit, handleResponse, refreshUnread, user]);

  useEffect(() => subscribeRealtime((envelope) => {
    if (envelope.event !== 'notification.created') return;
    emit(eventFromData(envelope.data, 'realtime', envelope.event_id));
    refreshUnread().catch(() => undefined);
  }), [emit, refreshUnread, subscribeRealtime]);

  const value = useMemo<NotificationSyncValue>(() => ({
    unreadCount,
    refreshUnread,
    subscribe,
    publishLocalChange(event) {
      emit({ ...event, source: 'local' });
      refreshUnread().catch(() => undefined);
    },
  }), [emit, refreshUnread, subscribe, unreadCount]);

  return <NotificationSyncContext.Provider value={value}>{children}</NotificationSyncContext.Provider>;
}

export function useNotificationSync(): NotificationSyncValue {
  const value = useContext(NotificationSyncContext);
  if (!value) throw new Error('useNotificationSync requiere NotificationSyncProvider');
  return value;
}
