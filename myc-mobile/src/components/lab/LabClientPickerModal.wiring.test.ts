import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import test, { mock } from 'node:test';
import { fileURLToPath } from 'node:url';
import ts from 'typescript';

import * as selectorState from '../../services/lab-client-selector';
import { generalWithLabClient } from '../../services/lab-work-order-client';
import type { GeneralData, LabClient } from '../../types/lab-work-order';

/**
 * Selector modal de cliente de OT LAB (C1–C19).
 *
 * Ejecuta el código real de LabWorkOrderClientField, LabClientPickerModal y
 * LabClientSelector sobre un mini-runtime de hooks (useState/useEffect con
 * limpieza, re-render y desmontaje) y puertos RN simulados. Prueba estados,
 * handlers y cableado; NO mide layout, SafeArea ni teclado nativo: eso se
 * valida en simulador/dispositivo.
 */

const here = dirname(fileURLToPath(import.meta.url));
const read = (relative: string) => readFileSync(resolve(here, relative), 'utf8');

type Element = { type: unknown; props: Record<string, any> };
type Host = { type: string; props: Record<string, any> };
type Client = selectorState.LabClientOption;

function client(id: number, company: string, extra: Partial<Client> = {}): Client {
  return { id, company, address: `Calle ${id}`, attention: `Contacto ${id}`, postal_code: null, city: null, state: null, ...extra };
}

function deferred<T>() {
  let resolvePromise!: (value: T) => void;
  let rejectPromise!: (error: Error) => void;
  const promise = new Promise<T>((ok, fail) => { resolvePromise = ok; rejectPromise = fail; });
  return { promise, resolve: resolvePromise, reject: rejectPromise };
}

const settle = () => new Promise<void>((done) => setImmediate(done));

function createRenderer() {
  class Instance { slots: any[] = []; effects = new Set<number>(); cursor = 0; }
  const instances = new Map<string, Instance>();
  let current: Instance | null = null;
  let visited = new Set<string>();
  let dirty = false;
  let pending: { inst: Instance; index: number; fn: () => unknown }[] = [];

  const react = {
    useState(initial: unknown) {
      const inst = current!;
      const index = inst.cursor++;
      if (!(index in inst.slots)) inst.slots[index] = typeof initial === 'function' ? (initial as () => unknown)() : initial;
      const set = (value: unknown) => {
        const next = typeof value === 'function' ? (value as (prev: unknown) => unknown)(inst.slots[index]) : value;
        if (!Object.is(next, inst.slots[index])) { inst.slots[index] = next; dirty = true; }
      };
      return [inst.slots[index], set];
    },
    useEffect(fn: () => unknown, deps?: unknown[]) {
      const inst = current!;
      const index = inst.cursor++;
      const prev = inst.slots[index] as { deps?: unknown[]; cleanup?: () => void } | undefined;
      const changed = !prev || !deps || !prev.deps || deps.length !== prev.deps.length
        || deps.some((dep, k) => !Object.is(dep, prev.deps![k]));
      if (changed) {
        inst.slots[index] = { deps, cleanup: prev?.cleanup };
        inst.effects.add(index);
        pending.push({ inst, index, fn });
      }
    },
    useRef(value: unknown) {
      const inst = current!;
      const index = inst.cursor++;
      if (!(index in inst.slots)) inst.slots[index] = { current: value };
      return inst.slots[index];
    },
    useCallback: (fn: unknown) => fn,
    useMemo: (fn: () => unknown) => fn(),
  };

  function expand(node: unknown, path: string): unknown {
    if (Array.isArray(node)) return node.map((child, i) => expand(child, `${path}.${i}`));
    if (node == null || typeof node !== 'object') return node;
    const { type, props } = node as Element;
    if (typeof type === 'function') {
      const key = `${path}>${type.name}`;
      let inst = instances.get(key);
      if (!inst) { inst = new Instance(); instances.set(key, inst); }
      visited.add(key);
      const parent = current;
      current = inst;
      inst.cursor = 0;
      let output: unknown;
      try { output = (type as (p: unknown) => unknown)(props); } finally { current = parent; }
      return expand(output, key);
    }
    return { type, props: { ...props, children: expand(props?.children, `${path}/${String(type)}`) } };
  }

  function cleanupInstance(inst: Instance) {
    for (const index of inst.effects) inst.slots[index]?.cleanup?.();
  }

  let tree: unknown = null;
  function render(root: () => Element) {
    for (let pass = 0; pass < 30; pass++) {
      dirty = false;
      visited = new Set();
      pending = [];
      tree = expand(root(), 'root');
      for (const [key, inst] of instances) {
        if (!visited.has(key)) { cleanupInstance(inst); instances.delete(key); }
      }
      for (const effect of pending) {
        const slot = effect.inst.slots[effect.index];
        slot.cleanup?.();
        const cleanup = effect.fn();
        slot.cleanup = typeof cleanup === 'function' ? cleanup : undefined;
      }
      if (!dirty) return tree;
    }
    throw new Error('render no converge');
  }

  return { react, render };
}

