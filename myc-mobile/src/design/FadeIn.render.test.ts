import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import ts from 'typescript';

/**
 * FadeIn real (src/design/primitives.tsx) ejecutado con un mini-runtime de
 * hooks y puertos simulados de Animated/AccessibilityInfo. Prueba que la
 * visibilidad nunca depende de una animación ni de la detección asíncrona de
 * "Reducir movimiento". No sustituye la validación física en iPhone.
 */
const root = resolve(dirname(fileURLToPath(import.meta.url)), '../..');
const read = (path: string) => readFileSync(resolve(root, path), 'utf8');
const source = read('src/design/primitives.tsx');

type Style = { opacity?: unknown; transform?: { translateY: FakeValue }[] };
type Node = { type: string; props: { style: Style; children: unknown } };

class FakeValue {
  history: number[] = [];
  animation: FakeAnimation | null = null;
  constructor(public value: number) {}
  setValue(value: number) {
    this.animation?.stop();
    this.value = value;
    this.history.push(value);
  }
}

type FakeAnimation = { value: FakeValue; config: { toValue: number; useNativeDriver: boolean }; started: boolean; stopped: boolean; stop(): void };

function mountFadeIn() {
  const values: FakeValue[] = [];
  const timings: FakeAnimation[] = [];
  const listeners: ((value: boolean) => void)[] = [];
  let resolvePreference!: (value: boolean) => void;
  const preference = new Promise<boolean>((ok) => { resolvePreference = ok; });

  const slots: any[] = [];
  let cursor = 0;
  let pending: { index: number; fn: () => unknown }[] = [];
  let dirty = false;
  const react = {
    useState(initial: unknown) {
      const index = cursor++;
      if (!(index in slots)) slots[index] = initial;
      return [slots[index], (value: unknown) => { if (!Object.is(value, slots[index])) { slots[index] = value; dirty = true; } }];
    },
    useRef(value: unknown) {
      const index = cursor++;
      if (!(index in slots)) slots[index] = { current: value };
      return slots[index];
    },
    useEffect(fn: () => unknown, deps?: unknown[]) {
      const index = cursor++;
      const prev = slots[index];
      if (!prev || !deps || deps.some((dep, k) => !Object.is(dep, prev.deps[k]))) {
        slots[index] = { deps, cleanup: prev?.cleanup };
        pending.push({ index, fn });
      }
    },
  };
  const ports: Record<string, unknown> = {
    react,
    'react/jsx-runtime': { jsx: (type: string, props: object) => ({ type, props }), jsxs: (type: string, props: object) => ({ type, props }) },
    'react-native': {
      AccessibilityInfo: {
        isReduceMotionEnabled: () => preference,
        addEventListener: (_name: string, listener: (value: boolean) => void) => {
          listeners.push(listener);
          return { remove: () => listeners.splice(listeners.indexOf(listener), 1) };
        },
      },
      ActivityIndicator: 'ActivityIndicator', Pressable: 'Pressable', Text: 'Text', TextInput: 'TextInput', View: 'View',
      StyleSheet: { create: (styles: unknown) => styles },
      Animated: {
        View: 'Animated.View',
        Value: function Value(this: unknown, initial: number) { const value = new FakeValue(initial); values.push(value); return value; },
        timing(value: FakeValue, config: FakeAnimation['config']) {
          const animation: FakeAnimation = {
            value, config, started: false, stopped: false,
            stop() { this.stopped = true; if (value.animation === this) value.animation = null; },
          };
          (animation as unknown as { start(): void }).start = () => { animation.started = true; value.animation = animation; };
          timings.push(animation);
          return animation;
        },
      },
    },
    '@expo/vector-icons': { MaterialCommunityIcons: 'Icon' },
    'expo-router': { router: {} },
    '@/src/design/tokens': { colors: {}, radius: {}, spacing: {}, typography: {} },
  };
  const javascript = ts.transpileModule(source, { compilerOptions: {
    target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX,
  } }).outputText;
  const exports: Record<string, (props: object) => Node> = {};
  new Function('require', 'exports', javascript)((name: string) => {
    assert.ok(name in ports, `import inesperado: ${name}`);
    return ports[name];
  }, exports);

  let tree!: Node;
  function render(props: { transitionKey?: string; children?: unknown }) {
    for (let pass = 0; pass < 10; pass++) {
      cursor = 0;
      pending = [];
      dirty = false;
      tree = exports.FadeIn({ children: 'contenido funcional', ...props });
      for (const effect of pending) {
        slots[effect.index].cleanup?.();
        const cleanup = effect.fn();
        slots[effect.index].cleanup = typeof cleanup === 'function' ? cleanup : undefined;
      }
      if (!dirty) return tree;
    }
    throw new Error('render no converge');
  }
  const settle = () => new Promise<void>((done) => setImmediate(done));
  /** Desmonta y vuelve a montar un FadeIn nuevo dentro de la misma instancia del módulo. */
  function remount(props: { transitionKey?: string } = {}) {
    slots.forEach((slot) => slot?.cleanup?.());
    slots.length = 0;
    return render(props);
  }
  return {
    values, timings, listeners, render, remount,
    tree: () => tree,
    translateY: () => tree.props.style.transform![0].translateY,
    async resolvePreference(value: boolean, props: { transitionKey?: string } = {}) { resolvePreference(value); await settle(); return render(props); },
    changePreference(value: boolean, props: { transitionKey?: string } = {}) { listeners.forEach((listener) => listener(value)); return render(props); },
    exports,
  };
}

