import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import ts from 'typescript';

/**
 * P2: disabling biometric access must ask for confirmation first and handle
 * a local/SecureStore failure without breaking the active session. Executes
 * the real technician/index.tsx source; only its dependencies are mocked.
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

type AlertButton = { text: string; style?: string; onPress?: () => void | Promise<void> };
type AlertCall = { title: string; message?: string; buttons?: AlertButton[] };

function harness(disableBiometric: () => Promise<void>) {
  const alerts: AlertCall[] = [];
  const slots: unknown[] = [];
  let cursor = 0;
  const jsx = (type: unknown, props: unknown) => ({ type, props });
  const authContext = {
    authorizedFetch: async () => new Response(null, { status: 200 }),
    biometricProfile: { user_id: 1, email: 'staff@myc.example.com', full_name: 'Staff', biometric_label: 'Face ID' },
    disableBiometric,
    isLoading: false,
    user: {
      id: 1, email: 'staff@myc.example.com', full_name: 'Staff', is_active: true,
      permissions: [], actor_type: 'internal' as const, client_id: null, membership_id: null,
    },
    logout: async () => undefined,
  };
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
      useEffect: () => undefined,
    },
    'react-native': {
      ActivityIndicator: 'ActivityIndicator', Pressable: 'Pressable', ScrollView: 'ScrollView', Text: 'Text', View: 'View',
      StyleSheet: { create: (styles: unknown) => styles },
      Alert: {
        alert: (title: string, message?: string, buttons?: AlertButton[]) => { alerts.push({ title, message, buttons }); },
      },
    },
    'react-native-safe-area-context': { SafeAreaView: 'SafeAreaView' },
    'expo-router': { Redirect: 'Redirect', router: { push: () => undefined, replace: () => undefined } },
    '@/src/auth/AuthProvider': { useAuth: () => authContext },
    '@/src/communications/CommunicationsProvider': { useCommunications: () => ({ unreadCount: 0 }) },
    '@/src/notifications/NotificationSyncProvider': { useNotificationSync: () => ({ unreadCount: 0 }) },
    '@/src/api/client': { apiUrl: (path: string) => path },
    '@/src/permissions/mobile-capabilities': {
      deriveMobileCapabilities: () => ({
        canCaptureFieldSheets: false, canClaimWorkOrderGroupRequests: false, canCreateWorkOrders: false,
        canReadLabClients: false, canReadTickets: false, canReadWorkOrderGroupRequests: false,
        canReadWorkOrders: false, canReviewTickets: false, canUseCommunications: false,
      }),
    },
    '@/src/requests/request-inbox': { actionableRequestCount: () => 0 },
  };
  const require_ = (name: string): unknown => {
    if (name in ports) return ports[name];
    throw new Error(`unexpected import in technician/index.tsx test: ${name}`);
  };
  const source = readFileSync(resolve(here, '../../app/(technician)/index.tsx'), 'utf8');
  const javascript = ts.transpileModule(source, { compilerOptions: {
    target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX,
  } }).outputText;
  const exports: Record<string, unknown> = {};
  new Function('require', 'exports', javascript)(require_, exports);
  const Screen = exports.default as () => unknown;
  const render = () => { cursor = 0; return Screen(); };
  return { render, alerts };
}

test('desactivar biometría exige confirmación antes de ejecutar', async () => {
  let disableCalled = false;
  const app = harness(async () => { disableCalled = true; });
  const tree = app.render();
  const button = pressableByText(tree, 'Desactivar acceso biométrico en este dispositivo')!;
  (button.props!.onPress as () => void)();
  assert.equal(disableCalled, false);
  assert.equal(app.alerts.length, 1);
  assert.equal(app.alerts[0].title, 'Desactivar acceso biométrico');
  assert.match(app.alerts[0].message ?? '', /correo y contraseña/);
});

test('cancelar la confirmación no llama disableBiometric', async () => {
  let disableCalled = false;
  const app = harness(async () => { disableCalled = true; });
  const tree = app.render();
  const button = pressableByText(tree, 'Desactivar acceso biométrico en este dispositivo')!;
  (button.props!.onPress as () => void)();
  const cancel = app.alerts[0].buttons?.find((b) => b.text === 'Cancelar');
  assert.ok(cancel);
  await cancel!.onPress?.();
  assert.equal(disableCalled, false);
});

test('confirmar la desactivación llama disableBiometric', async () => {
  let disableCalled = false;
  const app = harness(async () => { disableCalled = true; });
  const tree = app.render();
  const button = pressableByText(tree, 'Desactivar acceso biométrico en este dispositivo')!;
  (button.props!.onPress as () => void)();
  const confirm = app.alerts[0].buttons?.find((b) => b.text === 'Desactivar');
  assert.ok(confirm);
  await confirm!.onPress?.();
  assert.equal(disableCalled, true);
});

test('un fallo local al desactivar biometría muestra un manejo de error explícito', async () => {
  const app = harness(async () => { throw new Error('SecureStore no disponible'); });
  const tree = app.render();
  const button = pressableByText(tree, 'Desactivar acceso biométrico en este dispositivo')!;
  (button.props!.onPress as () => void)();
  const confirm = app.alerts[0].buttons?.find((b) => b.text === 'Desactivar');
  await confirm!.onPress?.();
  assert.equal(app.alerts.length, 2);
  assert.equal(app.alerts[1].title, 'No fue posible desactivar el acceso biométrico.');
});