function flatten(node: unknown): Host[] {
  if (Array.isArray(node)) return node.flatMap(flatten);
  if (node == null || typeof node !== 'object') return [];
  const host = node as Host;
  return [host, ...flatten(host.props?.children)];
}

function textOf(node: unknown): string {
  if (Array.isArray(node)) return node.map(textOf).join('');
  if (typeof node === 'string' || typeof node === 'number') return String(node);
  if (node == null || typeof node !== 'object') return '';
  return textOf((node as Host).props?.children);
}

function mount(root: (react: ReturnType<typeof createRenderer>['react'], jsx: (type: unknown, props: Record<string, any>) => Element, exports: Record<string, any>) => () => Element) {
  const renderer = createRenderer();
  const jsx = (type: unknown, props: Record<string, any>) => ({ type, props: props ?? {} });
  const alerts: unknown[][] = [];
  const ports: Record<string, unknown> = {
    'react/jsx-runtime': { jsx, jsxs: jsx, Fragment: 'Fragment' },
    react: renderer.react,
    'react-native': {
      Alert: { alert: (...args: unknown[]) => { alerts.push(args); } },
      KeyboardAvoidingView: 'KeyboardAvoidingView',
      // Como en RN: un Modal oculto no renderiza (y por tanto desmonta) su contenido.
      Modal: function Modal(props: Record<string, any>) {
        return props.visible ? { type: 'ModalHost', props: { onRequestClose: props.onRequestClose, children: props.children } } : null;
      },
      Platform: { OS: 'ios' },
      Pressable: 'Pressable',
      ScrollView: 'ScrollView',
      StyleSheet: { create: (styles: unknown) => styles },
      Text: 'Text',
      TextInput: 'TextInput',
      View: 'View',
    },
    'react-native-safe-area-context': { SafeAreaProvider: 'SafeAreaProvider', SafeAreaView: 'SafeAreaView' },
    '@expo/vector-icons': { MaterialCommunityIcons: 'Icon' },
    '@/src/design/primitives': {
      AlertBanner: 'AlertBanner', Card: 'Card', CloseButton: 'CloseButton', EmptyState: 'EmptyState', LoadingState: 'LoadingState',
    },
    '@/src/design/tokens': { colors: { primary: '#0067a8' }, radius: {}, spacing: {} },
    '@/src/services/lab-client-selector': selectorState,
  };
  const modules = new Map<string, Record<string, any>>();
  function load(name: string): Record<string, any> {
    if (name in ports) return ports[name] as Record<string, any>;
    const match = /^@\/src\/components\/lab\/(\w+)$/.exec(name);
    assert.ok(match, `import inesperado: ${name}`);
    if (modules.has(name)) return modules.get(name)!;
    const javascript = ts.transpileModule(read(`./${match[1]}.tsx`), { compilerOptions: {
      target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX,
    } }).outputText;
    const exports: Record<string, any> = {};
    modules.set(name, exports);
    new Function('require', 'exports', javascript)(load, exports);
    return exports;
  }
  const exports = {
    ...load('@/src/components/lab/LabWorkOrderClientField'),
    ...load('@/src/components/lab/LabClientPickerModal'),
    ...load('@/src/components/lab/LabClientSelector'),
  };
  const rootElement = root(renderer.react, jsx, exports);
  let tree: unknown = renderer.render(rootElement);
  const view = {
    alerts,
    rerender() { tree = renderer.render(rootElement); },
    async flush() { await settle(); tree = renderer.render(rootElement); },
    nodes: () => flatten(tree),
    texts: () => flatten(tree).filter((node) => node.type === 'Text').map((node) => textOf(node.props.children)),
    has: (text: string) => view.texts().includes(text),
    modalOpen: () => flatten(tree).some((node) => node.type === 'ModalHost'),
    press(label: string) {
      const target = flatten(tree).find((node) => node.type === 'Pressable' && (node.props.accessibilityLabel === label || textOf(node.props.children) === label))
        ?? flatten(tree).find((node) => node.type === 'CloseButton' && node.props.label === label);
      assert.ok(target, `no hay acción "${label}"; textos: ${view.texts().join(' | ')}`);
      assert.notEqual(target.props.disabled, true, `"${label}" está deshabilitado`);
      target.props.onPress();
      view.rerender();
    },
    pressResult(company: string) {
      const row = flatten(tree).find((node) => node.type === 'Pressable' && typeof node.props.style === 'function'
        && flatten(node.props.children).some((child) => child.type === 'Text' && textOf(child.props.children) === company));
      assert.ok(row, `sin fila de resultado "${company}"`);
      row.props.onPress();
      view.rerender();
    },
    search(value: string) {
      const input = flatten(tree).find((node) => node.type === 'TextInput' && node.props.accessibilityLabel === 'Buscar cliente');
      assert.ok(input, 'no hay buscador visible');
      input.props.onChangeText(value);
      view.rerender();
    },
    searchValue: () => flatten(tree).find((node) => node.type === 'TextInput' && node.props.accessibilityLabel === 'Buscar cliente')?.props.value,
    field(label: string): Host {
      const group = flatten(tree).find((node) => node.type === 'View' && Array.isArray(node.props.children)
        && node.props.children[0]?.type === 'Text' && textOf(node.props.children[0]).replace(' *', '') === label);
      assert.ok(group, `sin campo "${label}"`);
      return group.props.children[1] as Host;
    },
    fill(label: string, value: string) { view.field(label).props.onChangeText(value); view.rerender(); },
    hasNode: (type: string) => flatten(tree).some((node) => node.type === type),
  };
  return view;
}

