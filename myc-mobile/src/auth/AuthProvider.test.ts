import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import ts from 'typescript';
import type { TokenPair } from '../types/auth';

type AuthValue = {
  session: TokenPair | null;
  login(email: string, password: string): Promise<unknown>;
  refreshSession(): Promise<TokenPair>;
  logout(): Promise<void>;
  authorizedFetch(path: string): Promise<Response>;
};
const sourceRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const deviceKey = 'myc.security.device_uuid.v1';
const sessionKey = 'myc.internal.session.v1';
const uuid = '71ed56b4-516b-4705-a496-aebf294d32a4';
const tokenPair = (access = 'old', refresh = 'opaque-old'): TokenPair => ({
  access_token: access, refresh_token: refresh, token_type: 'bearer',
  user: { id: 7, email: 'user@example.com', full_name: 'User', is_active: true,
    permissions: ['mobile.access'], actor_type: 'internal', client_id: null, membership_id: null },
});
function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (error: Error) => void;
  const promise = new Promise<T>((ok, fail) => { resolve = ok; reject = fail; });
  return { promise, resolve, reject };
}
const settle = () => new Promise<void>((done) => setImmediate(done));

// Execute the real provider, auth service, HTTP client, storage and device helper.
// Replace only React's hook scheduler and native/platform ports (same repo render-test pattern).
function harness(request: typeof fetch, initial: TokenPair | null = tokenPair(), pushFails = false) {
  const store = new Map<string, string>();
  if (initial) store.set(sessionKey, JSON.stringify(initial));
  const events: string[] = [];
  const slots: unknown[] = [];
  const modules = new Map<string, Record<string, unknown>>();
  const effects: (() => unknown)[] = [];
  let cursor = 0;
  let uuidCalls = 0;
  const ports: Record<string, unknown> = {
    react: {
      createContext: () => ({ Provider: 'provider' }),
      useState: (initialValue: unknown) => {
        const index = cursor++;
        if (!(index in slots)) slots[index] = initialValue;
        return [slots[index], (value: unknown) => { slots[index] = value; }];
      },
      useRef: (current: unknown) => {
        const index = cursor++;
        if (!(index in slots)) slots[index] = { current };
        return slots[index];
      },
      useCallback: (fn: unknown) => fn,
      useMemo: (fn: () => unknown) => fn(),
      useEffect: (fn: () => unknown) => {
        const index = cursor++;
        if (!(index in slots)) { slots[index] = true; effects.push(fn); }
      },
    },
    'react/jsx-runtime': { jsx: (_type: unknown, props: unknown) => props },
    'react-native': { Platform: { OS: 'ios' } },
    'expo-secure-store': {
      getItemAsync: async (key: string) => store.get(key) ?? null,
      setItemAsync: async (key: string, value: string) => { events.push(`write:${key}`); store.set(key, value); },
      deleteItemAsync: async (key: string) => { events.push(`clear:${key}`); store.delete(key); },
    },
    'expo-crypto': { randomUUID: () => { uuidCalls++; return uuid; } },
    'expo-device': { deviceName: 'Test phone' },
    'expo-constants': { default: { expoConfig: { version: '1.0' } } },
    '@/src/config/environment': { API_BASE_URL: 'https://example.test/api' },
    '@/src/services/push-notifications': {
      deactivateCurrentDevice: async (accessToken: string) => {
        assert.equal(accessToken, initial?.access_token);
        events.push('push:deactivate');
        if (pushFails) throw new Error('push offline');
      },
    },
  };
  function load(name: string): Record<string, unknown> {
    if (ports[name]) return ports[name] as Record<string, unknown>;
    if (modules.has(name)) return modules.get(name)!;
    const relative = name.replace('@/src/', '');
    const path = resolve(sourceRoot, relative + (relative === 'auth/AuthProvider' ? '.tsx' : '.ts'));
    const javascript = ts.transpileModule(readFileSync(path, 'utf8'), { compilerOptions: {
      target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX,
    } }).outputText;
    const exports: Record<string, unknown> = {};
    new Function('require', 'exports', 'fetch', javascript)(load, exports, request);
    modules.set(name, exports);
    return exports;
  }
  const provider = load('@/src/auth/AuthProvider').AuthProvider as (props: object) => { value: AuthValue };
  const render = () => { cursor = 0; const result = provider({}); effects.splice(0).forEach((fn) => fn()); return result.value; };
  render();
  return { render, store, events, load, uuidCalls: () => uuidCalls };
}

