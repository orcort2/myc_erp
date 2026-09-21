import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

/**
 * BIOMETRIC-2: overscroll/rebote excesivo observado físicamente en iPhone --
 * el ScrollView principal de la Home técnica debe declarar las tres props
 * que lo desactivan en ambas plataformas.
 */
const source = readFileSync(
  resolve(dirname(fileURLToPath(import.meta.url)), '../../app/(technician)/index.tsx'),
  'utf8',
);

test('el ScrollView principal de la Home técnica desactiva el overscroll', () => {
  const block = source.slice(source.indexOf('<ScrollView'), source.indexOf('contentContainerStyle={styles.content}') + 1);
  assert.match(block, /bounces=\{false\}/);
  assert.match(block, /alwaysBounceVertical=\{false\}/);
  assert.match(block, /overScrollMode="never"/);
});
