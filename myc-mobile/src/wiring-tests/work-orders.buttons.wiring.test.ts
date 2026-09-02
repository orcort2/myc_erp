import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

/**
 * Cierre UX 2026-09 (item E): reabrir/restaurar/cancelar-preservando la OT
 * son operaciones administrativas/excepcionales -- no deben tener el mismo
 * peso visual que una acción secundaria común (compartir, descargar). Eliminar
 * sigue siendo la única acción realmente destructiva/irreversible.
 */
const source = readFileSync(
  resolve(dirname(fileURLToPath(import.meta.url)), '../../app/(technician)/work-orders.tsx'),
  'utf8',
);

test('reabrir directo y solicitar reapertura usan AdministrativeButton', () => {
  assert.match(source, /<AdministrativeButton label="Reabrir orden"/);
  assert.match(source, /<AdministrativeButton label="Solicitar reapertura"/);
});

test('restaurar OT usa AdministrativeButton con su propio estado de carga', () => {
  assert.match(source, /<AdministrativeButton label="Restaurar OT" loading=\{restoring\}/);
});

test('cancelar y conservar la OT es administrativo, no destructivo (es reversible vía Restaurar)', () => {
  assert.match(source, /<AdministrativeButton label="Cancelar y conservar OT"/);
});

test('eliminar la orden sigue siendo la única acción realmente destructiva (DangerButton)', () => {
  assert.match(source, /<DangerButton\s*\n\s*disabled=\{busy \|\| deleting\}\s*\n\s*label="Eliminar orden de trabajo"/);
});
