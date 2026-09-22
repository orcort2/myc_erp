import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { mock, test } from 'node:test';
import { fileURLToPath } from 'node:url';
import ts from 'typescript';

import { hasDeveloperCapability } from '../permissions/developer-policy';

/**
 * DEV-0: DeveloperProvider owns its own privilege-session lifecycle,
 * separate from AuthProvider. Executes the real DeveloperProvider.tsx
 * source; only its dependencies (AuthProvider, the Developer HTTP client,
 * biometric storage) are mocked, same convention as AuthProvider.test.ts.
 */
const here = dirname(fileURLToPath(import.meta.url));

type AuthState = {
  session: { access_token: string } | null;
  user: { permissions: string[]; actor_type: 'internal' | 'client' } | null;
};

type Opened = { developer_token: string; expires_at: string; session_id: number };
type Status = { active: boolean; expires_at: string | null; remaining_seconds: number | null; user_id: number | null; device_id: number | null };
const INACTIVE: Status = { active: false, expires_at: null, remaining_seconds: null, user_id: null, device_id: null };

function harness(initialAuth: AuthState) {
  const slots: unknown[] = [];
  const effectSlots: { deps: unknown[] | undefined; cleanup?: () => void }[] = [];
  const memoSlots: { deps: unknown[] | undefined; value: unknown }[] = [];
  let cursor = 0;
  let effectCursor = 0;
  let memoCursor = 0;
  let authState = initialAuth;

  const calls = {
    readCredential: 0,
    open: [] as { accessToken: string; credential: string }[],
    status: [] as { accessToken: string; developerToken: string }[],
    lock: [] as { accessToken: string; developerToken: string }[],
  };

  let credentialToReturn: string | null = 'real-biometric-credential';
  let credentialGate: Promise<string | null> | null = null;
  let openSequence: Opened[] = [];
  let lockShouldThrow = false;
  let statusResponse: Status | Error = INACTIVE;
  let statusGate: Promise<void> | null = null;
  const appStateListeners = new Set<(state: string) => void>();
  let appStateSubscriptions = 0;

  function shallowEqual(a: unknown[] | undefined, b: unknown[] | undefined): boolean {
    if (a === b) return true;
    if (!a || !b || a.length !== b.length) return false;
    return a.every((value, index) => Object.is(value, b[index]));
  }

  const jsx = (type: unknown, props: unknown) => ({ type, props });
  const ports: Record<string, unknown> = {
    react: {
      createContext: () => ({ Provider: 'DeveloperContext.Provider' }),
      useState: (initial: unknown) => {
        const index = cursor++;
        if (!(index in slots)) slots[index] = typeof initial === 'function' ? (initial as () => unknown)() : initial;
        return [slots[index], (value: unknown) => {
          slots[index] = typeof value === 'function' ? (value as (prev: unknown) => unknown)(slots[index]) : value;
        }];
      },
      useRef: (current: unknown) => {
        const index = cursor++;
        if (!(index in slots)) slots[index] = { current };
        return slots[index];
      },
      // Faithful (deps-based) memoization -- unlike a naive `(fn) => fn`,
      // this matters here: DeveloperProvider's unmount-cleanup effect is
      // keyed on a useCallback reference, and a fresh function identity
      // every render would make that effect re-fire (and clear the ticking
      // interval) on every single render instead of only on real unmount.
      useCallback: (fn: unknown, deps?: unknown[]) => {
        const index = memoCursor++;
        const previous = memoSlots[index];
        if (previous && shallowEqual(previous.deps, deps)) return previous.value;
        memoSlots[index] = { deps, value: fn };
        return fn;
      },
      useMemo: (fn: () => unknown, deps?: unknown[]) => {
        const index = memoCursor++;
        const previous = memoSlots[index];
        if (previous && shallowEqual(previous.deps, deps)) return previous.value;
        const value = fn();
        memoSlots[index] = { deps, value };
        return value;
      },
      useEffect: (fn: () => void | (() => void), deps?: unknown[]) => {
        const index = effectCursor++;
        const previous = effectSlots[index];
        const shouldRun = !previous || !shallowEqual(previous.deps, deps);
        if (shouldRun) {
          previous?.cleanup?.();
          const cleanup = fn();
          effectSlots[index] = { deps, cleanup: typeof cleanup === 'function' ? cleanup : undefined };
        }
      },
    },
    'react/jsx-runtime': { jsx, jsxs: jsx, Fragment: 'Fragment' },
    'react-native': {
      AppState: {
        currentState: 'active',
        addEventListener: (event: string, listener: (state: string) => void) => {
          assert.equal(event, 'change');
          appStateSubscriptions += 1;
          appStateListeners.add(listener);
          return { remove: () => { appStateListeners.delete(listener); } };
        },
      },
    },
    '@/src/auth/AuthProvider': { useAuth: () => authState },
    // The REAL explicit Developer policy, never a wildcard-aware mock.
    '@/src/permissions/developer-policy': { hasDeveloperCapability },
    '@/src/services/developer.service': {
      openDeveloperSession: async (accessToken: string, credential: string) => {
        calls.open.push({ accessToken, credential });
        const next = openSequence.shift();
        if (!next) throw new Error('no queued open() response in test');
        return next;
      },
      getDeveloperSessionStatus: async (accessToken: string, developerToken: string) => {
        calls.status.push({ accessToken, developerToken });
        if (statusGate) await statusGate;
        if (statusResponse instanceof Error) throw statusResponse;
        return statusResponse;
      },
      lockDeveloperSession: async (accessToken: string, developerToken: string) => {
        calls.lock.push({ accessToken, developerToken });
        if (lockShouldThrow) throw new Error('network down');
      },
    },
    '@/src/storage/biometric-storage': {
      readBiometricCredential: async () => {
        calls.readCredential++;
        if (credentialGate) return credentialGate;
        return credentialToReturn;
      },
    },
  };
  const require_ = (name: string): unknown => {
    if (name in ports) return ports[name];
    throw new Error(`unexpected import in DeveloperProvider test: ${name}`);
  };
  const source = readFileSync(resolve(here, 'DeveloperProvider.tsx'), 'utf8');
  const javascript = ts.transpileModule(source, { compilerOptions: {
    target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX,
  } }).outputText;
  const exports: Record<string, unknown> = {};
  new Function('require', 'exports', javascript)(require_, exports);
  const Provider = exports.DeveloperProvider as (props: { children: unknown }) => { props: { value: unknown } };

  function render() {
    cursor = 0;
    effectCursor = 0;
    memoCursor = 0;
    return Provider({ children: null }).props.value as {
      isDeveloperAvailable: boolean;
      isDeveloperUnlocked: boolean;
      remainingSeconds: number | null;
      showExpirationWarning: boolean;
      unlockDeveloper: () => Promise<void>;
      lockDeveloper: () => Promise<void>;
      dismissExpirationWarning: () => void;
      refreshDeveloperStatus: () => Promise<void>;
    };
  }

  function unmount() {
    for (const slot of effectSlots) slot?.cleanup?.();
  }

  return {
    render,
    unmount,
    calls,
    appState: {
      emit(state: string) { for (const listener of [...appStateListeners]) listener(state); },
      get listeners() { return appStateListeners.size; },
      get subscriptions() { return appStateSubscriptions; },
    },
    setStatus(value: Status | Error) { statusResponse = value; },
    deferStatus() {
      let release!: () => void;
      statusGate = new Promise<void>((resolveGate) => { release = resolveGate; });
      return () => { release(); statusGate = null; };
    },
    setAuth(next: AuthState) { authState = next; },
    setCredential(value: string | null) { credentialToReturn = value; },
    deferCredential() {
      let release!: (value: string | null) => void;
      credentialGate = new Promise<string | null>((resolveGate) => { release = resolveGate; });
      return (value: string | null) => { release(value); credentialGate = null; };
    },
    queueOpen(...opened: Opened[]) { openSequence = [...openSequence, ...opened]; },
    setLockThrows(value: boolean) { lockShouldThrow = value; },
  };
}

