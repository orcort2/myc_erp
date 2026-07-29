import { navigate } from '../../utils/routing.js';
import { ACTIVITY_ENTITY_DESTINATIONS } from '../activity/activityEntities.js';

const ENTITY_DESTINATIONS = {
  ...ACTIVITY_ENTITY_DESTINATIONS,
  quote: '/dashboard#cotizaciones',
  service: '/dashboard#servicios',
  ets: '/dashboard#servicios',
};

export function getNotificationDestination(notification) {
  const metadata = notification?.metadata_json ?? {};

  if (typeof metadata.frontend_path === 'string') {
    return metadata.frontend_path;
  }

  if (typeof metadata.path === 'string') {
    return metadata.path;
  }

  const basePath = ENTITY_DESTINATIONS[notification?.entity_type];

  if (!basePath) {
    return '/communications';
  }

  const query = new URLSearchParams();

  if (notification.entity_id != null) {
    query.set('entity_id', String(notification.entity_id));
  }

  if (notification.activity_message_id != null) {
    query.set(
      'activity_message_id',
      String(notification.activity_message_id),
    );
    query.set('open_activity', '1');
  }

  if (query.size === 0) {
    return basePath;
  }

  const [pathname, hash = ''] = basePath.split('#');
  return `${pathname}?${query.toString()}${hash ? `#${hash}` : ''}`;
}

export function openNotificationDestination(notification) {
  navigate(getNotificationDestination(notification));
}