function assertVisible(tree: Node) {
  assert.equal(tree.type, 'Animated.View');
  assert.equal(tree.props.style.opacity, 1, 'opacity debe ser 1 literal, nunca un valor animado');
  assert.equal(tree.props.children, 'contenido funcional');
}

test('1. FadeIn nunca inicia con opacity 0 (ni siquiera antes de conocer Reduce Motion)', () => {
  const fade = mountFadeIn();
  const tree = fade.render({ transitionKey: 'general' });
  assertVisible(tree);
  assert.equal(fade.values.length, 1, 'sólo existe el valor animado de translateY');
  assert.equal(fade.translateY().value, 0);
  assert.equal(fade.timings.length, 0, 'preferencia desconocida → sin animación');
});

test('2. con Reduce Motion activo los children se muestran sin depender de ninguna animación', async () => {
  const fade = mountFadeIn();
  fade.render({ transitionKey: 'general' });
  const tree = await fade.resolvePreference(true, { transitionKey: 'general' });
  assertVisible(tree);
  assert.equal(fade.translateY().value, 0);
  fade.render({ transitionKey: 'equipment' });
  assertVisible(fade.tree());
  assert.equal(fade.timings.length, 0, 'Reduce Motion nunca inicia animaciones');
});

test('2b. resolver la preferencia tarde no dispara animación sobre contenido ya visible', async () => {
  const fade = mountFadeIn();
  fade.render({ transitionKey: 'general' });
  await fade.resolvePreference(false, { transitionKey: 'general' });
  assert.equal(fade.timings.length, 0);
  assertVisible(fade.tree());
});

test('3/4. con movimiento permitido, cambiar transitionKey sólo anima translateY y nunca oculta children', async () => {
  const fade = mountFadeIn();
  fade.render({ transitionKey: 'general' });
  await fade.resolvePreference(false, { transitionKey: 'general' });
  const tree = fade.render({ transitionKey: 'equipment' });
  assertVisible(tree);
  assert.equal(fade.timings.length, 1);
  const [animation] = fade.timings;
  assert.equal(animation.value, fade.translateY(), 'la única propiedad animada es translateY');
  assert.equal(animation.config.toValue, 0);
  assert.equal(animation.started, true);
  assert.equal(fade.translateY().history.at(-1), 6, 'arranca desplazado 6 puntos, siempre visible');
  fade.render({ transitionKey: 'signatures' });
  assert.equal(animation.stopped, true, 'una transición nueva detiene la anterior');
  assertVisible(fade.tree());
});

test('3b. un FadeIn nuevo anima al montar sólo si ya se sabe que el movimiento está permitido', async () => {
  const allowed = mountFadeIn();
  allowed.render({ transitionKey: 'general' });
  await allowed.resolvePreference(false, { transitionKey: 'general' });
  assert.equal(allowed.timings.length, 0);
  assertVisible(allowed.remount({ transitionKey: 'equipment' }));
  assert.equal(allowed.timings.length, 1, 'con preferencia conocida=false el siguiente paso sí anima');
  assert.equal(allowed.timings[0].value, allowed.translateY());

  const reduced = mountFadeIn();
  reduced.render({ transitionKey: 'general' });
  await reduced.resolvePreference(true, { transitionKey: 'general' });
  assertVisible(reduced.remount({ transitionKey: 'equipment' }));
  assert.equal(reduced.timings.length, 0, 'con Reduce Motion conocido el nuevo FadeIn no anima');
  assert.equal(reduced.translateY().value, 0);
});

test('activar Reduce Motion a mitad de una transición devuelve translateY a 0 de inmediato', async () => {
  const fade = mountFadeIn();
  fade.render({ transitionKey: 'general' });
  await fade.resolvePreference(false, { transitionKey: 'general' });
  fade.render({ transitionKey: 'equipment' });
  const [animation] = fade.timings;
  const tree = fade.changePreference(true, { transitionKey: 'equipment' });
  assert.equal(animation.stopped, true);
  assert.equal(fade.translateY().value, 0);
  assertVisible(tree);
});

test('5. no existe animación de opacity ni opacity inicial 0 en FadeIn', () => {
  const body = source.slice(source.indexOf('export function FadeIn('), source.indexOf('const styles = StyleSheet.create({'));
  assert.doesNotMatch(body, /Animated\.timing\(opacity/);
  assert.doesNotMatch(body, /new Animated\.Value\(0\)\)\.current;\s*const translateY/);
  assert.doesNotMatch(body, /opacity\.setValue/);
  assert.match(body, /opacity: 1,\s*transform: \[\{ translateY \}\]/);
  assert.doesNotMatch(body, /setTimeout/, 'sin timeout/fallback de visibilidad');
});

test('6. los consumidores siguen usando FadeIn sin cambios funcionales ni estilos de opacity propios', () => {
  const expected: Record<string, string[]> = {
    'app/(technician)/work-orders.tsx': [
      ...Array(7).fill('<FadeIn transitionKey={step}>'),
      "<FadeIn transitionKey={equipmentEditor === 'new' ? 'new' : equipmentEditor?.id}>",
    ],
    'app/(technician)/clients.tsx': ['<FadeIn transitionKey={mode}>', '<FadeIn transitionKey={resultsKey}>'],
    'src/components/lab/LabTechnicalCapture.tsx': ["<FadeIn transitionKey={`${activeEquipment.id}:${sheet?.id ?? 'selector'}`}>"],
  };
  for (const [path, usages] of Object.entries(expected)) {
    const file = read(path);
    assert.deepEqual(file.match(/<FadeIn[^>]*>/g), usages, path);
    assert.match(file, /FadeIn,?[\s\S]*from '@\/src\/design\/primitives'/);
  }
});
