import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import test from 'node:test';
import ts from 'typescript';
import * as selector from '../../services/lab-client-selector';
import { fileURLToPath } from 'node:url';

/**
 * Cierre UX 2026-09 (item C): LabClientSelector debe quedar en un contenedor
 * delimitado (Card) con estados de carga/error/vacío visibles y feedback de
 * presión en cada fila -- antes la búsqueda fallaba en silencio y no había
 * borde/tarjeta que delimitara la lista.
 */
const source = readFileSync(
  resolve(dirname(fileURLToPath(import.meta.url)), './LabClientSelector.tsx'),
  'utf8',
);

test('el selector vive dentro de la tarjeta delimitada (Card), en ambos modos', () => {
  assert.match(source, /<Card>[\s\S]*Buscar cliente/);
  assert.match(source, /<Card>[\s\S]*Crear cliente/);
});

test('un error de búsqueda ya no se traga en silencio', () => {
  assert.doesNotMatch(source, /búsqueda silenciosa/);
  assert.match(source, /setSearchError\(/);
  assert.match(source, /<AlertBanner tone="danger">\{searchError\}<\/AlertBanner>/);
});

test('la búsqueda muestra un estado de carga explícito, no una lista vacía ambigua', () => {
  assert.match(source, /<LoadingState label="Buscando clientes…" \/>/);
});

test('cero o un carácter no programan request y dos o más conservan debounce de 300 ms', () => {
  const minimumGuard = source.indexOf('if (!shouldSearchLabClients(state.searchTerm))');
  const debounce = source.indexOf('const timer = setTimeout');
  const request = source.indexOf('request<LabClient[]>');
  assert.ok(minimumGuard >= 0 && minimumGuard < debounce && debounce < request);
  assert.match(source, /}, 300\);/);
  assert.match(source, /\/lab-clients\?\$\{query\}/);
});

test('cada fila de resultado da feedback de presión, no sólo seleccionado', () => {
  assert.match(source, /pressed && styles\.resultRowPressed/);
});

// Render/handlers con puertos simulados: no mide layout ni teclado nativo.
test('cinco resultados sin scroll anidado, sin recorte y seleccionables', () => {
  type Node = { type: string; props: { children?: unknown; style?: unknown; onPress?: () => void } };
  const clients = Array.from({ length: 25 }, (_, id) => ({
    id, company: `Cliente ${id}`, address: '', attention: 'Contacto',
    postal_code: null, city: null, state: null,
  }));
  let state = { ...selector.initialSelectorState(), searchTerm: 'Cliente', results: clients };
  let cursor = 0;
  const selected: unknown[] = [];
  const jsx = (type: string, props: unknown) => ({ type, props });
  const ports: Record<string, unknown> = {
    'react/jsx-runtime': { jsx, jsxs: jsx },
    react: {
      useEffect: () => undefined,
      useState: (initial: unknown) => cursor++ === 0
        ? [state, (update: (current: typeof state) => typeof state) => { state = update(state); }]
        : [initial, () => undefined],
    },
    'react-native': {
      Alert: {}, Pressable: 'Pressable', Text: 'Text', TextInput: 'TextInput', View: 'View',
      StyleSheet: { create: (styles: unknown) => styles },
    },
    '@/src/design/primitives': { Card: 'Card', AlertBanner: 'AlertBanner', EmptyState: 'EmptyState', LoadingState: 'LoadingState' },
    '@/src/design/tokens': { colors: {}, radius: {}, spacing: {} },
    '@/src/services/lab-client-selector': selector,
  };
  const javascript = ts.transpileModule(source, { compilerOptions: {
    module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX,
  } }).outputText;
  const exports: Record<string, (props: unknown) => unknown> = {};
  new Function('require', 'exports', javascript)((name: string) => {
    assert.ok(name in ports, `import inesperado: ${name}`);
    return ports[name];
  }, exports);
  function flatten(value: unknown): Node[] {
    if (Array.isArray(value)) return value.flatMap(flatten);
    if (!value || typeof value !== 'object') return [];
    const node = value as Node;
    return [node, ...flatten(node.props?.children)];
  }
  const nodes = flatten(exports.LabClientSelector({ onSelect: (client: unknown) => selected.push(client), request: () => { throw new Error('request inesperado'); } }));
  const rows = nodes.filter((node) => node.type === 'Pressable' && typeof node.props.style === 'function');
  assert.equal(rows.length, 5);
  assert.ok(nodes.every((node) => node.type !== 'ScrollView'));
  rows.forEach((row, index) => {
    row.props.onPress!();
    assert.equal(state.selectedClientId, clients[index].id);
    assert.equal(selected[index], clients[index]);
  });
  assert.doesNotMatch(source, /ScrollView|maxHeight/);
});
