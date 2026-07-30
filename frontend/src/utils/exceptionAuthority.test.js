import test from 'node:test';
import assert from 'node:assert/strict';

import {
  exceptionActionLabel,
  hasDirectExceptionAuthority
} from './exceptionAuthority.js';


test('administrator executes exceptions directly without a request modal', () => {
  const administrator = { permissions: ['*'] };
  assert.equal(hasDirectExceptionAuthority(administrator), true);
  assert.equal(exceptionActionLabel(administrator), 'Aplicar excepción');
});

test('administrator role is recognized even when permissions are not hydrated', () => {
  const administrator = { roles: [{ name: 'Administrador' }] };
  assert.equal(hasDirectExceptionAuthority(administrator), true);
  assert.equal(exceptionActionLabel(administrator), 'Aplicar excepción');
});

test('lower authority keeps the request path', () => {
  const operator = { permissions: ['service_orders.read'] };
  assert.equal(hasDirectExceptionAuthority(operator), false);
  assert.equal(exceptionActionLabel(operator), 'Solicitar excepción');
});
