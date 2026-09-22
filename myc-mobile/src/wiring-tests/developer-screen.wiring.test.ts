import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import ts from 'typescript';

/**
 * DEV-0: the Developer screen itself -- locked/unlocked states and the
 * 60-second expiration warning. Executes the real
 * app/(technician)/developer.tsx source; only its dependencies
 * (AuthProvider, DeveloperProvider, expo-router, react-native) are mocked.
 */
const here = dirname(fileURLToPath(import.meta.url));

type Node = { type?: unknown; props?: Record<string, unknown> };
function flatten(tree: unknown): Node[] {
  if (Array.isArray(tree)) return tree.flatMap(flatten);
  if (!tree || typeof tree !== 'object') return [];
  const node = tree as Node;
  return [node, ...flatten(node.props?.children)];
}
function pressableByText(tree: unknown, text: string): Node | undefined {
  return flatten(tree).find((node) => node.type === 'Pressable'
    && flatten(node.props?.children).some((child) => child.type === 'Text' && child.props?.children === text));
}
function textContent(node: Node): string | null {
  const children = node.props?.children;
  if (typeof children === 'string' || typeof children === 'number') return String(children);
  if (Array.isArray(children) && children.every((part) => typeof part === 'string' || typeof part === 'number')) {
    return children.join('');
  }
  return null;
}
function textExists(tree: unknown, matcher: string | RegExp): boolean {
  return flatten(tree).some((node) => {
    if (node.type !== 'Text') return false;
    const content = textContent(node);
    if (content === null) return false;
    return typeof matcher === 'string' ? content === matcher : matcher.test(content);
  });
}

type AlertButton = { text: string; style?: string; onPress?: () => void | Promise<void> };
type AlertCall = { title: string; message?: string; buttons?: AlertButton[] };

type DeveloperMock = {
  isDeveloperAvailable?: boolean;
  isDeveloperUnlocked?: boolean;
  remainingSeconds?: number | null;
  showExpirationWarning?: boolean;
  unlockDeveloper?: () => Promise<void>;
  lockDeveloper?: () => Promise<void>;
  dismissExpirationWarning?: () => void;
  refreshDeveloperStatus?: () => Promise<void>;
};

function harness(developer: DeveloperMock = {}, user: unknown = {
  id: 1, email: 'dev@myc.example.com', full_name: 'Dev', is_active: true,
  permissions: ['developer.access'], actor_type: 'internal', client_id: null, membership_id: null,
}) {
  const alerts: AlertCall[] = [];
  const slots: unknown[] = [];
  const effectSlots: { deps: unknown[] | undefined }[] = [];
  let cursor = 0;
  let effectCursor = 0;

  function shallowEqual(a: unknown[] | undefined, b: unknown[] | undefined): boolean {
    if (a === b) return true;
    if (!a || !b || a.length !== b.length) return false;
    return a.every((value, index) => Object.is(value, b[index]));
  }

  const developerContext = {
    isDeveloperAvailable: true,
    isDeveloperUnlocked: false,
    remainingSeconds: null,
    showExpirationWarning: false,
    unlockDeveloper: async () => undefined,
    lockDeveloper: async () => undefined,
    dismissExpirationWarning: () => undefined,
    refreshDeveloperStatus: async () => undefined,
    ...developer,
  };

  const jsx = (type: unknown, props: unknown) => ({ type, props });
  const ports: Record<string, unknown> = {
    'react/jsx-runtime': { jsx, jsxs: jsx, Fragment: 'Fragment' },
    react: {
      useState: (initial: unknown) => {
        const index = cursor++;
        if (!(index in slots)) slots[index] = typeof initial === 'function' ? (initial as () => unknown)() : initial;
        return [slots[index], (value: unknown) => {
          slots[index] = typeof value === 'function' ? (value as (prev: unknown) => unknown)(slots[index]) : value;
        }];
      },
      useEffect: (fn: () => void, deps?: unknown[]) => {
        const index = effectCursor++;
        const previous = effectSlots[index];
        if (!previous || !shallowEqual(previous.deps, deps)) {
          effectSlots[index] = { deps };
          fn();
        }
      },
    },
    'react-native': {
      ActivityIndicator: 'ActivityIndicator', Pressable: 'Pressable', ScrollView: 'ScrollView', Text: 'Text', View: 'View',
      StyleSheet: { create: (styles: unknown) => styles },
      Alert: {
        alert: (title: string, message?: string, buttons?: AlertButton[]) => { alerts.push({ title, message, buttons }); },
      },
    },
    'react-native-safe-area-context': { SafeAreaView: 'SafeAreaView' },
    'expo-router': { Redirect: 'Redirect' },
    '@/src/auth/AuthProvider': { useAuth: () => ({ user, isLoading: false }) },
    '@/src/auth/DeveloperProvider': { useDeveloper: () => developerContext },
  };
  const require_ = (name: string): unknown => {
    if (name in ports) return ports[name];
    throw new Error(`unexpected import in developer.tsx test: ${name}`);
  };
  const source = readFileSync(resolve(here, '../../app/(technician)/developer.tsx'), 'utf8');
  const javascript = ts.transpileModule(source, { compilerOptions: {
    target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX,
  } }).outputText;
  const exports: Record<string, unknown> = {};
  new Function('require', 'exports', javascript)(require_, exports);
  const Screen = exports.default as () => unknown;
  const render = () => { cursor = 0; effectCursor = 0; return Screen(); };
  return { render, alerts, developerContext };
}

