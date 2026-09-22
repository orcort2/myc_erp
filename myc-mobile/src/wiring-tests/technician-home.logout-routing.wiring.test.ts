import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import ts from 'typescript';

/**
 * Cierre UX post-BIOMETRIC-2: cerrar sesión debe regresar directo a login
 * (que muestra Face ID/Touch ID/Huella si el enrolamiento sigue vigente),
 * nunca a la pantalla pública retirada del flujo de entrada.
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

function harness(logout: () => Promise<void>) {
  const navigations: string[] = [];
  const slots: unknown[] = [];
  let cursor = 0;
  const jsx = (type: unknown, props: unknown) => ({ type, props });
  const authContext = {
    authorizedFetch: async () => new Response(null, { status: 200 }),
    biometricProfile: null,
    disableBiometric: async () => undefined,
    isLoading: false,
    user: {
      id: 1, email: 'staff@myc.example.com', full_name: 'Staff', is_active: true,
      permissions: [], actor_type: 'internal' as const, client_id: null, membership_id: null,
    },
    logout,
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
      ActivityIndicator: 'ActivityIndicator', Alert: { alert: () => undefined }, Pressable: 'Pressable',
      ScrollView: 'ScrollView', Text: 'Text', View: 'View',
      StyleSheet: { create: (styles: unknown) => styles },
    },
    'react-native-safe-area-context': { SafeAreaView: 'SafeAreaView' },
    'expo-router': { Redirect: 'Redirect', router: { push: () => undefined, replace: (path: string) => { navigations.push(path); } } },
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
  return { render, navigations };
}

test('cerrar sesión navega a /(auth)/login, nunca a /(public)', async () => {
  let logoutCalled = false;
  const app = harness(async () => { logoutCalled = true; });
  const tree = app.render();
  const button = pressableByText(tree, 'Cerrar sesión')!;
  await (button.props!.onPress as () => Promise<void>)();
  assert.ok(logoutCalled);
  assert.deepEqual(app.navigations, ['/(auth)/login']);
  assert.ok(!app.navigations.includes('/(public)'));
});
