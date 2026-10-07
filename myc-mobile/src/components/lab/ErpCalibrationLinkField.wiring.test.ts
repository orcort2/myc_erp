import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import test, { mock } from 'node:test';
import { fileURLToPath } from 'node:url';
import ts from 'typescript';

import * as erp from '../../services/lab-erp-calibration';

/**
 * ErpCalibrationLinkField real sobre un mini-runtime de hooks (useState /
 * useEffect con limpieza) y puertos RN simulados. Prueba estados, debounce,
 * selección y limpieza; no mide layout ni teclado nativo. Incluye cableado
 * estático de work-orders.tsx.
 */
const here = dirname(fileURLToPath(import.meta.url));
const source = readFileSync(resolve(here, './ErpCalibrationLinkField.tsx'), 'utf8');
const workOrders = readFileSync(resolve(here, '../../../app/(technician)/work-orders.tsx'), 'utf8');

type Host = { type: string; props: Record<string, any> };
type Candidate = erp.ErpCalibrationCandidate;

const candidate = (id: number, extra: Partial<Candidate> = {}): Candidate => ({
  service_order_id: id, service_order_folio: `OSMYC-${id}`, quotation_id: id, quotation_folio: `COT-${id}`,
  client_id: 1, client_name: 'MetroInd', calibration_item_count: 1, calibration_quantity: 2,
  calibration_items: [], active_lab_root_id: null, active_lab_root_folio: null, available: true, ...extra,
});

function deferred<T>() {
  let resolveValue!: (value: T) => void;
  let rejectValue!: (error: Error) => void;
  const promise = new Promise<T>((ok, fail) => { resolveValue = ok; rejectValue = fail; });
  return { promise, resolve: resolveValue, reject: rejectValue };
}

function mount(labClientName = 'MetroInd') {
  const slots: any[] = [];
  let cursor = 0;
  let pending: { index: number; fn: () => unknown }[] = [];
  let dirty = false;
  const react = {
    useState(initial: unknown) {
      const index = cursor++;
      if (!(index in slots)) slots[index] = initial;
      return [slots[index], (value: unknown) => {
        const next = typeof value === 'function' ? (value as (p: unknown) => unknown)(slots[index]) : value;
        if (!Object.is(next, slots[index])) { slots[index] = next; dirty = true; }
      }];
    },
    useEffect(fn: () => unknown, deps: unknown[]) {
      const index = cursor++;
      const prev = slots[index];
      if (!prev || deps.some((dep, k) => !Object.is(dep, prev.deps[k]))) {
        slots[index] = { deps, cleanup: prev?.cleanup };
        pending.push({ index, fn });
      }
    },
  };
  const jsx = (type: string, props: Record<string, any>) => ({ type, props });
  const ports: Record<string, unknown> = {
    react,
    'react/jsx-runtime': { jsx, jsxs: jsx },
    'react-native': {
      Pressable: 'Pressable', Text: 'Text', TextInput: 'TextInput', View: 'View',
      StyleSheet: { create: (styles: unknown) => styles },
    },
    '@/src/design/primitives': { AlertBanner: 'AlertBanner', Card: 'Card', EmptyState: 'EmptyState', LoadingState: 'LoadingState' },
    '@/src/design/tokens': { colors: {}, radius: {}, spacing: {} },
    '@/src/services/lab-erp-calibration': erp,
  };
  const javascript = ts.transpileModule(source, { compilerOptions: {
    target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX,
  } }).outputText;
  const exports: Record<string, (props: unknown) => Host> = {};
  new Function('require', 'exports', javascript)((name: string) => {
    assert.ok(name in ports, `import inesperado: ${name}`);
    return ports[name];
  }, exports);

  const calls: { path: string; reply: ReturnType<typeof deferred<Candidate[]>> }[] = [];
  const request = (path: string) => {
    const reply = deferred<Candidate[]>();
    calls.push({ path, reply });
    return reply.promise;
  };
  let selection: Candidate | null = null;
  const changes: (Candidate | null)[] = [];
  let tree!: Host;
  function render() {
    for (let pass = 0; pass < 10; pass++) {
      cursor = 0; pending = []; dirty = false;
      tree = exports.ErpCalibrationLinkField({
        request, selection, labClientName,
        onChange: (value: Candidate | null) => { selection = value; changes.push(value); },
      });
      for (const effect of pending) {
        slots[effect.index].cleanup?.();
        const cleanup = effect.fn();
        slots[effect.index].cleanup = typeof cleanup === 'function' ? cleanup : undefined;
      }
      if (!dirty) return;
    }
    throw new Error('render no converge');
  }
  const flatten = (node: unknown): Host[] => {
    if (Array.isArray(node)) return node.flatMap(flatten);
    if (!node || typeof node !== 'object') return [];
    return [node as Host, ...flatten((node as Host).props?.children)];
  };
  const text = (node: unknown): string => {
    if (Array.isArray(node)) return node.map(text).join('');
    if (typeof node === 'string' || typeof node === 'number') return String(node);
    if (!node || typeof node !== 'object') return '';
    return text((node as Host).props?.children);
  };
  render();
  return {
    calls, changes, render,
    nodes: () => flatten(tree),
    texts: () => flatten(tree).filter((node) => node.type === 'Text').map((node) => text(node.props.children)),
    type(value: string) {
      flatten(tree).find((node) => node.type === 'TextInput')!.props.onChangeText(value);
      render();
    },
    rows: () => flatten(tree).filter((node) => node.type === 'Pressable' && typeof node.props.style === 'function'),
    async settle() { await new Promise((done) => setImmediate(done)); render(); },
  };
}