test('locked: muestra "Developer / Acceso protegido" y el botón de desbloqueo', () => {
  const app = harness({ isDeveloperUnlocked: false });
  const tree = app.render();
  assert.ok(textExists(tree, 'Developer'));
  assert.ok(textExists(tree, 'Acceso protegido'));
  assert.ok(pressableByText(tree, 'Desbloquear con biometría'));
  assert.equal(pressableByText(tree, 'Developer Center'), undefined);
});

test('tocar "Desbloquear con biometría" llama unlockDeveloper', async () => {
  let unlockCalled = false;
  const app = harness({ isDeveloperUnlocked: false, unlockDeveloper: async () => { unlockCalled = true; } });
  const tree = app.render();
  const button = pressableByText(tree, 'Desbloquear con biometría')!;
  await (button.props!.onPress as () => Promise<void>)();
  assert.equal(unlockCalled, true);
});

test('un fallo al desbloquear muestra un error explícito sin romper la pantalla', async () => {
  const app = harness({ isDeveloperUnlocked: false, unlockDeveloper: async () => { throw new Error('Credencial biométrica inválida'); } });
  const tree = app.render();
  const button = pressableByText(tree, 'Desbloquear con biometría')!;
  await (button.props!.onPress as () => Promise<void>)();
  const after = app.render();
  assert.ok(textExists(after, 'Credencial biométrica inválida'));
});

test('unlocked: muestra Developer Center, el countdown y las tarjetas Próximamente', () => {
  const app = harness({ isDeveloperUnlocked: true, remainingSeconds: 574 });
  const tree = app.render();
  assert.ok(textExists(tree, 'Developer Center'));
  assert.ok(textExists(tree, /09:34 restantes/));
  for (const tool of ['Base de datos', 'Terminal', 'Logs', 'Servicios', 'Git']) {
    assert.ok(textExists(tree, tool), `esperaba la tarjeta ${tool}`);
  }
  assert.equal(flatten(tree).filter((node) => node.type === 'Text' && node.props?.children === 'Próximamente').length, 5);
});

test('unlocked: "Bloquear Developer" llama lockDeveloper', async () => {
  let lockCalled = false;
  const app = harness({ isDeveloperUnlocked: true, remainingSeconds: 100, lockDeveloper: async () => { lockCalled = true; } });
  const tree = app.render();
  const button = pressableByText(tree, 'Bloquear Developer')!;
  await (button.props!.onPress as () => Promise<void>)();
  assert.equal(lockCalled, true);
});

test('el warning de expiración muestra un Alert con "Extender con biometría" y "Bloquear ahora"', () => {
  const app = harness({ isDeveloperUnlocked: true, remainingSeconds: 45, showExpirationWarning: true });
  app.render();
  assert.equal(app.alerts.length, 1);
  assert.equal(app.alerts[0].title, 'Tu sesión Developer está por finalizar');
  const labels = app.alerts[0].buttons?.map((button) => button.text);
  assert.deepEqual(labels, ['Bloquear ahora', 'Extender con biometría']);
});

test('sin warning, nunca se muestra el Alert', () => {
  const app = harness({ isDeveloperUnlocked: true, remainingSeconds: 300, showExpirationWarning: false });
  app.render();
  assert.equal(app.alerts.length, 0);
});

test('"Bloquear ahora" del warning descarta el aviso y bloquea', async () => {
  let lockCalled = false;
  let dismissed = false;
  const app = harness({
    isDeveloperUnlocked: true, remainingSeconds: 45, showExpirationWarning: true,
    lockDeveloper: async () => { lockCalled = true; },
    dismissExpirationWarning: () => { dismissed = true; },
  });
  app.render();
  const button = app.alerts[0].buttons!.find((entry) => entry.text === 'Bloquear ahora')!;
  await button.onPress?.();
  assert.equal(dismissed, true);
  assert.equal(lockCalled, true);
});

test('"Extender con biometría" del warning descarta el aviso y desbloquea de nuevo', async () => {
  let unlockCalled = false;
  let dismissed = false;
  const app = harness({
    isDeveloperUnlocked: true, remainingSeconds: 45, showExpirationWarning: true,
    unlockDeveloper: async () => { unlockCalled = true; },
    dismissExpirationWarning: () => { dismissed = true; },
  });
  app.render();
  const button = app.alerts[0].buttons!.find((entry) => entry.text === 'Extender con biometría')!;
  await button.onPress?.();
  assert.equal(dismissed, true);
  assert.equal(unlockCalled, true);
});

test('sin developer.access, la pantalla no se muestra (redirige a Home)', () => {
  const app = harness({ isDeveloperAvailable: false });
  const tree = app.render();
  assert.equal((tree as Node).type, 'Redirect');
  assert.equal((tree as Node).props?.href, '/(technician)');
});

test('sin usuario, redirige a login', () => {
  const app = harness({}, null);
  const tree = app.render();
  assert.equal((tree as Node).type, 'Redirect');
  assert.equal((tree as Node).props?.href, '/(auth)/login');
});

test('entrar al Developer Center reconcilia el estado una vez por montaje, nunca por render', () => {
  let reconciles = 0;
  const refreshDeveloperStatus = async () => { reconciles += 1; };
  const app = harness({ isDeveloperUnlocked: true, remainingSeconds: 300, refreshDeveloperStatus });
  app.render();
  app.render();
  app.render();
  assert.equal(reconciles, 1);
});

test('la etiqueta biométrica es genérica, nunca "Face ID" rígido', () => {
  const source = readFileSync(resolve(here, '../../app/(technician)/developer.tsx'), 'utf8');
  assert.equal(/'[^']*Face ID[^']*'/.test(source.replace(/\/\/.*$/gm, '')), false);
});
