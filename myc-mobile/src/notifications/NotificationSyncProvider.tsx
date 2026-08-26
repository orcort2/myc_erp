import * as Notifications from 'expo-notifications';
import { Href, router } from 'expo-router';
import { createContext, PropsWithChildren, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { AppState } from 'react-native';

import { apiUrl } from '@/src/api/client';
import { useAuth } from '@/src/auth/AuthProvider';
import { useRealtime } from '@/src/realtime/RealtimeProvider';
import { registerCurrentDevice } from '@/src/services/push-notifications';
import type { NotificationSyncEvent } from '@/src/types/notification';
import { eventFromData, NotificationEventDeduper, targetFor } from '@/src/notifications/refresh-policy';

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

export function NotificationSyncProvider({ children }: PropsWithChildren) {
  const { authorizedFetch, user } = useAuth();
  const [unreadCount, setUnreadCount] = useState(0);
  const { subscribe: subscribeRealtime } = useRealtime();
  const listeners = useRef(new Set<Listener>());
  const processed = useRef(new NotificationEventDeduper());
  const pendingTarget = useRef<Href | null>(null);

  // Latest `user` for callbacks that must stay referentially stable (see
  // handleResponse below) without reintroducing `user` into their deps.
  const userRef = useRef(user);
  useEffect(() => { userRef.current = user; }, [user]);

  // Same pattern for `authorizedFetch`, read by the foreground push-device
  // revalidation below (MOB-004) so that effect can also stay registered
  // exactly once instead of re-subscribing on every session refresh.
  const authorizedFetchRef = useRef(authorizedFetch);
  useEffect(() => { authorizedFetchRef.current = authorizedFetch; }, [authorizedFetch]);

  const registerDevice = useCallback((trigger: 'login' | 'foreground') => {
    registerCurrentDevice(authorizedFetchRef.current, trigger)
      .then((result) => {
        if (!result.ok) {
          console.warn(`[push-notifications] registro de dispositivo incompleto (trigger=${trigger})`, result.reason);
        }
      })
      .catch((error) => console.warn(`[push-notifications] registro de dispositivo falló inesperadamente (trigger=${trigger})`, error));
  }, []);

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
    if (!userRef.current) return;
    const response = await authorizedFetch(apiUrl('/mobile/v1/notifications/unread-count'));
    if (!response.ok) return;
    const payload = await response.json() as { count: number };
    setUnreadCount(payload.count);
    await Notifications.setBadgeCountAsync(payload.count).catch(() => undefined);
  }, [authorizedFetch]);

  // Latest `refreshUnread` for the OS-listener effect below, which must not
  // depend on it directly (see that effect's comment).
  const refreshUnreadRef = useRef(refreshUnread);
  useEffect(() => { refreshUnreadRef.current = refreshUnread; }, [refreshUnread]);

  // Stable on purpose (deps: [emit] only). `emit` dedupes by
  // event.dedupe_key (the notification's request.identifier), so processing
  // the same response twice — e.g. because
  // Notifications.getLastNotificationResponseAsync() keeps returning the
  // same cached response — only navigates once. Reading `user` through a
  // ref (instead of closing over it) keeps this callback's identity stable
  // across unrelated re-renders (e.g. a silent token refresh producing a
  // new `user` object), which is what lets the listener-registration effect
  // below run only once per app session instead of re-subscribing (and
  // re-querying getLastNotificationResponseAsync) on every such re-render.
  const handleResponse = useCallback((response: Notifications.NotificationResponse) => {
    const data = response.notification.request.content.data as Record<string, unknown>;
    const event = eventFromData(data, 'push', response.notification.request.identifier);
    if (!emit(event)) return;
    const target = targetFor(event);
    if (!target) return;
    if (userRef.current) router.push(target);
    else pendingTarget.current = target;
  }, [emit]);

  useEffect(() => {
    if (!user) {
      setUnreadCount(0);
      return;
    }
    registerDevice('login');
    refreshUnread().catch(() => undefined);
    if (pendingTarget.current) {
      router.push(pendingTarget.current);
      pendingTarget.current = null;
    }
  }, [authorizedFetch, refreshUnread, registerDevice, user]);

  // MOB-003: registered exactly once (deps: [emit, handleResponse], both
  // stable). Notifications.getLastNotificationResponseAsync() keeps
  // returning the *same* cached response until the app relaunches, so
  // re-subscribing here on every unrelated re-render used to re-process
  // that stale response and push the same navigation target again right
  // after the user had already closed/backed out of it — the "cierra pero
  // rebota" symptom. handleResponse/emit/refreshUnreadRef read the latest
  // user/refreshUnread via refs, so nothing here goes stale by only running
  // once.
  useEffect(() => {
    const received = Notifications.addNotificationReceivedListener((notification) => {
      const data = notification.request.content.data as Record<string, unknown>;
      emit(eventFromData(data, 'push', notification.request.identifier));
      refreshUnreadRef.current().catch(() => undefined);
    });
    const responded = Notifications.addNotificationResponseReceivedListener(handleResponse);
    Notifications.getLastNotificationResponseAsync().then((response) => {
      if (response) handleResponse(response);
    }).catch(() => undefined);
    const appState = AppState.addEventListener('change', (state) => {
      if (state !== 'active' || !userRef.current) return;
      emit({ event_type: 'app.foreground', source: 'foreground' });
      refreshUnreadRef.current().catch(() => undefined);
      // MOB-004: revalidates the push-device registration on every
      // foreground so a token that changed (or a registration that failed
      // silently before) self-heals without waiting for the next login.
      // registerCurrentDevice's own throttle (see push-notification-policy)
      // keeps this from hitting the backend on every app switch.
      registerDevice('foreground');
    });
    return () => {
      received.remove();
      responded.remove();
      appState.remove();
    };
  }, [emit, handleResponse, registerDevice]);

  useEffect(() => subscribeRealtime((envelope) => {
    if (envelope.event !== 'notification.created') return;
    emit(eventFromData(envelope.data, 'realtime', envelope.event_id));
    refreshUnreadRef.current().catch(() => undefined);
  }), [emit, subscribeRealtime]);

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
