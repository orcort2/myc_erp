import assert from 'node:assert/strict';
import test from 'node:test';

import {
  canAccessModule,
  filterAccessibleEntries,
  hasAnyPermission,
  hasPermission,
} from './accessControl.js';

test('permissions support exact, scoped wildcard and administrator wildcard', () => {
  assert.equal(hasPermission({ permissions: ['clients.read'] }, 'clients.read'), true);
  assert.equal(hasPermission({ permissions: ['clients.*'] }, 'clients.update'), true);
  assert.equal(hasPermission({ permissions: ['*'] }, 'users.manage'), true);
  assert.equal(hasPermission({ permissions: ['clients.read'] }, 'users.manage'), false);
});

test('navigation exposes only capabilities returned by backend', () => {
  const entries = [
    { key: 'clients', permissions: ['clients.read'] },
    { key: 'settings', permissions: ['users.manage', 'audit_logs.read'] },
    { key: 'communications', permissions: [] },
  ];
  const user = { permissions: ['clients.read'] };
  assert.deepEqual(filterAccessibleEntries(entries, user).map((item) => item.key), [
    'clients',
    'communications',
  ]);
  assert.equal(canAccessModule(entries[1], user), false);
  assert.equal(hasAnyPermission(user, ['clients.update', 'clients.read']), true);
});