test('three concurrent 401s and realtime share one refresh HTTP and renewed access', async () => {
  const gate = deferred<Response>();
  let refreshCalls = 0;
  const retried: string[] = [];
  const app = harness((async (input, init) => {
    if (String(input).endsWith('/refresh')) { refreshCalls++; return gate.promise; }
    const auth = new Headers(init?.headers).get('Authorization');
    if (auth === 'Bearer old') return new Response(null, { status: 401 });
    retried.push(auth!);
    return new Response(null, { status: 200 });
  }) as typeof fetch);
  await settle();
  const auth = app.render();
  const requests = [auth.authorizedFetch('/one'), auth.authorizedFetch('/two'), auth.authorizedFetch('/three')];
  const realtime = auth.refreshSession();
  await settle();
  assert.equal(refreshCalls, 1);
  gate.resolve(Response.json(tokenPair('renewed', 'opaque-next')));
  assert.deepEqual((await Promise.all(requests)).map((res) => res.status), [200, 200, 200]);
  assert.equal((await realtime).access_token, 'renewed');
  assert.deepEqual(retried, ['Bearer renewed', 'Bearer renewed', 'Bearer renewed']);
  assert.equal(app.render().session?.refresh_token, 'opaque-next');
});

test('late 401 reuses completed refresh instead of rotating again', async () => {
  const late = deferred<Response>();
  let refreshCalls = 0;
  const app = harness((async (input, init) => {
    if (String(input).endsWith('/refresh')) { refreshCalls++; return Response.json(tokenPair('renewed', 'opaque-next')); }
    if (new Headers(init?.headers).get('Authorization') === 'Bearer renewed') return new Response(null, { status: 200 });
    if (input === '/late') return late.promise;
    return new Response(null, { status: 401 });
  }) as typeof fetch);
  await settle();
  const auth = app.render();
  const delayed = auth.authorizedFetch('/late');
  assert.equal((await auth.authorizedFetch('/early')).status, 200);
  late.resolve(new Response(null, { status: 401 }));
  assert.equal((await delayed).status, 200);
  assert.equal(refreshCalls, 1);
});

test('refresh failure clears once, rejects all waiters and releases promise for next login', async () => {
  const gate = deferred<Response>();
  let refreshCalls = 0;
  const app = harness((async (input) => {
    if (String(input).endsWith('/login')) return Response.json(tokenPair());
    if (String(input).endsWith('/refresh')) { refreshCalls++; return refreshCalls === 1 ? gate.promise : Response.json(tokenPair('next')); }
    return new Response(null, { status: 401 });
  }) as typeof fetch);
  await settle();
  const auth = app.render();
  const results = Promise.allSettled([auth.authorizedFetch('/one'), auth.authorizedFetch('/two'), auth.authorizedFetch('/three')]);
  await settle();
  gate.reject(new Error('offline'));
  const settled = await results;
  assert.equal(refreshCalls, 1);
  assert.ok(settled.every((item) => item.status === 'rejected' && item.reason.message === 'offline'));
  assert.equal(app.render().session, null);
  assert.equal(app.store.has(sessionKey), false);
  assert.equal(app.events.filter((item) => item === `clear:${sessionKey}`).length, 1);
  await auth.login('user@example.com', 'password');
  assert.equal((await auth.refreshSession()).access_token, 'next');
  assert.equal(refreshCalls, 2);
});

