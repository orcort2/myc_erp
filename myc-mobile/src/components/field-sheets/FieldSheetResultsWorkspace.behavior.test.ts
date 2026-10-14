import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { dirname, resolve } from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import ts from 'typescript';

const here = dirname(fileURLToPath(import.meta.url));
const require = createRequire(import.meta.url);

type Node = { type?: unknown; props?: Record<string, any> };
function nodes(tree: unknown): Node[] {
  if (Array.isArray(tree)) return tree.flatMap(nodes);
  if (!tree || typeof tree !== 'object') return [];
  const node = tree as Node;
  return [node, ...nodes(node.props?.children)];
}

class FakeApiError extends Error { fieldErrors: { field: string; message: string }[] = []; }

/** Ejecuta el componente REAL; sólo hooks de React y puertos nativos son falsos. */
function workspaceHarness(onSave: (rows: any[]) => Promise<void>, readOnly = false) {
  const slots: unknown[] = [];
  let cursor = 0;
  const jsx = (type: unknown, props: Record<string, unknown>) => ({ type, props });
  const ports = (name: string): unknown => {
    if (name === 'react/jsx-runtime') return { jsx, jsxs: jsx, Fragment: 'Fragment' };
    if (name === 'react') return {
      useState: (initial: unknown) => {
        const index = cursor++;
        if (!(index in slots)) slots[index] = typeof initial === 'function' ? (initial as () => unknown)() : initial;
        return [slots[index], (value: unknown) => { slots[index] = typeof value === 'function' ? (value as (v: unknown) => unknown)(slots[index]) : value; }];
      },
      useRef: (() => {
        // refs estables entre renders: se indexan en slots
        return (initial: unknown) => {
          const index = cursor++;
          if (!(index in slots)) slots[index] = { current: initial };
          return slots[index];
        };
      })(),
      useEffect: () => {},
      useMemo: (factory: () => unknown) => factory(),
    };
    if (name === 'react-native') return {
      StyleSheet: { create: (styles: unknown) => styles, flatten: (s: unknown) => s },
      Alert: { alert: () => {} }, Platform: { OS: 'ios' }, useWindowDimensions: () => ({ width: 400, height: 800 }),
      KeyboardAvoidingView: 'KeyboardAvoidingView', Modal: 'Modal', Pressable: 'Pressable', ScrollView: 'ScrollView',
      Text: 'Text', TextInput: 'TextInput', View: 'View',
    };
    if (name === '@/src/api/client') return { ApiError: FakeApiError };
    if (name === '@/src/design/primitives') return { PrimaryButton: 'PrimaryButton', SecondaryButton: 'SecondaryButton', CloseButton: 'CloseButton' };
    if (name === '@/src/design/tokens') return require(resolve(here, '../../design/tokens'));
    if (name.startsWith('@/src/services/')) return require(resolve(here, '../..', name.slice('@/src/'.length)));
    return new Proxy({}, { get: (_target, key) => key });
  };
  const source = readFileSync(resolve(here, 'FieldSheetResultsWorkspace.tsx'), 'utf8');
  const javascript = ts.transpileModule(source, { compilerOptions: {
    target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX,
  } }).outputText;
  const exports: Record<string, (props: unknown) => unknown> = {};
  new Function('require', 'exports', javascript)(ports, exports);

  let closed = 0;
  const section = {
    key: 'measurements', title: 'Mediciones', rows: 1,
    columns: [{ key: 'reading', label: 'Lectura', data_type: 'text', editable: true }],
  };
  const props = {
    visible: true, title: 'Equipo', sections: [section], readOnly,
    rows: [{ section_key: 'measurements', row_number: 1, row_data: { reading: '1' } }],
    onClose: () => { closed += 1; }, onSave,
  };
  const render = () => { cursor = 0; return exports.FieldSheetResultsWorkspace(props); };
  const footer = () => {
    const all = nodes(render());
    return all.filter((node) => node.type === 'PrimaryButton' || node.type === 'SecondaryButton').map((n) => n.props!);
  };
  const footerLabels = () => footer().map((props) => props.label).filter((l) => l === 'Guardar resultados' || l === 'Cerrar');
  const edit = (value: string) => {
    const input = nodes(render()).find((node) => node.type === 'TextInput');
    assert.ok(input);
    input.props!.onChangeText(value);
  };
  const press = (label: string) => {
    const button = footer().find((props) => props.label === label);
    assert.ok(button, `no hay botón ${label}`);
    return button.onPress();
  };
  const savedRows = () => nodes(render()).find((n) => n.type === 'TextInput')!.props!.value;
  return { render, footerLabels, edit, press, savedRows, closed: () => closed, footer };
}

