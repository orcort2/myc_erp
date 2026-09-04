import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

/**
 * Cierre UX 2026-09 (item G): FadeIn se aplica exactamente en las
 * transiciones nombradas -- general→equipo, equipo→firmas, firmas→captura,
 * y en el overlay de alta/edición de equipo -- sin animar todo el flujo.
 */
const source = readFileSync(
  resolve(dirname(fileURLToPath(import.meta.url)), '../../app/(technician)/work-orders.tsx'),
  'utf8',
);

test('general (crear/editar OT) usa FadeIn', () => {
  const block = source.slice(source.indexOf("step === 'general' &&"), source.indexOf("step !== 'general' &&"));
  assert.match(block, /<FadeIn transitionKey=\{step\}>/);
});

test('equipo (capture) usa FadeIn', () => {
  const block = source.slice(source.indexOf("step === 'capture' &&"), source.indexOf("step === 'technical' &&"));
  assert.match(block, /<FadeIn transitionKey=\{step\}>/);
});

test('firmas (signatures, las 4 variantes por status/workflow_mode) usan FadeIn', () => {
  // 4a variante (encargo equipo-por-equipo): step === 'signatures' &&
  // workflow_mode === 'equipment_by_equipment' -- prevalidación/blockers +
  // MobileSignatureFlow reutilizado para la firma única de finalize.
  const matches = source.match(/step === 'signatures'[^\n]*&& \(\s*\n\s*<FadeIn transitionKey=\{step\}>/g) ?? [];
  assert.equal(matches.length, 4);
});

test('el overlay de alta/edición de equipo usa FadeIn, keyed por identidad del equipo', () => {
  assert.match(source, /<FadeIn transitionKey=\{equipmentEditor === 'new' \? 'new' : equipmentEditor\?\.id\}>/);
});
