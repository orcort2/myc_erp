import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

/**
 * Cierre UX 2026-09 (item F): toda navegación "volver" pasa por el
 * BackButton compartido -- antes tickets.tsx, deliveries.tsx,
 * notifications.tsx, communications/index.tsx, communications/[id].tsx y
 * work-orders.tsx repetían su propio Pressable + router.back(), y
 * communications/index.tsx incluso etiquetaba ese comportamiento "‹ Inicio"
 * (semántica equivocada: Inicio navega a la raíz, Volver retrocede un paso).
 */
const root = resolve(dirname(fileURLToPath(import.meta.url)), '../..');

const screensThatMustUseBackButton = [
  'app/(technician)/tickets.tsx',
  'app/(technician)/deliveries.tsx',
  'app/(technician)/notifications.tsx',
  'app/(technician)/communications/index.tsx',
  'app/(technician)/communications/[id].tsx',
  'app/(technician)/work-orders.tsx',
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

test('el cierre del modal de OT usa CloseButton, distinto del BackButton de la lista', () => {
  const source = readFileSync(resolve(root, 'app/(technician)/work-orders.tsx'), 'utf8');
  assert.match(source, /<CloseButton disabled=\{deleting \|\| signatureSubmitRef\.current\} onPress=\{closeFlow\} \/>/);
});