const settle = () => new Promise<void>((done) => setImmediate(done));

const devUser = { permissions: ['mobile.access', 'developer.access'], actor_type: 'internal' as const };
const adminOnlyWildcard = { permissions: ['*'], actor_type: 'internal' as const };
const technicianUser = { permissions: ['mobile.access'], actor_type: 'internal' as const };
const session = (token = 'access-1') => ({ access_token: token });

function opened(token: string, secondsFromNow = 600, sessionId = 1): Opened {
  return { developer_token: token, expires_at: new Date(Date.now() + secondsFromNow * 1000).toISOString(), session_id: sessionId };
}

test('isDeveloperAvailable exige developer.access; cold start siempre bloqueado', () => {
  const app = harness({ session: session(), user: devUser });
  const value = app.render();
  assert.equal(value.isDeveloperAvailable, true);
  assert.equal(value.isDeveloperUnlocked, false);
  assert.equal(value.remainingSeconds, null);
});

test('unlockDeveloper lee la credencial biométrica real, nunca un boolean', async () => {
  const app = harness({ session: session(), user: devUser });
  app.queueOpen(opened('token-1'));
  let value = app.render();
  await value.unlockDeveloper();
  assert.equal(app.calls.readCredential, 1);
  assert.equal(app.calls.open.length, 1);
  assert.equal(app.calls.open[0].credential, 'real-biometric-credential');
  value = app.render();
  await value.lockDeveloper(); // clears the real setInterval this test started
});

