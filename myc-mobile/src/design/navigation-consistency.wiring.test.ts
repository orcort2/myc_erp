import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

/**
 * Cierre UX 2026-09 (item F): toda navegación "volver" pasa por el
 * BackButton compartido -- antes tickets.tsx, deliveries.tsx,
 * notifications.tsx, communications/index.tsx y communications/[id].tsx
 * repetían su propio Pressable + router.back(), y communications/index.tsx
 * incluso etiquetaba ese comportamiento "‹ Inicio" (semántica equivocada:
 * Inicio navega a la raíz, Volver retrocede un paso).
 *
 * work-orders.tsx quedó fuera de este barrido a propósito: su retrofit de
 * botones (BackButton/CloseButton/Primary/Secondary/Administrative/Danger)
 * se revirtió por completo a pedido explícito -- se detectaron leyendas
 * ausentes y espaciado roto entre grids/cards/encabezados en ese archivo.
 */
const root = resolve(dirname(fileURLToPath(import.meta.url)), '../..');

const screensThatMustUseBackButton = [
  'app/(technician)/tickets.tsx',
  'app/(technician)/deliveries.tsx',
  'app/(technician)/notifications.tsx',
  'app/(technician)/communications/index.tsx',
  'app/(technician)/communications/[id].tsx',
  'app/(technician)/clients.tsx',
];

for (const relativePath of screensThatMustUseBackButton) {
  test(`${relativePath} navega hacia atrás con el BackButton compartido, no un Pressable ad hoc`, () => {
    const source = readFileSync(resolve(root, relativePath), 'utf8');
    assert.match(source, /<BackButton/);
    assert.doesNotMatch(source, /Pressable[^>]*onPress=\{\(\) => router\.back\(\)\}/);
  });
}

test('ningún "Volver" queda etiquetado como "Inicio" (semántica de navegación)', () => {
  const source = readFileSync(resolve(root, 'app/(technician)/communications/index.tsx'), 'utf8');
  assert.doesNotMatch(source, /‹ Inicio/);
});
