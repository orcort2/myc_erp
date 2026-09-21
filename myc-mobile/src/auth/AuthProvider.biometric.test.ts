import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import ts from 'typescript';
import type { TokenPair } from '../types/auth';

type BiometricProfile = { user_id: number; email: string; full_name: string; biometric_label: string };

type AuthValue = {
  session: TokenPair | null;
  biometricProfile: BiometricProfile | null;
  biometricAvailable: boolean;
  login(email: string, password: string): Promise<unknown>;
  logout(): Promise<void>;
  biometricLogin(): Promise<unknown>;
  enableBiometric(): Promise<void>;
  disableBiometric(): Promise<void>;
};

const sourceRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const sessionKey = 'myc.internal.session.v1';
const profileKey = 'myc.biometric.profile.v1';
const credentialKey = 'myc.biometric.credential.v1';
const uuid = '71ed56b4-516b-4705-a496-aebf294d32a4';

const tokenPair = (access = 'access', refresh = 'refresh'): TokenPair => ({
  access_token: access, refresh_token: refresh, token_type: 'bearer',
  user: { id: 7, email: 'user@example.com', full_name: 'User Example', is_active: true,
    permissions: ['mobile.access'], actor_type: 'internal', client_id: null, membership_id: null },
});

const profile: BiometricProfile = {
  user_id: 7, email: 'user@example.com', full_name: 'User Example', biometric_label: 'Face ID',
};

const settle = () => new Promise<void>((done) => setImmediate(done));

type HarnessOptions = {
  initialSession?: TokenPair | null;
  initialProfile?: BiometricProfile | null;
  initialCredential?: string | null;
  hasHardware?: boolean;
  isEnrolled?: boolean;
  authenticateResult?: boolean;
  protectedReadError?: Error | null;
  protectedReadResolvesNull?: boolean;
};

// Executes the real provider, auth service, biometric service and storage
// modules; only React's hook scheduler and native/platform ports are
// replaced -- same convention as AuthProvider.test.ts.
function harness(request: typeof fetch, options: HarnessOptions = {}) {
  const store = new Map<string, string>();
  if (options.initialSession) store.set(sessionKey, JSON.stringify(options.initialSession));
  if (options.initialProfile) store.set(profileKey, JSON.stringify(options.initialProfile));
  if (options.initialCredential) store.set(credentialKey, options.initialCredential);
  const events: string[] = [];
  const slots: unknown[] = [];
  const modules = new Map<string, Record<string, unknown>>();
  const effects: (() => unknown)[] = [];
  let cursor = 0;

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
      WHEN_UNLOCKED_THIS_DEVICE_ONLY: 0,
      getItemAsync: async (key: string, opts?: { requireAuthentication?: boolean }) => {
        if (opts?.requireAuthentication && key === credentialKey) {
          events.push('read-protected-credential');
          if (options.protectedReadError) throw options.protectedReadError;
          if (options.protectedReadResolvesNull) return null;
        }
        return store.get(key) ?? null;
      },
      setItemAsync: async (key: string, value: string, opts?: { requireAuthentication?: boolean }) => {
        events.push(`write:${key}${opts?.requireAuthentication ? ':protected' : ''}`);
        store.set(key, value);
      },
      deleteItemAsync: async (key: string) => { events.push(`clear:${key}`); store.delete(key); },
    },
    'expo-crypto': { randomUUID: () => uuid },
    'expo-device': { deviceName: 'Test phone' },
    'expo-constants': { default: { expoConfig: { version: '1.0' } } },
    'expo-local-authentication': {
      AuthenticationType: { FINGERPRINT: 1, FACIAL_RECOGNITION: 2, IRIS: 3 },
      hasHardwareAsync: async () => options.hasHardware ?? true,
      isEnrolledAsync: async () => options.isEnrolled ?? true,
      supportedAuthenticationTypesAsync: async () => [2],
      authenticateAsync: async () => {
        events.push('local-auth:prompt');
        return (options.authenticateResult ?? true)
          ? { success: true } : { success: false, error: 'user_cancel' as const };
      },
    },
    '@/src/config/environment': { API_BASE_URL: 'https://example.test/api' },
    '@/src/services/push-notifications': {
      deactivateCurrentDevice: async () => { events.push('push:deactivate'); },
    },
  };

  function resolveModulePath(name: string, fromDir: string): string {
    if (name.startsWith('.')) {
      const base = resolve(fromDir, name);
      return existsSync(`${base}.tsx`) ? `${base}.tsx` : `${base}.ts`;
    }
    const relative = name.replace('@/src/', '');
    return resolve(sourceRoot, relative + (relative === 'auth/AuthProvider' ? '.tsx' : '.ts'));
  }
  function load(name: string, fromDir: string = sourceRoot): Record<string, unknown> {
    if (ports[name]) return ports[name] as Record<string, unknown>;
    const path = resolveModulePath(name, fromDir);
    if (modules.has(path)) return modules.get(path)!;
    const javascript = ts.transpileModule(readFileSync(path, 'utf8'), { compilerOptions: {
      target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX,
    } }).outputText;
    const exports: Record<string, unknown> = {};
    const moduleDir = dirname(path);
    modules.set(path, exports);
    new Function('require', 'exports', 'fetch', javascript)((dep: string) => load(dep, moduleDir), exports, request);
    return exports;
  }
  const provider = load('@/src/auth/AuthProvider').AuthProvider as (props: object) => { value: AuthValue };
  const render = () => { cursor = 0; const result = provider({}); effects.splice(0).forEach((fn) => fn()); return result.value; };
  render();
  return { render, store, events };
}

