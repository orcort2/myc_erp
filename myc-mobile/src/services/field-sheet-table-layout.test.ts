import assert from 'node:assert/strict';
import test from 'node:test';

import { computeTableLayout, orientationForDimensions } from './field-sheet-table-layout';

// Dimensiones de QA de orientación requeridas por Fase 6: iPhone
// portrait/landscape, Android compact, tablet.
const IPHONE_PORTRAIT = { width: 390, height: 844 };
const IPHONE_LANDSCAPE = { width: 844, height: 390 };
const ANDROID_COMPACT = { width: 360, height: 800 };
const TABLET = { width: 1024, height: 768 };

test('orientationForDimensions clasifica portrait/landscape para las 4 dimensiones de QA', () => {
  assert.equal(orientationForDimensions(IPHONE_PORTRAIT.width, IPHONE_PORTRAIT.height), 'portrait');
  assert.equal(orientationForDimensions(IPHONE_LANDSCAPE.width, IPHONE_LANDSCAPE.height), 'landscape');
  assert.equal(orientationForDimensions(ANDROID_COMPACT.width, ANDROID_COMPACT.height), 'portrait');
  assert.equal(orientationForDimensions(TABLET.width, TABLET.height), 'landscape');
});

test('rotar (portrait <-> landscape) es un recálculo puro -- mismo ancho produce el mismo layout', () => {
  const a = computeTableLayout(IPHONE_LANDSCAPE.width, 5);
  const b = computeTableLayout(IPHONE_LANDSCAPE.width, 5);
  assert.deepEqual(a, b);
});

test('portrait angosto con muchas columnas activa scroll horizontal en vez de comprimir bajo el mínimo legible', () => {
  const layout = computeTableLayout(IPHONE_PORTRAIT.width, 6);
  assert.equal(layout.needsHorizontalScroll, true);
  assert.ok(layout.columnWidth >= 96);
});

test('landscape con el mismo número de columnas aprovecha el ancho completo -- menos o ningún scroll', () => {
  const portrait = computeTableLayout(IPHONE_PORTRAIT.width, 4);
  const landscape = computeTableLayout(IPHONE_LANDSCAPE.width, 4);
  assert.ok(landscape.columnWidth >= portrait.columnWidth);
});

test('tablet con pocas columnas nunca necesita scroll horizontal', () => {
  const layout = computeTableLayout(TABLET.width, 4);
  assert.equal(layout.needsHorizontalScroll, false);
});

test('Android compact con columnas moderadas puede seguir sin scroll si caben al mínimo', () => {
  const layout = computeTableLayout(ANDROID_COMPACT.width, 3);
  assert.equal(layout.needsHorizontalScroll, false);
  assert.ok(layout.columnWidth >= 96);
});

test('columnWidth nunca baja del mínimo configurado, sin importar cuántas columnas', () => {
  const layout = computeTableLayout(320, 10);
  assert.equal(layout.columnWidth, 96);
  assert.equal(layout.needsHorizontalScroll, true);
});

test('cero columnas no revienta el cálculo', () => {
  const layout = computeTableLayout(390, 0);
  assert.equal(layout.columnWidth, 0);
  assert.equal(layout.needsHorizontalScroll, false);
});

test('un mínimo de columna configurable respeta el override', () => {
  const layout = computeTableLayout(390, 3, { minColumnWidth: 60 });
  assert.ok(layout.columnWidth >= 60);
});