test('sin credencial biométrica, unlockDeveloper falla y nunca llama al backend', async () => {
  const app = harness({ session: session(), user: devUser });
  app.setCredential(null);
  const value = app.render();
  await assert.rejects(value.unlockDeveloper());
  assert.equal(app.calls.open.length, 0);
});

test('un unlock exitoso queda unlocked y con countdown', async () => {
  const app = harness({ session: session(), user: devUser });
  app.queueOpen(opened('token-1', 600));
  const first = app.render();
  await first.unlockDeveloper();
  await settle();
  const after = app.render();
  assert.equal(after.isDeveloperUnlocked, true);
  assert.ok(after.remainingSeconds !== null && after.remainingSeconds > 590);
  await after.lockDeveloper(); // clears the real setInterval this test started
});

test('lockDeveloper limpia el estado local y revoca en el backend', async () => {
  const app = harness({ session: session(), user: devUser });
  app.queueOpen(opened('token-1'));
  let value = app.render();
  await value.unlockDeveloper();
  value = app.render();
  await value.lockDeveloper();
  value = app.render();
  assert.equal(value.isDeveloperUnlocked, false);
  assert.equal(app.calls.lock.length, 1);
  assert.equal(app.calls.lock[0].developerToken, 'token-1');
});

test('lockDeveloper es best-effort: un fallo de red igual deja el estado local bloqueado', async () => {
  const app = harness({ session: session(), user: devUser });
  app.queueOpen(opened('token-1'));
  let value = app.render();
  await value.unlockDeveloper();
  app.setLockThrows(true);
  value = app.render();
  await value.lockDeveloper();
  value = app.render();
  assert.equal(value.isDeveloperUnlocked, false);
});

test('el token nunca se persiste -- ningún import de storage-write, sólo la lectura protegida de biometría', () => {
  const source = readFileSync(resolve(here, 'DeveloperProvider.tsx'), 'utf8');
  const imports = [...source.matchAll(/from '([^']+)'/g)].map((match) => match[1]);
  assert.deepEqual(imports.sort(), [
    '@/src/auth/AuthProvider',
    '@/src/permissions/developer-policy',
    '@/src/services/developer.service',
    '@/src/storage/biometric-storage',
    'react',
    'react-native',
  ].sort());
});

test('logout dentro de la ventana del unlock impide resucitar Developer (P14)', async () => {
  const app = harness({ session: session('access-1'), user: devUser });
  app.queueOpen(opened('token-1'));
  const releaseCredential = app.deferCredential(); // holds unlockDeveloper() mid-Face-ID
  const value = app.render();

  const unlockPromise = value.unlockDeveloper();
  // Logout lands while we are still "waiting on Face ID".
  app.setAuth({ session: null, user: null });
  app.render();
  releaseCredential('real-biometric-credential');
  await assert.rejects(unlockPromise); // the stale unlock must surface as a failure, never resurrect state

  const after = app.render();
  assert.equal(after.isDeveloperUnlocked, false);
  // The orphaned DeveloperSession opened mid-race must still be revoked.
  assert.ok(app.calls.lock.some((call) => call.developerToken === 'token-1'));
});

