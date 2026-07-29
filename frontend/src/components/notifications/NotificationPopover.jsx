import {
  BellOff,
  CheckCheck,
  LoaderCircle,
} from 'lucide-react';

import { navigate } from '../../utils/routing.js';
import NotificationItem from './NotificationItem.jsx';

export default function NotificationPopover({
  error,
  loading,
  notifications,
  onClose,
  onMarkAllRead,
  onOpenNotification,
  unreadCount,
}) {
  const recentNotifications = notifications.slice(0, 8);

  function openCenter() {
    onClose();
    navigate('/notifications');
  }

  return (
    <section
      aria-label="Notificaciones recientes"
      className="notification-popover"
    >
      <header className="notification-popover__header">
        <div>
          <strong>Notificaciones</strong>
          <span>
            {unreadCount > 0
              ? `${unreadCount} sin leer`
              : 'Todo al día'}
          </span>
        </div>

        <button
          className="notification-popover__mark-all"
          disabled={unreadCount === 0}
          onClick={onMarkAllRead}
          type="button"
        >
          <CheckCheck aria-hidden="true" size={16} />
          Marcar todas
        </button>
      </header>

      <div className="notification-popover__list">
        {loading && recentNotifications.length === 0 ? (
          <div className="notification-popover__state">
            <LoaderCircle
              aria-hidden="true"
              className="is-spinning"
              size={22}
            />
            <span>Cargando notificaciones...</span>
          </div>
        ) : null}

        {!loading && error && recentNotifications.length === 0 ? (
          <div className="notification-popover__state is-error">
            <span>{error}</span>
          </div>
        ) : null}

        {!loading && !error && recentNotifications.length === 0 ? (
          <div className="notification-popover__state">
            <BellOff aria-hidden="true" size={24} />
            <strong>No hay notificaciones</strong>
            <span>Los avisos nuevos aparecerán aquí.</span>
          </div>
        ) : null}

        {recentNotifications.map((notification) => (
          <NotificationItem
            compact
            key={notification.id}
            notification={notification}
            onOpen={onOpenNotification}
          />
        ))}
      </div>

      <footer className="notification-popover__footer">
        <button onClick={openCenter} type="button">
          Ver todas las notificaciones
        </button>
      </footer>
    </section>
  );
}
