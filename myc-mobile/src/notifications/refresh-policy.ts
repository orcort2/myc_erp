import type { Href } from 'expo-router';

import type { NotificationSyncEvent } from '@/src/types/notification';

export class NotificationEventDeduper {
  private readonly keys = new Set<string>();

  accept(key?: string): boolean {
    if (!key) return true;
    if (this.keys.has(key)) return false;
    this.keys.add(key);
    if (this.keys.size > 100) this.keys.clear();
    return true;
  }
}

export class RefreshGate {
  private lastRefreshAt = 0;

  shouldRefresh(now: number, force = false): boolean {
    if (!force && now - this.lastRefreshAt < 1000) return false;
    this.lastRefreshAt = now;
    return true;
  }
}

export function affectsTickets(event: NotificationSyncEvent): boolean {
  return event.event_type === 'app.foreground'
    || event.entity_type === 'ticket'
    || event.entity_type === 'work_order_group_request'
    || event.event_type.startsWith('ticket.')
    || event.event_type.startsWith('lab_work_order_group.');
}

export function affectsWorkOrders(event: NotificationSyncEvent): boolean {
  return event.event_type === 'app.foreground'
    || event.event_type.startsWith('ticket.')
    || event.event_type.startsWith('work_order.')
    || event.entity_type === 'work_order_group_request'
    || event.work_order_id !== undefined;
}

function numberValue(value: unknown): number | undefined {
  return typeof value === 'number' ? value : typeof value === 'string' ? Number(value) : undefined;
}

export function eventFromData(
  data: Record<string, unknown>,
  source: NotificationSyncEvent['source'],
  key?: string,
): NotificationSyncEvent {
  return {
    event_type: typeof data.event_type === 'string' ? data.event_type : 'notification.received',
    entity_type: typeof data.entity_type === 'string' ? data.entity_type : null,
    entity_id: numberValue(data.entity_id),
    ticket_id: numberValue(data.ticket_id),
    work_order_id: numberValue(data.work_order_id),
    conversation_id: numberValue(data.conversation_id),
    request_id: numberValue(data.request_id),
    source,
    dedupe_key: key,
  };
}

export function targetFor(event: NotificationSyncEvent): Href | null {
  if (event.request_id || event.entity_type === 'work_order_group_request') {
    const id = event.request_id ?? event.entity_id;
    if (event.event_type === 'lab_work_order_group.requested') {
      return { pathname: '/(technician)/tickets', params: id ? { groupRequestId: String(id), requestKind: 'groups' } : { requestKind: 'groups' } };
    }
    return { pathname: '/(technician)/work-orders', params: id ? { groupRequestId: String(id) } : {} };
  }
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
  if (event.work_order_id || ['work_order', 'lab_work_order'].includes(event.entity_type ?? '')) {
    const id = event.work_order_id ?? event.entity_id;
    return { pathname: '/(technician)/work-orders', params: id ? { workOrderId: String(id) } : {} };
  }
  return null;
}

export async function markReadThenNavigate(
  markRead: () => Promise<unknown>,
  navigate: () => void,
): Promise<void> {
  try {
    await markRead();
  } finally {
    navigate();
  }
}

export type NotificationResponseLike = {
  notification: {
    request: {
      identifier: string;
      content: { data: Record<string, unknown> };
    };
  };
};

export type ResponseResolution =
  | { accepted: false }
  | { accepted: true; target: Href | null };

/**
 * Pure decision mirroring NotificationSyncProvider's handleResponse: given a
 * notification response and a deduper, decides whether the response should
 * be processed and, if so, what navigation target (if any) it resolves to.
 *
 * Processing the exact same response object twice (same
 * request.identifier, e.g. because Notifications.getLastNotificationResponseAsync()
 * keeps returning the same cached response across re-subscriptions) must be
 * accepted only once — the second call must report accepted: false so the
 * caller does not navigate again. This is the guarantee MOB-003 depends on.
 */
export function resolveNotificationResponse(
  response: NotificationResponseLike,
  deduper: NotificationEventDeduper,
): ResponseResolution {
  const data = response.notification.request.content.data ?? {};
  const event = eventFromData(data, 'push', response.notification.request.identifier);
  if (!deduper.accept(event.dedupe_key)) return { accepted: false };
  return { accepted: true, target: targetFor(event) };
}
