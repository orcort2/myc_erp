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
    || event.event_type.startsWith('ticket.');
}

export function affectsWorkOrders(event: NotificationSyncEvent): boolean {
  return event.event_type === 'app.foreground'
    || event.event_type.startsWith('ticket.')
    || event.event_type.startsWith('work_order.')
    || event.work_order_id !== undefined;
}
