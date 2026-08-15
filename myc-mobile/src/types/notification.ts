export type MobileNotification = {
  id: number;
  notification_type: string;
  event_key: string | null;
  title: string;
  body: string | null;
  priority: string;
  entity_type: string | null;
  entity_id: number | null;
  metadata_json: Record<string, unknown>;
  read_at: string | null;
  created_at: string;
};

export type NotificationPage = {
  items: MobileNotification[];
  total: number;
};

export type NotificationSyncEvent = {
  event_type: string;
  entity_type?: string | null;
  entity_id?: number | null;
  ticket_id?: number;
  work_order_id?: number;
  source: 'push' | 'foreground' | 'local';
  dedupe_key?: string;
};
