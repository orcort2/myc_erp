import {
  AtSign,
  Bell,
  CircleAlert,
  MessageSquare,
} from 'lucide-react';

function formatRelativeDate(value) {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return '';
  }

  const difference = date.getTime() - Date.now();
  const absoluteDifference = Math.abs(difference);

  if (absoluteDifference < 60000) {
    return 'Ahora';
  }

  const formatter = new Intl.RelativeTimeFormat('es-MX', {
    numeric: 'auto',
  });

  if (absoluteDifference < 3600000) {
    return formatter.format(
      Math.round(difference / 60000),
      'minute',
    );
  }

  if (absoluteDifference < 86400000) {
    return formatter.format(
      Math.round(difference / 3600000),
      'hour',
    );
  }

  if (absoluteDifference < 604800000) {
    return formatter.format(
      Math.round(difference / 86400000),
      'day',
    );
  }

  return new Intl.DateTimeFormat('es-MX', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  }).format(date);
}

function NotificationIcon({ notification }) {
  const type = notification.notification_type ?? '';

  if (type.includes('mention')) {
    return <AtSign aria-hidden="true" size={18} />;
  }

  if (type.includes('message')) {
    return <MessageSquare aria-hidden="true" size={18} />;
  }

  if (notification.priority === 'high') {
    return <CircleAlert aria-hidden="true" size={18} />;
  }

  return <Bell aria-hidden="true" size={18} />;
}

export default function NotificationItem({
  notification,
  onOpen,
  compact = false,
}) {
  const unread = !notification.read_at;
  const actorName = notification.actor_user?.full_name;

  return (
    <button
      className={[
        'notification-item',
        unread ? 'is-unread' : '',
        compact ? 'is-compact' : '',
      ].filter(Boolean).join(' ')}
      onClick={() => onOpen(notification)}
      type="button"
    >
      <span className="notification-item__icon">
        <NotificationIcon notification={notification} />
      </span>

      <span className="notification-item__content">
        <span className="notification-item__heading">
          <strong>{notification.title}</strong>
          {unread ? (
            <span
              aria-label="No leída"
              className="notification-item__unread-dot"
            />
          ) : null}
        </span>

        {notification.body ? (
          <span className="notification-item__body">
            {notification.body}
          </span>
        ) : null}

        <span className="notification-item__meta">
          {actorName ? <span>{actorName}</span> : null}
          <time dateTime={notification.created_at}>
            {formatRelativeDate(notification.created_at)}
          </time>
        </span>
      </span>
    </button>
  );
}
