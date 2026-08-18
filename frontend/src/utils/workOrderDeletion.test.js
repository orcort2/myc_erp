import assert from 'node:assert/strict';
import test from 'node:test';

import { canDeleteWorkOrder } from './workOrderDeletion.js';

test('la eliminación de OT sólo se muestra con la capacidad administrativa', () => {
  assert.equal(canDeleteWorkOrder({ permissions: ['*'] }), true);
  assert.equal(
    canDeleteWorkOrder({ permissions: ['service_orders.delete'] }),
    true,
  );
  assert.equal(canDeleteWorkOrder({ permissions: ['service_orders.read'] }), false);
  assert.equal(canDeleteWorkOrder({ permissions: ['service_orders.update'] }), false);
  assert.equal(canDeleteWorkOrder(null), false);
});
