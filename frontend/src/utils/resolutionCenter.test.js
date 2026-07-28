import assert from 'node:assert/strict';
import test from 'node:test';

import {
  canRunResolutionStage,
  shouldPollResolutions
} from './resolutionCenter.js';

test('polling runs only for visible active resolutions', () => {
  assert.equal(
    shouldPollResolutions([{ lifecycle_status: 'executing' }], 'visible'),
    true
  );
  assert.equal(
    shouldPollResolutions([{ lifecycle_status: 'completed' }], 'visible'),
    false
  );
  assert.equal(
    shouldPollResolutions([{ lifecycle_status: 'executing' }], 'hidden'),
    false
  );
});

test('stage permissions come only from backend capabilities', () => {
  const capabilities = {
    can_prepare: true,
    can_analyze: false,
    can_plan: true,
    can_simulate: true,
    can_authorize: false,
    can_execute: true
  };
  assert.equal(canRunResolutionStage('simulate', capabilities), true);
  assert.equal(canRunResolutionStage('analyze', capabilities), false);
  assert.equal(canRunResolutionStage('build-plan', capabilities), true);
  assert.equal(canRunResolutionStage('authorize', capabilities), false);
  assert.equal(canRunResolutionStage('execute', capabilities), true);
});
