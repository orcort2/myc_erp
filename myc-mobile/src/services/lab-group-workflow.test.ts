import assert from 'node:assert/strict';
import test from 'node:test';
import { buildLabWorkflowCreationPayload, reconcileMemberWorkflowModes, validGroupQuantity } from './lab-group-workflow';

for (const mode of ['group', 'equipment_by_equipment'] as const) {
  test(`apply all sends only the homogeneous contract: ${mode}`, () => {
    assert.deepEqual(buildLabWorkflowCreationPayload('direct', mode, '4', false, ['group']), {
      workflow_mode: mode, quantity: 4,
    });
  });
  test(`individual creation keeps its historical payload: ${mode}`, () => {
    assert.deepEqual(buildLabWorkflowCreationPayload('none', mode, '', true, ['group']), { workflow_mode: mode });
  });
  test(`entering manual initializes every position from ${mode}`, () => {
    assert.deepEqual(reconcileMemberWorkflowModes([], 5, mode), Array(5).fill(mode));
  });
}

test('manual payload preserves order and snapshots the array', () => {
  const modes = reconcileMemberWorkflowModes(['equipment_by_equipment', 'group'], 4, 'equipment_by_equipment');
  const body = buildLabWorkflowCreationPayload('direct', 'group', '4', true, modes);
  assert.deepEqual(body, { workflow_mode: 'group', quantity: 4,
    member_workflow_modes: ['equipment_by_equipment', 'group', 'equipment_by_equipment', 'equipment_by_equipment'] });
  assert.notEqual(body.member_workflow_modes, modes);
});

test('quantity grows preserving exceptions, shrinks, then uses the new base for new positions', () => {
  const initial = reconcileMemberWorkflowModes(['group', 'equipment_by_equipment'], 4, 'group');
  assert.deepEqual(initial, ['group', 'equipment_by_equipment', 'group', 'group']);
  const smaller = reconcileMemberWorkflowModes(initial, 2, 'group');
  assert.deepEqual(smaller, ['group', 'equipment_by_equipment']);
  assert.deepEqual(reconcileMemberWorkflowModes(smaller, 4, 'equipment_by_equipment'),
    ['group', 'equipment_by_equipment', 'equipment_by_equipment', 'equipment_by_equipment']);
});

test('changing the base resets every manual position before configuring new exceptions', () => {
  let manual = reconcileMemberWorkflowModes(['group', 'equipment_by_equipment', 'group'], 3, 'group');
  assert.deepEqual(manual, ['group', 'equipment_by_equipment', 'group']);
  manual = reconcileMemberWorkflowModes([], 3, 'equipment_by_equipment');
  assert.deepEqual(manual, ['equipment_by_equipment', 'equipment_by_equipment', 'equipment_by_equipment']);
  assert.deepEqual(reconcileMemberWorkflowModes(manual, 4, 'equipment_by_equipment'),
    ['equipment_by_equipment', 'equipment_by_equipment', 'equipment_by_equipment', 'equipment_by_equipment']);
});

test('returning to apply all omits any manual configuration', () => {
  assert.deepEqual(buildLabWorkflowCreationPayload('direct', 'group', '2', false, ['equipment_by_equipment', 'group']),
    { workflow_mode: 'group', quantity: 2 });
});

test('external requests never send per-member configuration', () => {
  assert.deepEqual(buildLabWorkflowCreationPayload('request', 'group', '2', true, ['equipment_by_equipment', 'group']),
    { workflow_mode: 'group', quantity: 2 });
});

test('inconsistent manual arrays cannot be submitted', () => {
  for (const modes of [[], ['group'], ['group', 'group', 'group']] as const) {
    assert.throws(() => buildLabWorkflowCreationPayload('direct', 'group', '2', true, modes));
  }
});

test('invalid quantities do not allocate controls or permit group submission', () => {
  for (const value of ['', '0', '-1', '51', '2.5', 'abc', 'Infinity']) {
    assert.equal(validGroupQuantity(value), null);
    assert.deepEqual(reconcileMemberWorkflowModes([], Number(value), 'group'), []);
    assert.throws(() => buildLabWorkflowCreationPayload('direct', 'group', value, false, []));
  }
  assert.equal(validGroupQuantity('1'), 1);
  assert.equal(validGroupQuantity('50'), 50);
});
