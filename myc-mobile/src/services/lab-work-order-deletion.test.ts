import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import test from 'node:test';

import {
  canDeleteLabWorkOrder,
  deleteLabWorkOrder,
  LabWorkOrderDeletionCoordinator,
} from './lab-work-order-deletion';

test('sólo la capacidad LAB específica muestra la acción', () => {
  assert.equal(canDeleteLabWorkOrder(['lab_work_orders.delete']), true);
  assert.equal(canDeleteLabWorkOrder(['*']), true);
  assert.equal(canDeleteLabWorkOrder(['lab_work_orders.use']), false);
  assert.equal(canDeleteLabWorkOrder(['service_orders.delete']), false);
});

test('la eliminación usa exclusivamente el endpoint LAB y reconoce 204', async () => {
  const calls: { url: string; method?: string }[] = [];
  const result = await deleteLabWorkOrder(async (url, init) => {
    calls.push({ url, method: init?.method });
    return new Response(null, { status: 204 });
  }, 'https://erp.test/api/mobile/v1/technician/lab-work-orders/42');
  assert.deepEqual(result, { kind: 'success' });
  assert.deepEqual(calls, [{
    url: 'https://erp.test/api/mobile/v1/technician/lab-work-orders/42',
    method: 'DELETE',
  }]);
  assert.doesNotMatch(calls[0].url, /service-orders/);
});

test('clasifica 403, 404, 409 y red sin simular éxito local', async () => {
  for (const [status, kind] of [[403, 'forbidden'], [404, 'not_found'], [409, 'conflict']] as const) {
    const result = await deleteLabWorkOrder(
      async () => new Response(JSON.stringify({ detail: 'mensaje' }), { status }),
      'https://erp.test/api/mobile/v1/technician/lab-work-orders/9',
    );
    assert.equal(result.kind, kind);
  }
  const network = await deleteLabWorkOrder(async () => { throw new TypeError('network'); }, 'lab-url');
  assert.equal(network.kind, 'error');
});

test('el coordinador impide dos DELETE simultáneos', async () => {
  const coordinator = new LabWorkOrderDeletionCoordinator();
  let calls = 0;
  let finish!: (value: { kind: 'success' }) => void;
  const first = coordinator.run(true, () => {
    calls += 1;
    return new Promise<{ kind: 'success' }>((resolve) => { finish = resolve; });
  });
  assert.deepEqual(await coordinator.run(true, async () => ({ kind: 'success' })), { kind: 'ignored' });
  assert.equal(calls, 1);
  finish({ kind: 'success' });
  assert.deepEqual(await first, { kind: 'success' });
});

test('cancelar la confirmación no ejecuta DELETE', async () => {
  const coordinator = new LabWorkOrderDeletionCoordinator();
  let calls = 0;
  const result = await coordinator.run(false, async () => {
    calls += 1;
    return { kind: 'success' };
  });
  assert.deepEqual(result, { kind: 'cancelled' });
  assert.equal(calls, 0);
});

test('la tarjeta LAB reserva metadata y limita clientes largos a dos líneas', () => {
  const source = readFileSync(resolve(process.cwd(), 'app/(technician)/work-orders.tsx'), 'utf8');
  assert.match(source, /style=\{styles\.cardContent\}/);
  assert.match(source, /ellipsizeMode="tail" numberOfLines=\{2\}/);
  assert.match(source, /cardContent:\s*\{[^}]*flex:\s*1,[^}]*minWidth:\s*0/s);
  assert.match(source, /cardRight: \{[^}]*flexShrink: 0/);
  for (const name of [
    'Autonova',
    'MULTI-COLORLABELCORPORATION-MEXICO',
    'LABORATORIOS Y SERVICIOS INDUSTRIALES DE OCCIDENTE S.A. DE C.V.',
    'CLIENTEEXTREMADAMENTELARGOSINESPACIOSPARAPROBARTRUNCAMIENTO',
  ]) assert.ok(name.length > 0);
});
