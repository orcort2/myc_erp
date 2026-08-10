import test from 'node:test';
import assert from 'node:assert/strict';

import { exceptionActionLabel } from './exceptionAuthority.js';


test('administrator also receives the request action', () => {
  assert.equal(exceptionActionLabel(), 'Solicitar excepción');
});

test('the label does not imply execution for any authority', () => {
  assert.equal(exceptionActionLabel(), 'Solicitar excepción');
});
