import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';

import {
  getNotificationUnreadCount,
  listNotifications,
  markAllNotificationsRead,
  markNotificationRead,
} from '../../services/api.js';

const NotificationContext = createContext(null);
const POLLING_INTERVAL_MS = 30000;

export function NotificationProvider({ children, enabled = true }) {
  const [notifications, setNotifications] = useState([]);
  const [total, setTotal] = useState(0);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const mountedRef = useRef(true);
  const loadingRef = useRef(false);

  const refresh = useCallback(async ({ silent = false } = {}) => {
    if (!enabled || loadingRef.current) {
      return;
    }

    loadingRef.current = true;

    if (!silent) {
      setLoading(true);
    }

    try {
      const [listResponse, countResponse] = await Promise.all([
        listNotifications({ limit: 50 }),
        getNotificationUnreadCount(),
      ]);

      if (!mountedRef.current) {
        return;
      }

      setNotifications(listResponse?.items ?? []);
      setTotal(Number(listResponse?.total ?? 0));
      setUnreadCount(Number(countResponse?.count ?? 0));
      setError('');
    } catch (requestError) {
      if (mountedRef.current && !silent) {
        setError(
          requestError?.message
            || 'No fue posible cargar las notificaciones.',
        );
      }
    } finally {
      loadingRef.current = false;

      if (mountedRef.current && !silent) {
        setLoading(false);
      }
    }
  }, [enabled]);

  const markRead = useCallback(async (notificationId) => {
    const current = notifications.find(
      (notification) => notification.id === notificationId,
    );

    if (!current || current.read_at) {
      return current ?? null;
    }

    const updatedNotification = await markNotificationRead(
      notificationId,
    );

    if (!mountedRef.current) {
      return updatedNotification;
    }

    setNotifications((items) =>
      items.map((notification) =>
        notification.id === notificationId
          ? updatedNotification
          : notification,
      ),
    );

    setUnreadCount((count) => Math.max(0, count - 1));

    return updatedNotification;
  }, [notifications]);

  const markAllRead = useCallback(async () => {
    if (unreadCount === 0) {
      return;
    }

    await markAllNotificationsRead();

    if (!mountedRef.current) {
      return;
    }

    const readAt = new Date().toISOString();

    setNotifications((items) =>
      items.map((notification) => ({
        ...notification,
        read_at: notification.read_at ?? readAt,
      })),
    );
    setUnreadCount(0);
  }, [unreadCount]);

  useEffect(() => {
    mountedRef.current = true;

    if (!enabled) {
      setNotifications([]);
      setTotal(0);
      setUnreadCount(0);
      setError('');
      return () => {
        mountedRef.current = false;
      };
    }

    void refresh();

    const intervalId = window.setInterval(() => {
      if (document.visibilityState === 'visible') {
        void refresh({ silent: true });
      }
    }, POLLING_INTERVAL_MS);

    function handleVisibilityChange() {
      if (document.visibilityState === 'visible') {
        void refresh({ silent: true });
      }
    }

    document.addEventListener(
      'visibilitychange',
      handleVisibilityChange,
    );

    return () => {
      mountedRef.current = false;
      window.clearInterval(intervalId);
      document.removeEventListener(
        'visibilitychange',
        handleVisibilityChange,
      );
    };
  }, [enabled, refresh]);

  const value = useMemo(() => ({
    notifications,
    total,
    unreadCount,
    loading,
    error,
    refresh,
    markRead,
    markAllRead,
  }), [
    notifications,
    total,
    unreadCount,
    loading,
    error,
    refresh,
    markRead,
    markAllRead,
  ]);

  return (
    <NotificationContext.Provider value={value}>
      {children}
    </NotificationContext.Provider>
  );
}

export function useNotifications() {
  const context = useContext(NotificationContext);

  if (!context) {
    throw new Error(
      'useNotifications debe usarse dentro de NotificationProvider.',
    );
  }

  return context;
}