function router(handlers: Record<string, (init?: RequestInit) => Promise<Response>>): typeof fetch {
  return (async (input: string | URL | Request, init?: RequestInit) => {
    const url = String(input);
    for (const [suffix, handler] of Object.entries(handlers)) {
      if (url.endsWith(suffix)) return handler(init);
    }
    return new Response(null, { status: 404 });
  }) as typeof fetch;
}

test('opt-in explícito: login normal nunca enrola biometría por sí solo', async () => {
  const app = harness(router({
    '/login': async () => Response.json(tokenPair()),
  }));
  await settle();
  await app.render().login('user@example.com', 'password');
  assert.equal(app.render().biometricProfile, null);
  assert.equal(app.store.has(profileKey), false);
  assert.equal(app.store.has(credentialKey), false);
});

test('enableBiometric ejecuta biometría local, llama a enroll y guarda credencial protegida + perfil sin password', async () => {
  let enrollCalled = false;
  const app = harness(router({
    '/login': async () => Response.json(tokenPair()),
    '/biometric/enroll': async (init) => {
      enrollCalled = true;
      assert.equal(new Headers(init?.headers).get('Authorization'), 'Bearer access');
      return Response.json({ biometric_credential: 'opaque-bio-credential', expires_at: '2027-01-01T00:00:00Z' });
    },
  }));
  await settle();
  const auth = app.render();
  await auth.login('user@example.com', 'password');
  await auth.enableBiometric();
  assert.ok(enrollCalled);
  assert.ok(app.events.includes('local-auth:prompt'));
  assert.equal(app.store.get(credentialKey), 'opaque-bio-credential');
  assert.ok(app.events.includes(`write:${credentialKey}:protected`));
  const storedProfile = JSON.parse(app.store.get(profileKey)!);
  assert.deepEqual(storedProfile, { user_id: 7, email: 'user@example.com', full_name: 'User Example', biometric_label: 'Face ID' });
  assert.doesNotMatch(app.store.get(profileKey)!, /password/i);
  assert.equal(app.render().biometricProfile?.biometric_label, 'Face ID');
});

test('cold start con biometría habilitada nunca restaura una sesión operativa en silencio', async () => {
  const app = harness(router({}), {
    initialSession: tokenPair(),
    initialProfile: profile,
    initialCredential: 'stored-credential',
  });
  await settle();
  const auth = app.render();
  assert.equal(auth.session, null);
  assert.equal(auth.biometricProfile?.email, profile.email);
});