type Call = { path: string; init?: RequestInit; reply: ReturnType<typeof deferred<unknown>> };

function backend() {
  const calls: Call[] = [];
  const request = (path: string, init?: RequestInit) => {
    const reply = deferred<unknown>();
    calls.push({ path, init, reply });
    return reply.promise;
  };
  return { calls, request };
}

const EMPTY_GENERAL: GeneralData = {
  lab_client_id: null, reception_date: '2026-09-28', client_name: '', address: '', contact_name: '',
  contact_phone: '', contact_email: '', postal_code: '', city: '', state_name: '', purchase_order: '', notes: '',
};

/** Formulario de OT mínimo que usa la autoridad real de mapeo (generalWithLabClient), igual que selectLabClient. */
function otForm(request: unknown, initialClient: Client | null = null) {
  const selections: Client[] = [];
  let general: GeneralData = initialClient ? generalWithLabClient(EMPTY_GENERAL, initialClient as LabClient) : EMPTY_GENERAL;
  return {
    selections,
    general: () => general,
    root: (react: any, jsx: any, exports: Record<string, any>) => {
      function OtForm() {
        const [current, setGeneral] = react.useState(general);
        general = current;
        function selectLabClient(picked: Client) {
          selections.push(picked);
          setGeneral((previous: GeneralData) => generalWithLabClient(previous, picked as LabClient));
        }
        return jsx(exports.LabWorkOrderClientField, {
          address: current.address, clientId: current.lab_client_id, clientName: current.client_name,
          onSelect: selectLabClient, request,
        });
      }
      return () => jsx(OtForm, {});
    },
  };
}

async function searchAndSettle(view: ReturnType<typeof mount>, api: ReturnType<typeof backend>, term: string, results: Client[]) {
  view.search(term);
  mock.timers.tick(300);
  view.rerender();
  const call = api.calls.at(-1)!;
  assert.equal(call.path, `/mobile/v1/technician/lab-clients?${selectorState.buildLabClientSearchQuery(term)}`);
  call.reply.resolve(results);
  await view.flush();
}

