import assert from 'node:assert/strict';
import test from 'node:test';

import { affectsTickets, affectsWorkOrders, NotificationEventDeduper, RefreshGate } from './refresh-policy';

test('ticket events invalidate ticket and related work-order resources', () => {
  const approved = { event_type: 'ticket.approved', entity_type: 'ticket', ticket_id: 12, work_order_id: 5, source: 'push' as const };
  assert.equal(affectsTickets(approved), true);
  assert.equal(affectsWorkOrders(approved), true);
  assert.equal(affectsTickets({ ...approved, event_type: 'ticket.rejected' }), true);
  assert.equal(affectsWorkOrders({ ...approved, event_type: 'ticket.signature_required' }), true);
});

test('foreground refetches active ticket and work-order screens', () => {
  const foreground = { event_type: 'app.foreground', source: 'foreground' as const };
  assert.equal(affectsTickets(foreground), true);
  assert.equal(affectsWorkOrders(foreground), true);
});

test('duplicate pushes are consumed once and do not create refresh loops', () => {
  const deduper = new NotificationEventDeduper();
  assert.equal(deduper.accept('push-12'), true);
  assert.equal(deduper.accept('push-12'), false);
  assert.equal(deduper.accept('push-13'), true);
});

test('focus and event refreshes are throttled while local mutation can force refresh', () => {
  const gate = new RefreshGate();
  assert.equal(gate.shouldRefresh(10_000), true);
  assert.equal(gate.shouldRefresh(10_100), false);
  assert.equal(gate.shouldRefresh(10_100, true), true);
  assert.equal(gate.shouldRefresh(11_200), true);
});