test('logout limpia Developer inmediatamente incluso ya desbloqueado', async () => {
  const app = harness({ session: session(), user: devUser });
  app.queueOpen(opened('token-1'));
  let value = app.render();
  await value.unlockDeveloper();
  app.setAuth({ session: null, user: null });
  app.render(); // this pass runs the logout effect, which schedules the clear
  value = app.render(); // this pass observes the cleared state, like React would after commit
  assert.equal(value.isDeveloperUnlocked, false);
  assert.ok(app.calls.lock.some((call) => call.developerToken === 'token-1'));
});

test('la expiración por countdown local limpia el estado sin llamar al backend', async () => {
  mock.timers.enable({ apis: ['setInterval', 'Date'] });
  try {
    const app = harness({ session: session(), user: devUser });
    app.queueOpen(opened('token-1', 5));
    let value = app.render();
    await value.unlockDeveloper();
    value = app.render();
    assert.equal(value.isDeveloperUnlocked, true);
    mock.timers.tick(6000);
    value = app.render();
    assert.equal(value.isDeveloperUnlocked, false);
    assert.equal(value.remainingSeconds, null);
  } finally {
    mock.timers.reset();
  }
});

test('el warning de expiración aparece una sola vez por ciclo', async () => {
  mock.timers.enable({ apis: ['setInterval', 'Date'] });
  try {
    const app = harness({ session: session(), user: devUser });
    app.queueOpen(opened('token-1', 90));
    let value = app.render();
    await value.unlockDeveloper();
    value = app.render();
    assert.equal(value.showExpirationWarning, false);
    mock.timers.tick(31_000); // remaining ~59s: crosses the 60s threshold
    value = app.render();
    assert.equal(value.showExpirationWarning, true);
    value.dismissExpirationWarning();
    value = app.render();
    assert.equal(value.showExpirationWarning, false);
    mock.timers.tick(5000); // still under threshold -- must not re-fire
    value = app.render();
    assert.equal(value.showExpirationWarning, false);
  } finally {
    mock.timers.reset();
  }
});

test('"Extender con Face ID" (unlockDeveloper de nuevo) obtiene una nueva DeveloperSession', async () => {
  mock.timers.enable({ apis: ['setInterval', 'Date'] });
  try {
    const app = harness({ session: session(), user: devUser });
    app.queueOpen(opened('token-1', 90), opened('token-2', 600));
    let value = app.render();
    await value.unlockDeveloper();
    mock.timers.tick(31_000);
    value = app.render();
    assert.equal(value.showExpirationWarning, true);
    await value.unlockDeveloper();
    value = app.render();
    assert.equal(app.calls.open.length, 2);
    assert.equal(value.isDeveloperUnlocked, true);
    // token-2's expires_at was computed 31s of (fake) clock time before this
    // unlock landed, so ~569s -- comfortably more than the 90s the FIRST
    // session had left, proving this is a genuinely NEW DeveloperSession.
    assert.ok(value.remainingSeconds !== null && value.remainingSeconds > 500);
  } finally {
    mock.timers.reset();
  }
});

const activeStatus = (secondsFromNow = 600): Status => ({
  active: true,
  expires_at: new Date(Date.now() + secondsFromNow * 1000).toISOString(),
  remaining_seconds: secondsFromNow,
  user_id: 1,
  device_id: 1,
});

async function unlocked(app: ReturnType<typeof harness>, token = 'token-1', seconds = 600) {
  app.queueOpen(opened(token, seconds));
  await app.render().unlockDeveloper();
  return app.render();
}

// --- P0: explicit Developer policy --------------------------------------------------

test('P0: "*" (Administrador) por sí solo NO habilita Developer y unlock nunca llama al backend', async () => {
  const app = harness({ session: session(), user: adminOnlyWildcard });
  const value = app.render();
  assert.equal(value.isDeveloperAvailable, false);
  await assert.rejects(value.unlockDeveloper());
  assert.equal(app.calls.readCredential, 0);
  assert.equal(app.calls.open.length, 0);
});

