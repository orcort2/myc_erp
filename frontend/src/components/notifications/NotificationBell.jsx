import {
  Bell,
} from 'lucide-react';
import {
  useEffect,
  useRef,
  useState,
} from 'react';

import { useNotifications } from './NotificationProvider.jsx';
import NotificationPopover from './NotificationPopover.jsx';
import { openNotificationDestination } from './notificationNavigation.js';

export default function NotificationBell() {
  const [open, setOpen] = useState(false);
  const rootRef = useRef(null);
  const {
    error,
    loading,
    markAllRead,
    markRead,
    notifications,
    refresh,
    unreadCount,
  } = useNotifications();

  useEffect(() => {
    if (!open) {
      return undefined;
    }

    function handlePointerDown(event) {
      if (!rootRef.current?.contains(event.target)) {
        setOpen(false);
      }
    }

    function handleKeyDown(event) {
      if (event.key === 'Escape') {
        setOpen(false);
      }
    }

    document.addEventListener('pointerdown', handlePointerDown);
    window.addEventListener('keydown', handleKeyDown);

    return () => {
      document.removeEventListener('pointerdown', handlePointerDown);
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [open]);

  async function togglePopover() {
    const nextOpen = !open;
    setOpen(nextOpen);

    if (nextOpen) {
      await refresh({ silent: true });
    }
  }

  async function handleOpenNotification(notification) {
    try {
      await markRead(notification.id);
    } finally {
      setOpen(false);
      openNotificationDestination(notification);
    }
  }

  return (
    <div className="notification-bell" ref={rootRef}>
      <button
        aria-expanded={open}
        aria-haspopup="dialog"
        aria-label={
          unreadCount > 0
            ? `Notificaciones, ${unreadCount} sin leer`
            : 'Notificaciones'
        }
        className={[
          'notification-bell__button',
          open ? 'is-open' : '',
        ].filter(Boolean).join(' ')}
        onClick={togglePopover}
        type="button"
      >
        <Bell aria-hidden="true" size={20} />

        {unreadCount > 0 ? (
          <span className="notification-bell__badge">
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        ) : null}
      </button>

      {open ? (
        <NotificationPopover
          error={error}
          loading={loading}
          notifications={notifications}
          onClose={() => setOpen(false)}
          onMarkAllRead={markAllRead}
          onOpenNotification={handleOpenNotification}
          unreadCount={unreadCount}
        />
      ) : null}
    </div>
  );
}