const ACME = client(1, 'Acme', { postal_code: '76000', city: 'Querétaro', state: 'Querétaro' });
// B con el mínimo del contrato: address/attention vacíos, CP/ciudad/estado null.
const BETA = client(2, 'Beta Industrial', { address: '', attention: '' });

test.beforeEach(() => mock.timers.enable({ apis: ['setTimeout'] }));
test.afterEach(() => mock.timers.reset());

test('C1. sin cliente aparece "Elegir cliente" y no hay buscador inline', () => {
  const api = backend();
  const view = mount(otForm(api.request).root);
  assert.ok(view.has('Elegir cliente'));
  assert.equal(view.modalOpen(), false);
  assert.equal(view.searchValue(), undefined);
});

test('C2/C3. "Elegir cliente" abre el selector; cerrar sin elegir no toca la OT', () => {
  const api = backend();
  const form = otForm(api.request);
  const view = mount(form.root);
  view.press('Elegir cliente');
  assert.equal(view.modalOpen(), true);
  assert.ok(view.has('Seleccionar cliente'));
  assert.equal(view.searchValue(), '');
  view.press('Cerrar');
  assert.equal(view.modalOpen(), false);
  assert.equal(form.selections.length, 0);
  assert.ok(view.has('Elegir cliente'));
});

test('C4/C5/C6/C7. elegir un cliente llama una sola vez a la autoridad, cierra y muestra la tarjeta con "Cambiar cliente"', async () => {
  const api = backend();
  const form = otForm(api.request);
  const view = mount(form.root);
  view.press('Elegir cliente');
  await searchAndSettle(view, api, 'Acme', [ACME]);
  view.pressResult('Acme');
  assert.deepEqual(form.selections, [ACME]);
  assert.equal(view.modalOpen(), false);
  assert.ok(view.has('Acme'));
  assert.ok(view.has(ACME.address));
  assert.ok(view.has('Cambiar cliente'));
  assert.equal(view.has('Elegir cliente'), false);
});

test('C8/C9. "Cambiar cliente" abre el selector sin borrar el cliente actual; cancelar lo conserva', () => {
  const api = backend();
  const form = otForm(api.request, ACME);
  const view = mount(form.root);
  view.press('Cambiar cliente');
  assert.equal(view.modalOpen(), true);
  assert.ok(view.has('Acme'), 'la tarjeta del cliente actual sigue en el formulario debajo del modal');
  view.press('Cerrar');
  assert.equal(form.selections.length, 0);
  assert.ok(view.has('Acme'));
  assert.ok(view.has('Cambiar cliente'));
});

test('C9b. el cierre por sistema (Android back / swipe) tampoco modifica la OT', () => {
  const api = backend();
  const form = otForm(api.request, ACME);
  const view = mount(form.root);
  view.press('Cambiar cliente');
  view.nodes().find((node) => node.type === 'ModalHost')!.props.onRequestClose();
  view.rerender();
  assert.equal(view.modalOpen(), false);
  assert.equal(form.selections.length, 0);
  assert.ok(view.has('Acme'));
});

test('C10. elegir otro cliente reemplaza al anterior', async () => {
  const api = backend();
  const form = otForm(api.request, ACME);
  const view = mount(form.root);
  view.press('Cambiar cliente');
  await searchAndSettle(view, api, 'Beta', [BETA]);
  view.pressResult('Beta Industrial');
  assert.deepEqual(form.selections, [BETA]);
  assert.equal(view.modalOpen(), false);
  assert.ok(view.has('Beta Industrial'));
  assert.equal(view.has('Acme'), false);
  // Sin datos híbridos: nada derivado de Acme sobrevive en la OT.
  const general = form.general();
  assert.deepEqual(
    [general.lab_client_id, general.client_name, general.address, general.contact_name, general.postal_code, general.city, general.state_name],
    [2, 'Beta Industrial', '', '', '', '', ''],
  );
});