test('P0: un actor client nunca tiene Developer aunque traiga developer.access', () => {
  const app = harness({ session: session(), user: { permissions: ['developer.access'], actor_type: 'client' } });
  assert.equal(app.render().isDeveloperAvailable, false);
});

// --- A. capability loss ---------------------------------------------------------------

test('A: perder developer.access (true → false) bloquea de inmediato y revoca best-effort, sin esperar countdown', async () => {
  const app = harness({ session: session('access-1'), user: devUser });
  let value = await unlocked(app);
  assert.equal(value.isDeveloperUnlocked, true);
  app.setAuth({ session: session('access-1'), user: technicianUser });
  app.render(); // capability-loss effect runs
  value = app.render();
  assert.equal(value.isDeveloperAvailable, false);
  assert.equal(value.isDeveloperUnlocked, false);
  assert.equal(value.remainingSeconds, null);
  assert.deepEqual(app.calls.lock, [{ accessToken: 'access-1', developerToken: 'token-1' }]);
  assert.equal(app.calls.status.length, 0);
});

test('A: quedar sólo con "*" tras refrescar permisos también bloquea', async () => {
  const app = harness({ session: session('access-1'), user: devUser });
  await unlocked(app);
  app.setAuth({ session: session('access-1'), user: adminOnlyWildcard });
  app.render();
  assert.equal(app.render().isDeveloperUnlocked, false);
});

test('A: perder la capacidad mientras un unlock espera biometría descarta el resultado y revoca el huérfano', async () => {
  const app = harness({ session: session('access-1'), user: devUser });
  app.queueOpen(opened('token-1'));
  const releaseCredential = app.deferCredential();
  const pending = app.render().unlockDeveloper();
  app.setAuth({ session: session('access-1'), user: technicianUser });
  app.render();
  releaseCredential('real-biometric-credential');
  await assert.rejects(pending);
  assert.equal(app.render().isDeveloperUnlocked, false);
  assert.ok(app.calls.lock.some((call) => call.developerToken === 'token-1'));
});

test('A: sin token en memoria, perder la capacidad no genera requests', () => {
  const app = harness({ session: session(), user: devUser });
  app.render();
  app.setAuth({ session: session(), user: technicianUser });
  app.render();
  app.render();
  assert.equal(app.calls.lock.length, 0);
  assert.equal(app.calls.status.length, 0);
});

// --- B. foreground reconciliation ------------------------------------------------------

test('B: volver a foreground con token consulta el backend y active:false limpia Developer', async () => {
  const app = harness({ session: session('access-1'), user: devUser });
  await unlocked(app);
  app.setStatus(INACTIVE);
  app.appState.emit('active');
  await settle();
  const value = app.render();
  assert.deepEqual(app.calls.status, [{ accessToken: 'access-1', developerToken: 'token-1' }]);
  assert.equal(value.isDeveloperUnlocked, false);
});

test('B: foreground con sesión aún activa conserva Developer y re-sincroniza el reloj', async () => {
  const app = harness({ session: session(), user: devUser });
  await unlocked(app, 'token-1', 600);
  app.setStatus(activeStatus(300)); // server says 300s left: the server wins
  app.appState.emit('active');
  await settle();
  const value = app.render();
  assert.equal(value.isDeveloperUnlocked, true);
  assert.ok(value.remainingSeconds !== null && value.remainingSeconds <= 300 && value.remainingSeconds > 290);
  await value.lockDeveloper();
});

test('B: una reconciliación de la MISMA sesión no vuelve a disparar el warning ya mostrado', async () => {
  mock.timers.enable({ apis: ['setInterval', 'Date'] });
  try {
    const app = harness({ session: session(), user: devUser });
    let value = await unlocked(app, 'token-1', 90);
    mock.timers.tick(31_000);
    value = app.render();
    assert.equal(value.showExpirationWarning, true);
    value.dismissExpirationWarning();
    app.setStatus(activeStatus(59));
    app.appState.emit('active');
    await settle();
    value = app.render();
    assert.equal(value.isDeveloperUnlocked, true);
    assert.equal(value.showExpirationWarning, false);
    await value.lockDeveloper();
  } finally {
    mock.timers.reset();
  }
});

