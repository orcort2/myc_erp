import {
  BellOff,
  CheckCheck,
  RefreshCw,
} from 'lucide-react';
import {
  useMemo,
  useState,
} from 'react';

import NotificationItem from '../components/notifications/NotificationItem.jsx';
import { useNotifications } from '../components/notifications/NotificationProvider.jsx';
import { openNotificationDestination } from '../components/notifications/notificationNavigation.js';

export default function NotificationCenterPage() {
  const [filter, setFilter] = useState('all');
  const {
    error,
    loading,
    markAllRead,
    markRead,
    notifications,
    refresh,
    total,
    unreadCount,
  } = useNotifications();

  const visibleNotifications = useMemo(() => {
    if (filter === 'unread') {
      return notifications.filter(
        (notification) => !notification.read_at,
      );
    }

    return notifications;
  }, [filter, notifications]);

  async function handleOpen(notification) {
    try {
      await markRead(notification.id);
    } finally {
      openNotificationDestination(notification);
    }
  }

  return (
    <section className="notification-center">
      <header className="notification-center__header">
        <div>
          <h1>Centro de notificaciones</h1>
          <p>
            Consulta menciones, asignaciones y eventos relevantes del sistema.
          </p>
        </div>

        <div className="notification-center__actions">
          <button
            disabled={loading}
            onClick={() => refresh()}
            type="button"
          >
            <RefreshCw
              aria-hidden="true"
              className={loading ? 'is-spinning' : ''}
              size={16}
            />
            Actualizar
          </button>

          <button
            disabled={unreadCount === 0}
            onClick={markAllRead}
            type="button"
          >
            <CheckCheck aria-hidden="true" size={16} />
            Marcar todas como leídas
          </button>
        </div>
      </header>

      {error ? (
        <div className="notification-center__error" role="alert">
          {error}
        </div>
      ) : null}

      <div className="notification-center__panel">
        <nav
          aria-label="Filtros de notificaciones"
          className="notification-center__filters"
        >
          <button
            className={filter === 'all' ? 'is-active' : ''}
            onClick={() => setFilter('all')}
            type="button"
          >
            Todas ({total})
          </button>

          <button
            className={filter === 'unread' ? 'is-active' : ''}
            onClick={() => setFilter('unread')}
            type="button"
          >
            No leídas ({unreadCount})
          </button>
        </nav>

        <div className="notification-center__list">
          {visibleNotifications.map((notification) => (
            <NotificationItem
              key={notification.id}
              notification={notification}
              onOpen={handleOpen}
            />
          ))}

          {!loading && visibleNotifications.length === 0 ? (
            <div className="notification-center__empty">
              <BellOff aria-hidden="true" size={30} />
              <strong>
                {filter === 'unread'
                  ? 'No tienes notificaciones pendientes'
                  : 'Todavía no hay notificaciones'}
              </strong>
              <span>
                Los nuevos avisos aparecerán en este centro.
              </span>
            </div>
          ) : null}
        </div>
      </div>
    </section>
  );
}
