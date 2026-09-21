import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import ts from 'typescript';

/**
 * P1-1: the enrollment modal must never be torn down by an immediate
 * navigation -- `submit()` may only navigate once the user has decided
 * (Activar/Ahora no). Executes the real login.tsx source; only its
 * dependencies (AuthProvider, biometric-auth service, expo-router,
 * react-native) are mocked, same convention as LabTechnicalCapture's tests.
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
function inputByPlaceholder(tree: unknown, placeholder: string): Node | undefined {
  return flatten(tree).find((node) => node.type === 'TextInput' && node.props?.placeholder === placeholder);
}

type AlertCall = { title: string; message?: string; buttons?: { text: string; onPress?: () => void }[] };

type AuthMock = {
  biometricProfile?: { user_id: number; email: string; full_name: string; biometric_label: string } | null;
  biometricAvailable?: boolean;
  login?: (email: string, password: string) => Promise<unknown>;
  biometricLogin?: () => Promise<unknown>;
  enableBiometric?: () => Promise<void>;
};

function harness(
  auth: AuthMock = {},
  availability: { available: boolean; enrolled: boolean } = { available: false, enrolled: false },
) {
  const navigations: string[] = [];
  const alerts: AlertCall[] = [];
  const slots: unknown[] = [];
  let cursor = 0;
  const jsx = (type: unknown, props: unknown) => ({ type, props });
  const authContext = {
    biometricProfile: auth.biometricProfile ?? null,
    biometricAvailable: auth.biometricAvailable ?? false,
    login: auth.login ?? (async () => ({ id: 1, email: 'user@example.com' })),
    biometricLogin: auth.biometricLogin ?? (async () => { throw new Error('not used in this test'); }),
    enableBiometric: auth.enableBiometric ?? (async () => undefined),
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
      ActivityIndicator: 'ActivityIndicator', Image: 'Image', KeyboardAvoidingView: 'KeyboardAvoidingView',
      Modal: 'Modal', Pressable: 'Pressable', ScrollView: 'ScrollView', Text: 'Text', TextInput: 'TextInput', View: 'View',
      Platform: { OS: 'ios' },
      StyleSheet: { create: (styles: unknown) => styles },
      Alert: {
        alert: (title: string, message?: string, buttons?: { text: string; onPress?: () => void }[]) => {
          alerts.push({ title, message, buttons });
        },
      },
    },
    'react-native-safe-area-context': { SafeAreaView: 'SafeAreaView' },
    'expo-constants': { default: { expoConfig: { version: '1.0' } } },
    'expo-router': { router: { replace: (path: string) => { navigations.push(path); } } },
    '@/src/auth/AuthProvider': { useAuth: () => authContext },
    '@/src/services/biometric-auth': {
      getBiometricAvailability: async () => ({
        available: availability.available, enrolled: availability.enrolled, type: 'face_id', label: 'Face ID',
      }),
    },
  };
  const require_ = (name: string): unknown => {
    if (name in ports) return ports[name];
    if (/\.(png|jpe?g)$/.test(name)) return 0;
    throw new Error(`unexpected import in login.tsx test: ${name}`);
  };
  const source = readFileSync(resolve(here, '../../app/(auth)/login.tsx'), 'utf8');
  const javascript = ts.transpileModule(source, { compilerOptions: {
    target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX,
  } }).outputText;
  const exports: Record<string, unknown> = {};
  new Function('require', 'exports', javascript)(require_, exports);
  const Screen = exports.default as () => unknown;
  const render = () => { cursor = 0; return Screen(); };
  return { render, navigations, alerts };
}

function fillCredentials(app: ReturnType<typeof harness>) {
  let tree = app.render();
  (inputByPlaceholder(tree, 'Correo electrónico')!.props!.onChangeText as (v: string) => void)('user@example.com');
  tree = app.render();
  (inputByPlaceholder(tree, 'Contraseña')!.props!.onChangeText as (v: string) => void)('secret');
  return app.render();
}

test('login password sin biometría disponible navega directo a Home', async () => {
  const app = harness({}, { available: false, enrolled: false });
  const tree = fillCredentials(app);
  const submit = pressableByText(tree, 'Iniciar sesión')!;
  await (submit.props!.onPress as () => Promise<void>)();
  assert.deepEqual(app.navigations, ['/(technician)']);
});

test('login password con biometría disponible NO navega de inmediato y muestra el modal', async () => {
  const app = harness({}, { available: true, enrolled: true });
  const tree = fillCredentials(app);
  const submit = pressableByText(tree, 'Iniciar sesión')!;
  await (submit.props!.onPress as () => Promise<void>)();
  assert.deepEqual(app.navigations, []);
  const modal = flatten(app.render()).find((node) => node.type === 'Modal');
  assert.equal(modal?.props?.visible, true);
});

test('"Ahora no" cierra el modal y navega a Home', async () => {
  const app = harness({}, { available: true, enrolled: true });
  let tree = fillCredentials(app);
  await (pressableByText(tree, 'Iniciar sesión')!.props!.onPress as () => Promise<void>)();
  tree = app.render();
  const dismiss = pressableByText(tree, 'Ahora no')!;
  (dismiss.props!.onPress as () => void)();
  assert.deepEqual(app.navigations, ['/(technician)']);
  const modal = flatten(app.render()).find((node) => node.type === 'Modal');
  assert.equal(modal?.props?.visible, false);
});

test('"Activar" llama enableBiometric y navega a Home tras éxito', async () => {
  let enableCalled = false;
  const app = harness({ enableBiometric: async () => { enableCalled = true; } }, { available: true, enrolled: true });
  let tree = fillCredentials(app);
  await (pressableByText(tree, 'Iniciar sesión')!.props!.onPress as () => Promise<void>)();
  tree = app.render();
  const activar = pressableByText(tree, 'Activar')!;
  await (activar.props!.onPress as () => Promise<void>)();
  assert.ok(enableCalled);
  assert.deepEqual(app.navigations, ['/(technician)']);
  const modal = flatten(app.render()).find((node) => node.type === 'Modal');
  assert.equal(modal?.props?.visible, false);
});

test('"Activar" fallido conserva la sesión y ofrece una salida clara a Home', async () => {
  const app = harness(
    { enableBiometric: async () => { throw new Error('No fue posible validar tu biometría'); } },
    { available: true, enrolled: true },
  );
  let tree = fillCredentials(app);
  await (pressableByText(tree, 'Iniciar sesión')!.props!.onPress as () => Promise<void>)();
  tree = app.render();
  await (pressableByText(tree, 'Activar')!.props!.onPress as () => Promise<void>)();

  // Never left stuck: an Alert with an explicit exit was shown, and taking
  // it navigates Home without ever having lost the password session (this
  // harness's mocked `login` always "succeeds"; nothing here ever logs out).
  assert.equal(app.alerts.length, 1);
  assert.deepEqual(app.navigations, []);
  const exit = app.alerts[0].buttons?.find((button) => button.text === 'Continuar sin biometría');
  assert.ok(exit);
  exit!.onPress?.();
  assert.deepEqual(app.navigations, ['/(technician)']);
});