test('B: foreground sin token en memoria, background o inactive nunca consultan el backend', async () => {
  const app = harness({ session: session(), user: devUser });
  app.render();
  app.appState.emit('active');
  await settle();
  assert.equal(app.calls.status.length, 0);
  await unlocked(app);
  app.appState.emit('background');
  app.appState.emit('inactive');
  await settle();
  assert.equal(app.calls.status.length, 0);
  await app.render().lockDeveloper();
});

test('B: un error de red al reconciliar falla cerrado (bloquea)', async () => {
  const app = harness({ session: session(), user: devUser });
  await unlocked(app);
  app.setStatus(new Error('network down'));
  app.appState.emit('active');
  await settle();
  assert.equal(app.render().isDeveloperUnlocked, false);
});

test('B: un único listener AppState durante toda la vida del provider, removido al desmontar', async () => {
  const app = harness({ session: session(), user: devUser });
  await unlocked(app);
  for (let index = 0; index < 5; index += 1) app.render();
  assert.equal(app.appState.subscriptions, 1);
  assert.equal(app.appState.listeners, 1);
  await app.render().lockDeveloper();
  app.unmount();
  assert.equal(app.appState.listeners, 0);
});

test('B: foreground + reentrada simultáneas producen una sola consulta (dedupe)', async () => {
  const app = harness({ session: session(), user: devUser });
  const value = await unlocked(app);
  app.setStatus(activeStatus(500));
  const release = app.deferStatus();
  app.appState.emit('active');
  const entry = value.refreshDeveloperStatus();
  release();
  await entry;
  await settle();
  assert.equal(app.calls.status.length, 1);
  await app.render().lockDeveloper();
});

test('B: una respuesta de reconciliación tardía nunca resucita Developer tras un lock', async () => {
  const app = harness({ session: session(), user: devUser });
  const value = await unlocked(app);
  app.setStatus(activeStatus(500));
  const release = app.deferStatus();
  const reconcile = value.refreshDeveloperStatus();
  await value.lockDeveloper();
  release();
  await reconcile;
  assert.equal(app.render().isDeveloperUnlocked, false);
});

test('B: la respuesta tardía del token anterior no afecta al token nuevo tras "Extender"', async () => {
  const app = harness({ session: session(), user: devUser });
  const value = await unlocked(app, 'token-1');
  app.setStatus(INACTIVE); // token-1 was superseded server-side
  const release = app.deferStatus();
  const reconcile = value.refreshDeveloperStatus();
  app.queueOpen(opened('token-2'));
  await app.render().unlockDeveloper();
  release();
  await reconcile;
  const after = app.render();
  assert.equal(after.isDeveloperUnlocked, true);
  await after.lockDeveloper();
  assert.equal(app.calls.lock.at(-1)?.developerToken, 'token-2');
});

// --- rotation of the Mobile access token -------------------------------------------------

test('rotación del access token Mobile: reconcilia con el token nuevo y active:false limpia', async () => {
  const app = harness({ session: session('access-1'), user: devUser });
  await unlocked(app);
  app.setStatus(INACTIVE);
  app.setAuth({ session: session('access-2'), user: devUser });
  app.render();
  await settle();
  assert.deepEqual(app.calls.status, [{ accessToken: 'access-2', developerToken: 'token-1' }]);
  assert.equal(app.render().isDeveloperUnlocked, false);
});

// --- no polling ---------------------------------------------------------------------------

test('el countdown local nunca hace polling al backend', async () => {
  mock.timers.enable({ apis: ['setInterval', 'Date'] });
  try {
    const app = harness({ session: session(), user: devUser });
    await unlocked(app, 'token-1', 600);
    for (let second = 0; second < 120; second += 1) {
      mock.timers.tick(1000);
      app.render();
    }
    assert.equal(app.calls.status.length, 0);
    await app.render().lockDeveloper();
  } finally {
    mock.timers.reset();
  }
});

test('el lifecycle no depende de eslint-disable para sus dependencias', () => {
  const source = readFileSync(resolve(here, 'DeveloperProvider.tsx'), 'utf8');
  assert.equal(source.includes('eslint-disable'), false);
});
