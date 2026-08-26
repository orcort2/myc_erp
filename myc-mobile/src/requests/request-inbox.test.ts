import assert from 'node:assert/strict';
import test from 'node:test';

import { actionableRequestCount, visibleRequestKinds } from './request-inbox';
import type { LabWorkOrderGroupRequest } from '../types/lab-work-order';
import type { OperationalTicket } from '../types/operational-ticket';

test('actionable count includes only pending entities the reviewer can process', () => {
  const tickets = [{ status: 'pending' }, { status: 'resolved' }] as OperationalTicket[];
  const groups = [{ status: 'pending' }, { status: 'in_review' }] as LabWorkOrderGroupRequest[];
  assert.equal(actionableRequestCount(tickets, groups, { canReviewTickets: true, canClaimGroups: true }), 2);
  assert.equal(actionableRequestCount(tickets, groups, { canReviewTickets: false, canClaimGroups: true }), 1);
});

test('request filters preserve separate reopening and group projections', () => {
  assert.deepEqual(visibleRequestKinds('all'), { showTickets: true, showGroups: true });
  assert.deepEqual(visibleRequestKinds('reopenings'), { showTickets: true, showGroups: false });
  assert.deepEqual(visibleRequestKinds('groups'), { showTickets: false, showGroups: true });
});
