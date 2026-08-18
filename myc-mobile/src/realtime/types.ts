export type RealtimeState = 'connected' | 'disconnected' | 'reconnecting' | 'resynchronizing';

export type RealtimeEnvelope<T extends Record<string, unknown> = Record<string, unknown>> = {
  version: 1;
  event: string;
  event_id: string;
  occurred_at: string;
  data: T;
};

export type RealtimeListener = (envelope: RealtimeEnvelope) => void;
export type RealtimeResynchronizer = () => void | Promise<void>;
