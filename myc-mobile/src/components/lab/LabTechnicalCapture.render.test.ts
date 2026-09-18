import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { dirname, resolve } from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import ts from 'typescript';

const here = dirname(fileURLToPath(import.meta.url));
const require = createRequire(import.meta.url);

// Execute the real component and event handler. Only native/expo ports and
// React hooks are replaced; canonical fields, payload and progress are real.
function captureHarness(sheet: Record<string, unknown>, hasSheet = true) {
  const slots: unknown[] = [];
  let cursor = 0;
  const jsx = (type: unknown, props: Record<string, unknown>) => ({ type, props });
  const ports = (name: string): unknown => {
    if (name === 'react/jsx-runtime') return { jsx, jsxs: jsx, Fragment: 'Fragment' };
    if (name === 'react') return {
      useState: (initial: unknown) => {
        const index = cursor++;
        if (!(index in slots)) slots[index] = initial;
        return [slots[index], (value: unknown) => { slots[index] = typeof value === 'function' ? value(slots[index]) : value; }];
      },
      useEffect: () => {},
      useRef: (current: unknown) => ({ current }),
    };
    if (name === 'react-native') return {
      StyleSheet: { create: (styles: unknown) => styles }, Alert: { alert: () => {} },
      ScrollView: 'ScrollView', View: 'View', Text: 'Text', Pressable: 'Pressable',
    };
    if (name.startsWith('@/src/services/') && !name.includes('label-print-service')) {
      return require(resolve(here, '../..', name.slice('@/src/'.length)));
    }
    return new Proxy({}, { get: (_target, key) => key });
  };
  const source = readFileSync(resolve(here, 'LabTechnicalCapture.tsx'), 'utf8');
  const javascript = ts.transpileModule(source, { compilerOptions: {
    target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX,
  } }).outputText;
  const exports: Record<string, (props: unknown) => unknown> = {};
  new Function('require', 'exports', javascript)(ports, exports);
  const equipment = { id: 289, position: 1, instrument: 'Equipo', service_type: 'linked', field_sheet_id: hasSheet ? sheet.id : null };
  const props = {
    accessToken: 'test', canCapture: true, canCreateTickets: true, canOverrideReceptionDate: false,
    canReopenFieldSheetDirectly: true, external: false, onUpdated: () => {},
    request: async () => sheet,
    workOrder: { id: 72, folio: 6471, reception_date: '2026-09-17', status: 'in_progress', equipment: [equipment] },
  };
  return () => { cursor = 0; return exports.LabTechnicalCapture(props); };
}

type Node = { type?: unknown; props?: Record<string, unknown> };
function nodes(tree: unknown): Node[] {
  if (Array.isArray(tree)) return tree.flatMap(nodes);
  if (!tree || typeof tree !== 'object') return [];
  const node = tree as Node;
  return [node, ...nodes(node.props?.children)];
}

test('opens linked LAB EXTERNO with groups and no result_sections using common capture', async () => {
  const render = captureHarness({
    id: 91, template_key: 'lab_externo', status: 'in_progress',
    template_definition: { kind: 'lab_externo', groups: [] },
    capture_values: {}, results_rows: [], company: 'Cliente',
  });
  const open = nodes(render()).find((node) => node.props?.label === 'Abrir hoja');
  assert.ok(open);
  await (open.props!.onPress as () => Promise<void>)();
  let tree: unknown;
  assert.doesNotThrow(() => { tree = render(); });
  const rendered = nodes(tree);
  assert.ok(rendered.some((node) => node.props?.title === 'Firmas'));
  assert.ok(rendered.some((node) => node.props?.label === 'Editar'));
  assert.ok(rendered.some((node) => node.type === 'LabExternalFieldSheet'));
  assert.ok(!rendered.some((node) => node.type === 'FieldSheetResultsWorkspace'));
});


test('linked sin hoja crea LAB EXTERNO sin mostrar selector interno durante la carga', async () => {
  const render = captureHarness({
    id: 91, template_key: 'lab_externo', status: 'draft',
    template_definition: { kind: 'lab_externo', groups: [] }, capture_values: {}, results_rows: [],
  }, false);
  const open = nodes(render()).find((node) => node.props?.label === 'Seleccionar hoja');
  assert.ok(open);
  const pending = (open.props!.onPress as () => Promise<void>)();
  assert.ok(nodes(render()).some((node) => node.type === 'LoadingState'));
  await pending;
  const rendered = nodes(render());
  assert.ok(rendered.some((node) => node.type === 'LabExternalFieldSheet'));
  assert.ok(rendered.some((node) => node.props?.label === 'Guardar borrador'));
  assert.ok(!rendered.some((node) => node.props?.title === 'Selecciona hoja de campo'));
});