for (const { pushFails, logoutFails } of [
  { pushFails: false, logoutFails: false },
  { pushFails: true, logoutFails: false },
  { pushFails: false, logoutFails: true },
  { pushFails: true, logoutFails: true },
]) {
  test(`logout attempts push before auth and always clears (pushFails=${pushFails}, logoutFails=${logoutFails})`, async () => {
    const app = harness((async (input, init) => {
      assert.match(String(input), /\/logout$/);
      assert.equal(new Headers(init?.headers).get('Authorization'), 'Bearer old');
      app.events.push('auth:logout');
      if (logoutFails) throw new Error('logout offline');
      return new Response(null, { status: 204 });
    }) as typeof fetch, tokenPair(), pushFails);
    app.store.set(deviceKey, uuid);
    await settle();
    const pending = app.render().logout();
    assert.equal(app.render().session, null); // Invalidated before any network await.
    await pending;
    assert.deepEqual(app.events, ['push:deactivate', 'auth:logout', `clear:${sessionKey}`]);
    assert.equal(app.render().session, null);
    assert.equal(app.store.has(sessionKey), false);
    assert.equal(app.store.get(deviceKey), uuid);
  });
}

test('logout during refresh revokes the returned successor without restoring local session', async () => {
  const gate = deferred<Response>();
  const revoked: string[] = [];
  const app = harness((async (input, init) => {
    if (String(input).endsWith('/refresh')) return gate.promise;
    revoked.push(new Headers(init?.headers).get('Authorization')!);
    return new Response(null, { status: 204 });
  }) as typeof fetch);
  await settle();
  const auth = app.render();
  const refresh = assert.rejects(auth.refreshSession(), /sesión cambió/);
  const logout = auth.logout();
  gate.resolve(Response.json(tokenPair('successor', 'opaque-successor')));
  await Promise.all([refresh, logout]);
  assert.ok(revoked.includes('Bearer successor'));
  assert.equal(app.render().session, null);
  assert.equal(app.store.has(sessionKey), false);
});

test('UUID is persisted before login and reused across calls and concurrent reads', async () => {
  let received: Record<string, unknown> = {};
  const app = harness((async (_input, init) => {
    assert.equal(app.store.get(deviceKey), uuid);
    received = JSON.parse(String(init?.body));
    return Response.json(tokenPair());
  }) as typeof fetch, null);
  await settle();
  const device = app.load('@/src/services/security-device') as { getSecurityDeviceUuid(): Promise<string> };
  assert.deepEqual(await Promise.all([device.getSecurityDeviceUuid(), device.getSecurityDeviceUuid()]), [uuid, uuid]);
  await app.render().login('USER@example.com', 'password');
  assert.equal(app.uuidCalls(), 1);
  assert.deepEqual(received.device, { device_uuid: uuid, platform: 'ios', device_name: 'Test phone', app_version: '1.0' });
  assert.equal(received.email, 'user@example.com');
  assert.equal(await device.getSecurityDeviceUuid(), uuid);
  assert.equal(app.uuidCalls(), 1);
});

test('existing SecureStore identity survives a fresh helper instance; empty storage generates again', async () => {
  const app = harness((async () => Response.json(tokenPair())) as typeof fetch, null);
  const existing = 'bc69bf83-e885-4b06-914f-a3c7c561d416';
  app.store.set(deviceKey, existing);
  const device = app.load('@/src/services/security-device') as { getSecurityDeviceUuid(): Promise<string> };
  assert.equal(await device.getSecurityDeviceUuid(), existing);
  assert.equal(app.uuidCalls(), 0);
  app.store.clear(); // Models a new/cleared SecureStore. iOS reinstall may preserve Keychain.
  assert.equal(await device.getSecurityDeviceUuid(), uuid);
  assert.notEqual(uuid, existing);
  assert.equal(app.uuidCalls(), 1);
});

test('legacy refresh sends device once; subsequent opaque refresh omits it', async () => {
  const bodies: Record<string, unknown>[] = [];
  const app = harness((async (_input, init) => {
    bodies.push(JSON.parse(String(init?.body)));
    return Response.json(tokenPair('new', 'opaque-next'));
  }) as typeof fetch, tokenPair('old', 'eyJhIjox.eyJiIjoy.signature'));
  await settle();
  const auth = app.render();
  await auth.refreshSession();
  await auth.refreshSession();
  assert.equal(bodies.length, 2);
  assert.equal((bodies[0].device as Record<string, unknown>).device_uuid, uuid);
  assert.deepEqual(bodies[1], { refresh_token: 'opaque-next' });
  assert.equal(app.uuidCalls(), 1);
  assert.equal(app.events.includes('push:deactivate'), false);
});
