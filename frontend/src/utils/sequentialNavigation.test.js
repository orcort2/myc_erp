import assert from 'node:assert/strict';
import test from 'node:test';

import { getSequentialNavigationState } from './sequentialNavigation.js';
import { itemBelongsToWorkOrder } from './workOrderGroups.js';

test('recorre 1 → 2 → 3 → 2 sin navegación circular', () => {
  const itemIds = [1, 2, 3];
  let activeId = 1;
  const route = [activeId];

  for (const direction of ['next', 'next', 'previous']) {
    const navigation = getSequentialNavigationState(itemIds, activeId);
    activeId = direction === 'next' ? navigation.nextId : navigation.previousId;
    route.push(activeId);
  }

  assert.deepEqual(route, [1, 2, 3, 2]);
  assert.equal(getSequentialNavigationState(itemIds, 1).previousId, null);
  assert.equal(getSequentialNavigationState(itemIds, 3).nextId, null);
});

test('limita el contexto a la misma Orden de Trabajo', () => {
  const equipmentById = new Map([
    [1, { id: 1, work_order_id: 11, work_order_number: 7002 }],
    [2, { id: 2, work_order_id: 11, work_order_number: 7002 }],
    [3, { id: 3, work_order_id: 12, work_order_number: 7003 }],
  ]);
  const certificates = [
    { id: 101, equipment_id: 1 },
    { id: 102, equipment_id: 2 },
    { id: 103, equipment_id: 3 },
  ];

  const contextualIds = certificates
    .filter((certificate) => itemBelongsToWorkOrder(certificate, { id: 11, work_order_number: 7002 }, equipmentById))
    .map((certificate) => certificate.id);

  assert.deepEqual(contextualIds, [101, 102]);
});

