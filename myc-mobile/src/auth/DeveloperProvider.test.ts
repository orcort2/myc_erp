import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { mock, test } from 'node:test';
import { fileURLToPath } from 'node:url';
import ts from 'typescript';

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
    '@/src/auth/AuthProvider': { useAuth: () => authState },
    '@/src/permissions/permissions': {
      hasPermission: (permissions: string[], permission: string) =>
        permissions.includes('*') || permissions.includes(permission),
    },
    '@/src/services/developer.service': {
      openDeveloperSession: async (accessToken: string, credential: string) => {
        calls.open.push({ accessToken, credential });
        const next = openSequence.shift();
        if (!next) throw new Error('no queued open() response in test');
        return next;
      },
      getDeveloperSessionStatus: async (accessToken: string, developerToken: string) => {
        calls.status.push({ accessToken, developerToken });
        return { active: false, expires_at: null, remaining_seconds: null, user_id: null, device_id: null };
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

  return {
    render,
    calls,
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
    '@/src/permissions/permissions',
    '@/src/services/developer.service',
    '@/src/storage/biometric-storage',
    'react',
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
