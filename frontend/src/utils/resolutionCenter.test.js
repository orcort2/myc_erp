import assert from 'node:assert/strict';
import test from 'node:test';

import {
  buildResolutionParameters,
  canRunResolutionStage,
  resolutionParameterFields,
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

test('versioned metadata builds fields and accepts only declared parameters', () => {
  const definition = {
    parameter_schema: {
      type: 'object',
      additionalProperties: false,
      required: ['reason'],
      properties: {
        reason: { type: 'string', title: 'Motivo' },
        severity: { type: 'integer', title: 'Severidad' }
      }
    }
  };

  assert.deepEqual(
    resolutionParameterFields(definition).map(({ name, required }) => ({
      name,
      required
    })),
    [
      { name: 'reason', required: true },
      { name: 'severity', required: false }
    ]
  );
  assert.deepEqual(
    buildResolutionParameters(definition, {
      reason: '  corrección requerida  ',
      severity: '3',
      arbitrary_command: 'delete'
    }),
    { reason: 'corrección requerida', severity: 3 }
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
