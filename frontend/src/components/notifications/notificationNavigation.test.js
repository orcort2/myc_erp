import assert from 'node:assert/strict';
import test from 'node:test';

import { getNotificationDestination } from './notificationNavigation.js';

test('notification destinations use structured entity identity', () => {
  assert.equal(
    getNotificationDestination({
      entity_type: 'conversation',
      entity_id: 5,
    }),
    '/communications?conversation_id=5',
  );

  assert.equal(
    getNotificationDestination({
      entity_type: 'service_order',
      entity_id: 21,
    }),
    '/dashboard?service_order_id=21#servicios',
  );

  assert.equal(
    getNotificationDestination({
      entity_type: 'work_order_group_request',
      entity_id: 17,
    }),
    '/communications',
  );

  assert.equal(
    getNotificationDestination({
      entity_type: 'ticket',
      entity_id: 8,
    }),
    '/communications',
  );

  assert.equal(
    getNotificationDestination({
      entity_type: 'work_order',
      entity_id: 12,
    }),
    '/communications',
  );

  assert.equal(
    getNotificationDestination({
      entity_type: 'lab_work_order',
      entity_id: 33,
    }),
    '/communications',
  );
});

test('explicit backend path remains authoritative and unknown entities fall back safely', () => {
  assert.equal(
    getNotificationDestination({
      metadata_json: {
        frontend_path: '/communications?conversation_id=4',
      },
    }),
    '/communications?conversation_id=4',
  );

  assert.equal(
    getNotificationDestination({
      entity_type: 'not_implemented',
      entity_id: 2,
    }),
    '/communications',
  );
});