test.beforeEach(() => mock.timers.enable({ apis: ['setTimeout'] }));
test.afterEach(() => mock.timers.reset());

test('sin selección: estado opcional explícito y ninguna consulta', () => {
  const view = mount();
  assert.equal(view.nodes().find((node) => node.type === 'EmptyState')?.props.title, 'Sin vínculo ERP');
  assert.equal(view.calls.length, 0);
});

test('debounce de 300 ms y mínimo de 2 caracteres', () => {
  const view = mount();
  view.type('c');
  mock.timers.tick(1000);
  view.render();
  assert.equal(view.calls.length, 0);
  view.type('co');
  mock.timers.tick(200);
  view.type('cot');
  mock.timers.tick(299);
  view.render();
  assert.equal(view.calls.length, 0);
  assert.ok(view.nodes().some((node) => node.type === 'LoadingState'), 'pendiente = cargando');
  mock.timers.tick(1);
  view.render();
  assert.equal(view.calls.length, 1);
  assert.equal(view.calls[0].path, `${erp.ERP_CANDIDATES_PATH}?q=cot&limit=20`);
});

test('muestra Cotización/ETS/Cliente, selecciona uno y permite limpiar antes de crear', async () => {
  const view = mount();
  view.type('cot');
  mock.timers.tick(300);
  view.render();
  view.calls[0].reply.resolve([candidate(41), candidate(42, { available: false, active_lab_root_folio: 6410 })]);
  await view.settle();
  assert.ok(view.texts().includes('Cotización COT-41'));
  assert.ok(view.texts().includes('ETS OSMYC-41 · MetroInd'));
  const [first, linked] = view.rows();
  assert.equal(linked.props.disabled, true);
  assert.ok(view.texts().includes('Ya vinculada a OT 6410'));
  first.props.onPress();
  view.render();
  assert.equal(view.changes.at(-1)?.service_order_id, 41);
  assert.ok(view.texts().includes('Cotización COT-41'));
  const clear = view.nodes().find((node) => node.props.accessibilityLabel === 'Quitar vínculo ERP')!;
  clear.props.onPress();
  view.render();
  assert.equal(view.changes.at(-1), null);
});

test('error y vacío son estados explícitos', async () => {
  const view = mount();
  view.type('zz');
  mock.timers.tick(300);
  view.render();
  view.calls[0].reply.reject(new Error('Sin conexión'));
  await view.settle();
  assert.equal(view.nodes().find((node) => node.type === 'AlertBanner')?.props.children, 'Sin conexión');
  view.type('zzz');
  mock.timers.tick(300);
  view.render();
  view.calls[1].reply.resolve([]);
  await view.settle();
  assert.equal(view.nodes().find((node) => node.type === 'EmptyState')?.props.title, 'Sin resultados');
});

test('work-orders: el campo es interno, separado de purchase_order y sólo al crear', () => {
  assert.match(workOrders, /\{user\.actor_type === 'internal' && canAttachErpLink\(groupMode, !!workOrder\) && categoryAllowsErpLink\(operationalCategory\) && \(/);
  assert.match(workOrders, /<FormSection title="Vincular con cotización ERP \(opcional\)">/);
  assert.match(workOrders, /<ErpCalibrationLinkField labClientName=\{general\.client_name\} onChange=\{setErpLink\}/);
  assert.match(workOrders, /<Field label="Orden de compra \/ cotización" value=\{general\.purchase_order\}/);
  assert.match(workOrders, /body: JSON\.stringify\(withOperationalCategory\(withErpLink\(\{[\s\S]*?\}, erpLink, groupMode, !!workOrder\), operationalCategory, groupMode, !!workOrder\)\)/);
  assert.match(workOrders, /setGeneral\(emptyGeneral\(\)\);\n\s*setErpLink\(null\);/);
});

async function selectFirst(view: ReturnType<typeof mount>) {
  view.type('cot');
  mock.timers.tick(300);
  view.render();
  view.calls[0].reply.resolve([candidate(41)]);
  await view.settle();
  view.rows()[0].props.onPress();
  view.render();
}

test('con selección muestra el cliente ERP; si difiere del LAB advierte sin bloquear ni sobrescribir', async () => {
  const same = mount('MetroInd');
  await selectFirst(same);
  assert.ok(same.texts().includes('Cliente ERP: MetroInd'));
  assert.equal(same.nodes().some((node) => node.type === 'AlertBanner'), false);

  const different = mount('Laboratorio Norte');
  await selectFirst(different);
  const banner = different.nodes().find((node) => node.type === 'AlertBanner');
  assert.equal(banner?.props.tone, 'warning');
  assert.match(String(banner?.props.children), /Laboratorio Norte[\s\S]*MetroInd/);
  // No bloquea: la selección sigue vigente y puede limpiarse.
  assert.equal(different.changes.at(-1)?.service_order_id, 41);
  assert.ok(different.nodes().some((node) => node.props.accessibilityLabel === 'Quitar vínculo ERP'));
});
