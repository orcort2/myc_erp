import { reconnectDelayMs, shouldRetryClose } from '@/src/realtime/reconnection-policy';
import type { RealtimeEnvelope, RealtimeState } from '@/src/realtime/types';

export const REALTIME_PROTOCOL = 'myc.realtime.v1';

type Timer = ReturnType<typeof setTimeout>;

export type RealtimeSocket = Pick<WebSocket, 'onopen' | 'onmessage' | 'onclose' | 'onerror' | 'close' | 'send'>;

type RealtimeClientOptions = {
  url: string;
  getAccessToken(): string | null;
  refreshAccessToken(): Promise<string | null>;
  createSocket(url: string, protocols: string[]): RealtimeSocket;
  onState(state: RealtimeState): void;
  onEnvelope(envelope: RealtimeEnvelope): void;
  resynchronize(): Promise<void>;
  schedule?: (callback: () => void, delay: number) => Timer;
  cancelSchedule?: (timer: Timer) => void;
  delayForAttempt?: (attempt: number) => number;
};

function isEnvelope(value: unknown): value is RealtimeEnvelope {
  if (!value || typeof value !== 'object') return false;
  const candidate = value as Partial<RealtimeEnvelope>;
  return candidate.version === 1
    && typeof candidate.event === 'string'
    && typeof candidate.event_id === 'string'
    && typeof candidate.occurred_at === 'string'
    && !!candidate.data
    && typeof candidate.data === 'object';
}

export class RealtimeClient {
  private socket: RealtimeSocket | null = null;
  private retryTimer: Timer | null = null;
  private attempt = 0;
  private active = false;
  private stopped = true;
  private hasConnected = false;
  private refreshedForAuthFailure = false;
  private generation = 0;

  constructor(private readonly options: RealtimeClientOptions) {}

  start(): void {
    if (!this.stopped) return;
    this.stopped = false;
    this.active = true;
    this.connect(false);
  }

  stop(): void {
    this.stopped = true;
    this.active = false;
    this.generation += 1;
    this.clearRetry();
    const socket = this.socket;
    this.socket = null;
    socket?.close(1000, 'session_closed');
    this.options.onState('disconnected');
  }

  background(): void {
    if (this.stopped) return;
    this.active = false;
    this.generation += 1;
    this.clearRetry();
    const socket = this.socket;
    this.socket = null;
    socket?.close(1000, 'app_background');
    this.options.onState('disconnected');
  }

  foreground(): void {
    if (this.stopped || this.active) return;
    this.active = true;
    this.options.onState('reconnecting');
    this.connect(true);
  }

  sendCommand(event: string, data: Record<string, unknown> = {}): boolean {
    if (!this.socket || this.stopped || !this.active) return false;
    try {
      this.socket.send(JSON.stringify({ event, data }));
      return true;
    } catch {
      return false;
    }
  }

  private connect(recovery: boolean): void {
    if (this.stopped || !this.active || this.socket) return;
    const token = this.options.getAccessToken();
    if (!token) {
      this.options.onState('disconnected');
      return;
    }
    const generation = ++this.generation;
    let socket: RealtimeSocket;
    try {
      socket = this.options.createSocket(
        this.options.url,
        [REALTIME_PROTOCOL, `auth.${token}`],
      );
    } catch {
      this.scheduleReconnect();
      return;
    }
    this.socket = socket;
    socket.onmessage = (event) => {
      if (generation !== this.generation) return;
      let parsed: unknown;
      try { parsed = JSON.parse(event.data); } catch { return; }
      if (!isEnvelope(parsed)) return;
      this.options.onEnvelope(parsed);
      if (parsed.event !== 'realtime.connected') return;
      const mustResynchronize = recovery || this.hasConnected;
      this.hasConnected = true;
      this.attempt = 0;
      this.refreshedForAuthFailure = false;
      if (!mustResynchronize) {
        this.options.onState('connected');
        return;
      }
      this.options.onState('resynchronizing');
      void this.options.resynchronize().finally(() => {
        if (generation === this.generation && this.active && !this.stopped) {
          this.options.onState('connected');
        }
      });
    };
    socket.onclose = (event) => {
      if (generation !== this.generation) return;
      this.socket = null;
      if (this.stopped || !this.active) {
        this.options.onState('disconnected');
        return;
      }
      if (event.code === 4401) {
        void this.recoverAuthentication();
        return;
      }
      if (!shouldRetryClose(event.code)) {
        this.options.onState('disconnected');
        return;
      }
      this.scheduleReconnect();
    };
    socket.onerror = () => {
      // El evento close es la autoridad para decidir reconexión.
    };
  }

  private async recoverAuthentication(): Promise<void> {
    if (this.refreshedForAuthFailure) {
      this.options.onState('disconnected');
      return;
    }
    this.refreshedForAuthFailure = true;
    this.options.onState('reconnecting');
    try {
      const token = await this.options.refreshAccessToken();
      if (!token || this.stopped || !this.active) {
        this.options.onState('disconnected');
        return;
      }
      this.connect(true);
    } catch {
      this.options.onState('disconnected');
    }
  }

  private scheduleReconnect(): void {
    if (this.stopped || !this.active || this.retryTimer) return;
    this.options.onState('reconnecting');
    const delay = (this.options.delayForAttempt ?? reconnectDelayMs)(this.attempt++);
    const schedule = this.options.schedule ?? setTimeout;
    this.retryTimer = schedule(() => {
      this.retryTimer = null;
      this.connect(true);
    }, delay);
  }

  private clearRetry(): void {
    if (!this.retryTimer) return;
    const cancel = this.options.cancelSchedule ?? clearTimeout;
    cancel(this.retryTimer);
    this.retryTimer = null;
  }
}
