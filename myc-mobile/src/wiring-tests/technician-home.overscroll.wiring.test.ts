import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

/**
 * Cierre UX post-BIOMETRIC-2: el hardening anterior (bounces={false},
 * alwaysBounceVertical={false}, overScrollMode="never") dejaba el scroll de
 * la Home técnica demasiado rígido/mecánico en iPhone físico. Se restauró la
 * física nativa de ScrollView; sólo se conserva ocultar el indicador.
 */
const source = readFileSync(
  resolve(dirname(fileURLToPath(import.meta.url)), '../../app/(technician)/index.tsx'),
  'utf8',
);

function scrollViewBlock(): string {
  const start = source.indexOf('<ScrollView');
  const end = source.indexOf('>', start) + 1;
  return source.slice(start, end);
}

test('el ScrollView principal de la Home técnica ya no fuerza bounces desactivados', () => {
  const block = scrollViewBlock();
  assert.doesNotMatch(block, /bounces=\{false\}/);
  assert.doesNotMatch(block, /alwaysBounceVertical=\{false\}/);
  assert.doesNotMatch(block, /overScrollMode="never"/);
});

test('el ScrollView principal de la Home técnica oculta el indicador de scroll', () => {
  const block = scrollViewBlock();
  assert.match(block, /showsVerticalScrollIndicator=\{false\}/);
});

test('el ScrollView principal conserva contentContainerStyle sin forzar flexGrow', () => {
  const block = scrollViewBlock();
  assert.match(block, /contentContainerStyle=\{styles\.content\}/);
  const contentBlock = source.slice(source.indexOf('content: {'), source.indexOf('content: {') + 200);
  assert.doesNotMatch(contentBlock, /flexGrow:\s*1/);
});
