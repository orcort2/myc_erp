import assert from 'node:assert/strict';
import test from 'node:test';

import { RealtimeClient, type RealtimeSocket } from './realtime-client';
import { reconnectDelayMs, shouldRetryClose } from './reconnection-policy';
import type { RealtimeEnvelope, RealtimeState } from './types';

class FakeSocket implements RealtimeSocket {
  onopen: WebSocket['onopen'] = null;
  onmessage: WebSocket['onmessage'] = null;
  onclose: WebSocket['onclose'] = null;
  onerror: WebSocket['onerror'] = null;
  closed: { code?: number; reason?: string }[] = [];
  sent: string[] = [];

  emit(envelope: RealtimeEnvelope) {
    this.onmessage?.call(this as unknown as WebSocket, { data: JSON.stringify(envelope) } as MessageEvent);
  }

  disconnect(code: number) {
    this.onclose?.call(this as unknown as WebSocket, { code } as CloseEvent);
  }

  close(code?: number, reason?: string) {
    this.closed.push({ code, reason });
  }

  send(data: string) {
    this.sent.push(data);
  }
}

function connected(id: string): RealtimeEnvelope {
  return {
    version: 1,
    event: 'realtime.connected',
    event_id: id,
    occurred_at: '2026-08-17T12:00:00+00:00',
    data: { user_id: 7 },
  };
}

test('reconnects with backoff and resynchronizes before returning connected', async () => {
  const sockets: FakeSocket[] = [];
  const states: RealtimeState[] = [];
  const scheduled: (() => void)[] = [];
  let resyncs = 0;
  const client = new RealtimeClient({
    url: 'ws://example.test/api/realtime/ws',
    getAccessToken: () => 'access-token',
    refreshAccessToken: async () => 'renewed-token',
    createSocket: () => {
      const socket = new FakeSocket();
      sockets.push(socket);
      return socket;
    },
    onState: (state) => states.push(state),
    onEnvelope: () => undefined,
    async resynchronize() { resyncs += 1; },
    schedule: (callback) => { scheduled.push(callback); return 1 as never; },
    cancelSchedule: () => undefined,
    delayForAttempt: () => 1,
  });

  client.start();
  sockets[0].emit(connected('initial'));
  assert.equal(states.at(-1), 'connected');
  sockets[0].disconnect(1006);
  assert.equal(states.at(-1), 'reconnecting');
  assert.equal(scheduled.length, 1);
  scheduled.shift()?.();
  sockets[1].emit(connected('reconnected'));
  await Promise.resolve();
  assert.deepEqual(states.slice(-2), ['resynchronizing', 'connected']);
  assert.equal(resyncs, 1);
  client.stop();
  assert.deepEqual(sockets[1].closed.at(-1), { code: 1000, reason: 'session_closed' });
  assert.equal(states.at(-1), 'disconnected');
});

test('access-token rejection refreshes once through the supplied HTTP session flow', async () => {
  const sockets: FakeSocket[] = [];
  const protocols: string[][] = [];
  let token = 'expired-token';
  let refreshes = 0;
  const client = new RealtimeClient({
    url: 'ws://example.test/api/realtime/ws',
    getAccessToken: () => token,
    async refreshAccessToken() {
      refreshes += 1;
      token = 'renewed-token';
      return token;
    },
    createSocket: (_url, offered) => {
      protocols.push(offered);
      const socket = new FakeSocket();
      sockets.push(socket);
      return socket;
    },
    onState: () => undefined,
    onEnvelope: () => undefined,
    resynchronize: async () => undefined,
  });
  client.start();
  sockets[0].disconnect(4401);
  await Promise.resolve();
  await Promise.resolve();
  assert.equal(refreshes, 1);
  assert.equal(sockets.length, 2);
  assert.equal(protocols[1][1], 'auth.renewed-token');
  client.stop();
});

test('background and logout close sockets and suppress retry timers', () => {
  const sockets: FakeSocket[] = [];
  let scheduled = 0;
  const client = new RealtimeClient({
    url: 'ws://example.test/api/realtime/ws',
    getAccessToken: () => 'token',
    refreshAccessToken: async () => null,
    createSocket: () => {
      const socket = new FakeSocket(); sockets.push(socket); return socket;
    },
    onState: () => undefined,
    onEnvelope: () => undefined,
    resynchronize: async () => undefined,
    schedule: () => { scheduled += 1; return 1 as never; },
  });
  client.start();
  client.background();
  sockets[0].disconnect(1006);
  assert.equal(scheduled, 0);
  assert.deepEqual(sockets[0].closed[0], { code: 1000, reason: 'app_background' });
  client.stop();
});