function backFromSystem(view: ReturnType<typeof mount>) {
  view.nodes().find((node) => node.type === 'ModalHost')!.props.onRequestClose();
  view.rerender();
}

test('Back Android en búsqueda/resultados cierra el modal sin tocar la OT', async () => {
  const api = backend();
  const form = otForm(api.request, ACME);
  const view = mount(form.root);
  view.press('Cambiar cliente');
  await searchAndSettle(view, api, 'Beta', [BETA]);
  backFromSystem(view);
  assert.equal(view.modalOpen(), false);
  assert.equal(form.selections.length, 0);
  assert.equal(form.general().lab_client_id, ACME.id);
});

test('Back Android en creación cancela el alta, vuelve a búsqueda y no cierra el modal ni cambia el cliente', async () => {
  const api = backend();
  const form = otForm(api.request, ACME);
  const view = mount(form.root);
  view.press('Cambiar cliente');
  await searchAndSettle(view, api, 'Zeta', []);
  view.press('+ Crear cliente "Zeta"');
  assert.ok(view.has('Crear cliente'));
  const callsBefore = api.calls.length;
  backFromSystem(view);
  assert.equal(view.modalOpen(), true, 'el modal sigue abierto');
  assert.equal(view.has('Crear cliente'), false, 'salió del alta');
  assert.equal(view.searchValue(), 'Zeta', 'regresa a la misma búsqueda');
  assert.ok(view.has('+ Crear cliente "Zeta"'));
  assert.equal(api.calls.length, callsBefore, 'no crea nada');
  assert.equal(form.selections.length, 0);
  assert.equal(form.general().lab_client_id, ACME.id);
  assert.ok(view.has('Acme'), 'la tarjeta del cliente actual no cambia');
  backFromSystem(view);
  assert.equal(view.modalOpen(), false, 'un segundo Back, ya en búsqueda, cierra el modal');
  assert.equal(form.general().lab_client_id, ACME.id);
});

test('"Cancelar" y Back Android producen exactamente la misma transición desde el alta', async () => {
  async function exitCreate(exit: 'cancel' | 'back') {
    const api = backend();
    const view = mount(otForm(api.request, ACME).root);
    view.press('Cambiar cliente');
    await searchAndSettle(view, api, 'Zeta', []);
    view.press('+ Crear cliente "Zeta"');
    view.fill('Ciudad', 'León');
    if (exit === 'cancel') view.press('Cancelar'); else backFromSystem(view);
    const afterExit = { open: view.modalOpen(), texts: view.texts(), search: view.searchValue() };
    view.press('+ Crear cliente');
    return { ...afterExit, capturedCity: view.field('Ciudad').props.value };
  }
  const cancelled = await exitCreate('cancel');
  const backed = await exitCreate('back');
  assert.deepEqual(backed, cancelled);
  assert.equal(cancelled.open, true);
  assert.equal(cancelled.capturedCity, 'León', 'ambos conservan lo capturado del alta, como Cancelar ya hacía');
});

test('C10b. cada apertura empieza con búsqueda limpia (el contenido se desmonta al cerrar)', async () => {
  const api = backend();
  const view = mount(otForm(api.request).root);
  view.press('Elegir cliente');
  await searchAndSettle(view, api, 'Acme', [ACME]);
  view.press('Cerrar');
  view.press('Elegir cliente');
  assert.equal(view.searchValue(), '');
});

test('C11. la búsqueda conserva el debounce de 300 ms, el mínimo de 2 caracteres y el tope de 5 resultados', () => {
  const api = backend();
  const view = mount(otForm(api.request).root);
  view.press('Elegir cliente');
  view.search('A');
  mock.timers.tick(1000);
  view.rerender();
  assert.equal(api.calls.length, 0, 'un carácter nunca consulta');
  view.search('Ac');
  mock.timers.tick(200);
  view.search('Acm');
  mock.timers.tick(299);
  view.rerender();
  assert.equal(api.calls.length, 0, 'teclear dentro de la ventana reinicia el debounce');
  mock.timers.tick(1);
  view.rerender();
  assert.equal(api.calls.length, 1);
  assert.equal(api.calls[0].path, '/mobile/v1/technician/lab-clients?search=Acm&limit=5');
});