const settle = () => new Promise((resolve) => setImmediate(resolve));
function deferred() {
  let resolve!: () => void; let reject!: (e: unknown) => void;
  const promise = new Promise<void>((res, rej) => { resolve = res; reject = rej; });
  return { promise, resolve, reject };
}

test('abre sin cambios: el pie es "Cerrar" y no existe "Cerrar" en el encabezado', () => {
  const h = workspaceHarness(async () => {});
  assert.deepEqual(h.footerLabels(), ['Cerrar']);
  const tree = nodes(h.render());
  assert.equal(tree.some((node) => node.type === 'CloseButton'), false);
  assert.equal(tree.filter((node) => node.props?.label === 'Cerrar').length, 1);
});

test('editar -> "Guardar resultados"; guardado exitoso -> "Cerrar"; volver a editar -> "Guardar resultados"', async () => {
  const sent: unknown[] = [];
  const h = workspaceHarness(async (rows) => { sent.push(rows); });
  h.edit('2');
  assert.deepEqual(h.footerLabels(), ['Guardar resultados']);
  await h.press('Guardar resultados');
  assert.equal(sent.length, 1);
  assert.deepEqual(h.footerLabels(), ['Cerrar']);
  h.edit('3');
  assert.deepEqual(h.footerLabels(), ['Guardar resultados']);
  await h.press('Guardar resultados');
  assert.deepEqual(h.footerLabels(), ['Cerrar']);
});

test('guardado fallido: sigue "Guardar resultados", conserva el valor local y permite reintentar', async () => {
  let fail = true;
  const h = workspaceHarness(async () => { if (fail) throw new Error('sin red'); });
  h.edit('9');
  assert.equal(await h.press('Guardar resultados'), undefined);
  assert.deepEqual(h.footerLabels(), ['Guardar resultados']);
  assert.equal(h.savedRows(), '9');
  assert.equal(h.closed(), 0);
  fail = false;
  await h.press('Guardar resultados');
  assert.deepEqual(h.footerLabels(), ['Cerrar']);
  assert.equal(h.savedRows(), '9');
});

test('una respuesta vieja NO limpia la edición posterior: editar durante el guardado deja "Guardar resultados"', async () => {
  const gate = deferred();
  const sent: any[] = [];
  const h = workspaceHarness((rows) => { sent.push(rows); return gate.promise; });
  h.edit('A');
  const saving = h.press('Guardar resultados');
  await settle();
  h.edit('B'); // se edita mientras A viaja
  gate.resolve();
  await saving;
  assert.equal(sent[0][0].row_data.reading, 'A');
  assert.equal(h.savedRows(), 'B');
  assert.deepEqual(h.footerLabels(), ['Guardar resultados'], 'B no está persistido');
  assert.equal(h.footer().find((p) => p.label === 'Guardar resultados')!.disabled, false);
});

test('no se abre un segundo guardado mientras uno sigue en vuelo', async () => {
  const gate = deferred();
  let calls = 0;
  const h = workspaceHarness(() => { calls += 1; return gate.promise; });
  h.edit('A');
  const first = h.press('Guardar resultados');
  await settle();
  h.edit('B');
  assert.equal(h.footer().find((p) => p.label === 'Guardar resultados')!.disabled, true);
  h.press('Guardar resultados'); // aunque se fuerce el onPress, handleSave lo rechaza
  await settle();
  assert.equal(calls, 1);
  gate.resolve();
  await first;
});

test('el botón "Cerrar" usa requestClose (salida segura existente) y cierra sin cambios pendientes', async () => {
  const h = workspaceHarness(async () => {});
  h.press('Cerrar');
  assert.equal(h.closed(), 1);
});

test('sólo lectura: se ofrece "Cerrar" y nunca "Guardar resultados"', () => {
  const h = workspaceHarness(async () => {}, true);
  assert.deepEqual(h.footerLabels(), ['Cerrar']);
});