test('sends commands only while the session socket is active', () => {
  const socket = new FakeSocket();
  const client = new RealtimeClient({
    url: 'ws://example.test/api/realtime/ws',
    getAccessToken: () => 'token',
    refreshAccessToken: async () => null,
    createSocket: () => socket,
    onState: () => undefined,
    onEnvelope: () => undefined,
    resynchronize: async () => undefined,
  });
  assert.equal(client.sendCommand('typing.started'), false);
  client.start();
  assert.equal(client.sendCommand('typing.started', { conversation_id: 9 }), true);
  assert.deepEqual(JSON.parse(socket.sent[0]), {
    event: 'typing.started', data: { conversation_id: 9 },
  });
  client.stop();
  assert.equal(client.sendCommand('typing.stopped'), false);
});

test('reconnection policy is bounded and does not retry policy closures', () => {
  assert.equal(reconnectDelayMs(0, () => 0), 1_000);
  assert.equal(reconnectDelayMs(20, () => 1), 30_000);
  assert.equal(shouldRetryClose(1006), true);
  assert.equal(shouldRetryClose(1000), false);
  assert.equal(shouldRetryClose(1008), false);
  assert.equal(shouldRetryClose(4403), false);
});

test('sends periodic connection.ping while connected and forces a reconnect after prolonged silence', () => {
  type Entry = { callback: () => void; delay: number };
  const sockets: FakeSocket[] = [];
  const states: RealtimeState[] = [];
  let entries: Entry[] = [];
  let clock = 0;
  const client = new RealtimeClient({
    url: 'ws://example.test/api/realtime/ws',
    getAccessToken: () => 'access-token',
    refreshAccessToken: async () => 'renewed-token',
    createSocket: () => {
      const socket = new FakeSocket();
      sockets.push(socket);
      return socket;
    },
    onState: (state) => states.push(state),
    onEnvelope: () => undefined,
    resynchronize: async () => undefined,
    schedule: (callback, delay) => {
      const entry: Entry = { callback, delay };
      entries.push(entry);
      return entry as never;
    },
    cancelSchedule: (entry) => {
      entries = entries.filter((item) => item !== (entry as unknown as Entry));
    },
    delayForAttempt: () => 1,
    now: () => clock,
    heartbeatIntervalMs: 1_000,
    heartbeatTimeoutMs: 2_500,
  });

  const fireHeartbeatTick = () => {
    const index = entries.findIndex((entry) => entry.delay === 1_000);
    assert.ok(index >= 0, 'expected a scheduled heartbeat tick');
    const [entry] = entries.splice(index, 1);
    entry.callback();
  };

  client.start();
  sockets[0].emit(connected('initial'));
  assert.equal(states.at(-1), 'connected');

  clock += 500;
  fireHeartbeatTick();
  assert.deepEqual(JSON.parse(sockets[0].sent.at(-1) as string), {
    event: 'connection.ping', data: {},
  });

  clock += 3_000; // supera heartbeatTimeoutMs sin respuesta ni actividad del servidor
  fireHeartbeatTick();
  assert.deepEqual(sockets[0].closed.at(-1), { code: 4408, reason: 'heartbeat_timeout' });

  // El socket "zombie" recién cerrado localmente dispara su propio onclose,
  // tal como ocurriría con un WebSocket real; el flujo normal de reconexión
  // debe hacerse cargo (sin llamadas duplicadas a scheduleReconnect).
  sockets[0].disconnect(4408);
  assert.equal(states.at(-1), 'reconnecting');

  client.stop();
});

test('heartbeat stays off by default, leaving existing reconnect timing unaffected', () => {
  const sockets: FakeSocket[] = [];
  const scheduledDelays: number[] = [];
  const client = new RealtimeClient({
    url: 'ws://example.test/api/realtime/ws',
    getAccessToken: () => 'token',
    refreshAccessToken: async () => null,
    createSocket: () => { const socket = new FakeSocket(); sockets.push(socket); return socket; },
    onState: () => undefined,
    onEnvelope: () => undefined,
    resynchronize: async () => undefined,
    schedule: (_callback, delay) => { scheduledDelays.push(delay); return 1 as never; },
  });
  client.start();
  sockets[0].emit(connected('initial'));
  assert.equal(scheduledDelays.length, 0);
  client.stop();
});