test('C12. loading, error y vacío son estados explícitos (nunca "vacío" mientras el término sigue pendiente)', async () => {
  const api = backend();
  const view = mount(otForm(api.request).root);
  view.press('Elegir cliente');
  assert.equal(view.nodes().find((node) => node.type === 'EmptyState')?.props.title, 'Buscar cliente', 'estado inicial explícito');
  view.search('Zeta');
  assert.ok(view.hasNode('LoadingState'), 'debounce pendiente = cargando, no "Sin resultados"');
  mock.timers.tick(300);
  view.rerender();
  assert.ok(view.hasNode('LoadingState'));
  api.calls[0].reply.reject(new Error('Sin conexión'));
  await view.flush();
  const banner = view.nodes().find((node) => node.type === 'AlertBanner');
  assert.equal(textOf(banner?.props.children), 'Sin conexión');
  view.search('Zetas');
  assert.equal(view.hasNode('AlertBanner'), false, 'el error pertenece al término que lo produjo');
  mock.timers.tick(300);
  view.rerender();
  api.calls[1].reply.resolve([]);
  await view.flush();
  const empty = view.nodes().find((node) => node.type === 'EmptyState');
  assert.equal(empty?.props.title, 'Sin resultados');
});

test('C13/C18. "+ Crear cliente" crea con el contrato actual, selecciona el nuevo cliente y cierra el modal', async () => {
  const api = backend();
  const form = otForm(api.request);
  const view = mount(form.root);
  view.press('Elegir cliente');
  view.press('+ Crear cliente');
  assert.ok(view.has('Crear cliente'));
  view.fill('Empresa', ' Nueva SA ');
  view.fill('Dirección', 'Av. 1');
  view.fill('Código postal', '76000');
  view.fill('Ciudad', 'Querétaro');
  view.fill('Estado', 'Qro');
  view.fill('Atención a', 'Ana');
  view.press('Guardar');
  const call = api.calls.at(-1)!;
  assert.equal(call.path, '/mobile/v1/technician/lab-clients');
  assert.equal(call.init?.method, 'POST');
  assert.deepEqual(JSON.parse(String(call.init?.body)), {
    company: 'Nueva SA', address: 'Av. 1', attention: 'Ana', postal_code: '76000', city: 'Querétaro', state: 'Qro',
  });
  const created = client(50, 'Nueva SA');
  call.reply.resolve(created);
  await view.flush();
  assert.deepEqual(form.selections, [created]);
  assert.equal(view.modalOpen(), false);
  assert.ok(view.has('Nueva SA'));
});

test('C14/C15. sin coincidencias se ofrece crear con el término; precarga Empresa sin crear nada', async () => {
  const api = backend();
  const view = mount(otForm(api.request).root);
  view.press('Elegir cliente');
  view.search('Zeta Labs');
  assert.equal(view.has('+ Crear cliente "Zeta Labs"'), false, 'no se ofrece antes de que responda el backend');
  mock.timers.tick(300);
  view.rerender();
  api.calls[0].reply.resolve([]);
  await view.flush();
  assert.ok(view.has('+ Crear cliente "Zeta Labs"'));
  const callsBefore = api.calls.length;
  view.press('+ Crear cliente "Zeta Labs"');
  assert.equal(view.field('Empresa').props.value, 'Zeta Labs');
  assert.equal(view.field('Dirección').props.value, '');
  assert.equal(api.calls.length, callsBefore, 'abrir la creación no crea nada');
});

test('C14b. con coincidencias no aparece la creación contextual', async () => {
  const api = backend();
  const view = mount(otForm(api.request).root);
  view.press('Elegir cliente');
  await searchAndSettle(view, api, 'Acme', [ACME]);
  assert.equal(view.texts().some((text) => text.startsWith('+ Crear cliente "')), false);
  assert.ok(view.has('+ Crear cliente'));
});

test('C16. cancelar la creación regresa al selector (mismo término) sin cerrar el modal ni la OT', async () => {
  const api = backend();
  const form = otForm(api.request);
  const view = mount(form.root);
  view.press('Elegir cliente');
  await searchAndSettle(view, api, 'Zeta', []);
  view.press('+ Crear cliente "Zeta"');
  view.press('Cancelar');
  assert.equal(view.modalOpen(), true);
  assert.equal(view.searchValue(), 'Zeta');
  assert.ok(view.has('+ Crear cliente "Zeta"'));
  assert.equal(form.selections.length, 0);
});

