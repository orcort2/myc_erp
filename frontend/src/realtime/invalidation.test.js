import assert from 'node:assert/strict';
import test from 'node:test';

import {
  invalidateResources,
  matchesInvalidation,
  subscribeInvalidations,
} from './invalidation.js';

test('notifica a los suscriptores activos', () => {
  const received = [];

  const unsubscribe = subscribeInvalidations((resources) => {
    received.push(resources);
  });

  invalidateResources(['users']);

  assert.deepEqual(received, [['users']]);

  unsubscribe();
  invalidateResources(['quotations']);

  assert.deepEqual(received, [['users']]);
});

test('permite invalidaciones globales', () => {
  assert.equal(matchesInvalidation(['*'], ['users']), true);
  assert.equal(matchesInvalidation(['users'], ['*']), true);
});

test('filtra recursos no relacionados', () => {
  assert.equal(matchesInvalidation(['users'], ['users']), true);
  assert.equal(matchesInvalidation(['users'], ['quotations']), false);
});
