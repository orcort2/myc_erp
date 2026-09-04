import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

// Deep link a una OT cerrada (work_order.completed / notificaciones): audita
// que work-orders.tsx abre por workOrderId vía fetch directo, no vía el
// listado paginado, y que un param obsoleto nunca reabre en loop.

const workOrdersPath = resolve(
  dirname(fileURLToPath(import.meta.url)),
  '../../app/(technician)/work-orders.tsx',
);

const source = readFileSync(workOrdersPath, 'utf8');

test('el efecto de deep link lee workOrderId de los params y llama a openExisting una sola vez por id', () => {
  const effectStart = source.indexOf('const openedDeepLinkId = useRef<number | null>(null);');
  assert.notEqual(effectStart, -1);
  const effectBlock = source.slice(effectStart, source.indexOf('}, [params.workOrderId, user]);') + 30);

  assert.match(effectBlock, /const id = Number\(params\.workOrderId\);/);
  assert.match(effectBlock, /if \(id > 0 && user && openedDeepLinkId\.current !== id\)/);
  assert.match(effectBlock, /openedDeepLinkId\.current = id;/);
  assert.match(effectBlock, /openExisting\(id\);/);

  // openedDeepLinkId nunca se resetea a null -- cerrar el modal no debe
  // hacer que el mismo workOrderId stale reabra en loop.
  assert.doesNotMatch(source, /openedDeepLinkId\.current\s*=\s*null/);
});

test('openExisting hace fetch directo por ID -- nunca depende del listado paginado', () => {
  const fnStart = source.indexOf('async function openExisting(id: number) {');
  assert.notEqual(fnStart, -1);
  const fnBody = source.slice(fnStart, source.indexOf('\n  }\n', fnStart));

  assert.match(fnBody, /request<LabWorkOrder>\(`\/mobile\/v1\/technician\/lab-work-orders\/\$\{id\}`\)/);
  // No debe filtrar/buscar dentro de ningún arreglo de la primera página
  // (items/results/list) antes de decidir si la OT existe.
  assert.doesNotMatch(fnBody, /\.find\(|\.filter\(|items\[|results\[/);
});

test('openExisting maneja el fallo de fetch (404/403) mostrando una alerta, sin dejar el flujo colgado', () => {
  const fnStart = source.indexOf('async function openExisting(id: number) {');
  const fnBody = source.slice(fnStart, source.indexOf('\n  }\n', fnStart));

  assert.match(fnBody, /try \{/);
  assert.match(fnBody, /catch \(error\) \{/);
  assert.match(fnBody, /Alert\.alert\('No fue posible abrir la OT'/);
  assert.match(fnBody, /\} finally \{\s*setBusy\(false\);/);
});

test('openExisting no gatea por status -- completed y cancelled abren igual, la autorización la resuelve el backend', () => {
  const fnStart = source.indexOf('async function openExisting(id: number) {');
  const fnBody = source.slice(fnStart, source.indexOf('\n  }\n', fnStart));

  assert.doesNotMatch(fnBody, /detail\.status === 'cancelled'/);
  assert.doesNotMatch(fnBody, /detail\.status === 'completed'/);
  assert.match(fnBody, /setWorkOrder\(detail\);/);
});