test('login biométrico intercambia la credencial y produce un TokenPair sin persistir sesión operativa en disco', async () => {
  const app = harness(
    router({
      '/biometric/exchange': async (init) => {
        const body = JSON.parse(String(init?.body));
        assert.equal(body.biometric_credential, 'stored-credential');
        return Response.json(tokenPair('new-access', 'new-refresh'));
      },
    }),
    { initialProfile: profile, initialCredential: 'stored-credential' },
  );
  await settle();
  const auth = app.render();
  const user = await auth.biometricLogin();
  assert.equal((user as { email: string }).email, 'user@example.com');
  assert.equal(app.render().session?.access_token, 'new-access');
  // Biometric enabled for this installation: the operational session must
  // stay memory-only, never written to the plain session key.
  assert.equal(app.events.includes(`write:${sessionKey}`), false);
  assert.equal(app.store.has(sessionKey), false);
});

test('cancelar el prompt biométrico conserva el enrolamiento intacto', async () => {
  const app = harness(router({}), {
    initialProfile: profile,
    initialCredential: 'stored-credential',
    protectedReadError: new Error('user_cancel'),
  });
  await settle();
  const auth = app.render();
  await assert.rejects(auth.biometricLogin(), /user_cancel/);
  assert.equal(app.render().biometricProfile?.email, profile.email);
  assert.equal(app.store.get(credentialKey), 'stored-credential');
});

test('una credencial invalidada por el sistema limpia el enrolamiento y ofrece el fallback de contraseña', async () => {
  const app = harness(router({}), {
    initialProfile: profile,
    initialCredential: 'stored-credential',
    protectedReadResolvesNull: true,
  });
  await settle();
  const auth = app.render();
  await assert.rejects(auth.biometricLogin(), /configurarse nuevamente/);
  assert.equal(app.render().biometricProfile, null);
  assert.equal(app.store.has(profileKey), false);
  assert.equal(app.store.has(credentialKey), false);
});

test('un 401 del backend en exchange (credencial revocada/expirada) limpia el enrolamiento local', async () => {
  const app = harness(
    router({ '/biometric/exchange': async () => Response.json({ detail: 'Credencial biométrica inválida' }, { status: 401 }) }),
    { initialProfile: profile, initialCredential: 'stored-credential' },
  );
  await settle();
  const auth = app.render();
  await assert.rejects(auth.biometricLogin());
  assert.equal(app.render().biometricProfile, null);
  assert.equal(app.store.has(credentialKey), false);
});

test('logout conserva el perfil y la credencial biométricos', async () => {
  const app = harness(
    router({ '/logout': async () => new Response(null, { status: 204 }) }),
    { initialSession: tokenPair(), initialProfile: profile, initialCredential: 'stored-credential' },
  );
  await settle();
  const auth = app.render();
  await auth.logout();
  assert.equal(app.render().session, null);
  assert.equal(app.store.get(profileKey), JSON.stringify(profile));
  assert.equal(app.store.get(credentialKey), 'stored-credential');
});

test('disableBiometric revoca en el backend y elimina perfil + credencial locales', async () => {
  let revokeCalled = false;
  const app = harness(
    router({
      '/biometric/exchange': async () => Response.json(tokenPair()),
      '/biometric': async (init) => {
        revokeCalled = true;
        assert.equal(new Headers(init?.headers).get('Authorization'), 'Bearer access');
        return new Response(null, { status: 204 });
      },
    }),
    { initialProfile: profile, initialCredential: 'stored-credential' },
  );
  await settle();
  const auth = app.render();
  // A session must be active (via biometric login, since cold start never
  // auto-restores one) for disableBiometric to reach the backend at all.
  await auth.biometricLogin();
  await auth.disableBiometric();
  assert.ok(revokeCalled);
  assert.equal(app.store.has(profileKey), false);
  assert.equal(app.store.has(credentialKey), false);
  assert.equal(app.render().biometricProfile, null);
});

test('disableBiometric limpia el almacenamiento local aunque el DELETE falle por red', async () => {
  const app = harness(
    router({
      '/biometric/exchange': async () => Response.json(tokenPair()),
      '/biometric': async () => { throw new Error('network down'); },
    }),
    { initialProfile: profile, initialCredential: 'stored-credential' },
  );
  await settle();
  const auth = app.render();
  await auth.biometricLogin();
  await auth.disableBiometric();
  assert.equal(app.store.has(profileKey), false);
  assert.equal(app.store.has(credentialKey), false);
});