test('C17. un error de creación conserva lo capturado y no selecciona ni cierra', async () => {
  const api = backend();
  const form = otForm(api.request);
  const view = mount(form.root);
  view.press('Elegir cliente');
  await searchAndSettle(view, api, 'Zeta', []);
  view.press('+ Crear cliente "Zeta"');
  view.fill('Ciudad', 'León');
  view.press('Guardar');
  api.calls.at(-1)!.reply.reject(new Error('Cliente duplicado'));
  await view.flush();
  assert.equal(view.alerts.length, 1);
  assert.equal(view.alerts[0][1], 'Cliente duplicado');
  assert.equal(view.modalOpen(), true);
  assert.equal(view.field('Empresa').props.value, 'Zeta');
  assert.equal(view.field('Ciudad').props.value, 'León');
  assert.equal(form.selections.length, 0);
});

test('C19. consumidor de equipos: el selector sigue siendo inline (sin Modal) y entrega el cliente a su propio onSelect', async () => {
  const api = backend();
  const picked: Client[] = [];
  const view = mount((_react, jsx, exports) => () => jsx(exports.LabClientSelector, { request: api.request, onSelect: (item: Client) => picked.push(item) }));
  assert.equal(view.modalOpen(), false);
  assert.ok(view.searchValue() !== undefined, 'el buscador se muestra directamente, sin paso intermedio');
  await searchAndSettle(view, api, 'Beta', [BETA]);
  view.pressResult('Beta Industrial');
  assert.deepEqual(picked, [BETA]);

  const equipmentForm = read('./LabEquipmentForm.tsx');
  assert.match(equipmentForm, /<LabClientSelector\s+request=\{request\}\s+onSelect=\{\(client: LabClient\) =>\s+setDocumentaryClient\(selectFinalClient\(client\)\)\s+\}\s+\/>/);
  assert.doesNotMatch(equipmentForm, /LabClientPickerModal|LabWorkOrderClientField/);
  assert.doesNotMatch(read('./LabClientSelector.tsx'), /\bModal\b/);
});

test('cableado OT: work-orders usa el campo modal con selectLabClient y ya no limpia el cliente al cambiarlo', () => {
  const source = read('../../../app/(technician)/work-orders.tsx');
  assert.match(source, /function selectLabClient\(client: LabClient\) \{\s*setGeneral\(\(current\) => generalWithLabClient\(current, client\)\);\s*\}/);
  assert.match(source, /<LabWorkOrderClientField\s+address=\{general\.address\}\s+clientId=\{general\.lab_client_id\}\s+clientName=\{general\.client_name\}\s+onSelect=\{selectLabClient\}\s+request=\{request\}\s+\/>/);
  assert.doesNotMatch(source, /<LabClientSelector/);
  assert.doesNotMatch(source, /lab_client_id: null, client_name: ''/);
  const modal = read('./LabClientPickerModal.tsx');
  assert.doesNotMatch(modal, /lab_client_id|client_name|postal_code|state_name/);
});

test('cableado modal: SafeArea propio y una sola autoridad de teclado por plataforma', () => {
  const modal = read('./LabClientPickerModal.tsx');
  assert.match(modal, /<Modal animationType="slide" onRequestClose=\{requestClose\} visible=\{visible\}>\s*<SafeAreaProvider>\s*<SafeAreaView edges=\{\['top', 'right', 'bottom', 'left'\]\}/);
  assert.match(modal, /<KeyboardAvoidingView\s+enabled=\{Platform\.OS === 'android'\}\s+behavior=\{Platform\.OS === 'android' \? 'height' : undefined\}/);
  assert.match(modal, /automaticallyAdjustKeyboardInsets=\{Platform\.OS === 'ios'\}/);
  assert.match(modal, /keyboardShouldPersistTaps="handled"/);
  assert.doesNotMatch(modal, /behavior=\{Platform\.OS === 'ios'/);
});
