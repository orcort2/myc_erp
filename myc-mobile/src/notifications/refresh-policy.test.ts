import assert from 'node:assert/strict';
import test from 'node:test';

import {
  affectsTickets,
  affectsWorkOrders,
  eventFromData,
  NotificationEventDeduper,
  resolveNotificationResponse,
  RefreshGate,
  targetFor,
} from './refresh-policy';

function notificationResponse(identifier: string, data: Record<string, unknown>) {
  return {
    notification: {
      request: {
        identifier,
        content: { data },
      },
    },
  };
}

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

test('targetFor resolves a communication, ticket or work order deep link', () => {
  assert.deepEqual(
    targetFor(eventFromData({ conversation_id: 7 }, 'push', 'id-1')),
    { pathname: '/(technician)/communications/[id]', params: { id: '7' } },
  );
  assert.deepEqual(
    targetFor(eventFromData({ ticket_id: 9 }, 'push', 'id-2')),
    { pathname: '/(technician)/tickets', params: { ticketId: '9' } },
  );
  assert.deepEqual(
    targetFor(eventFromData({ work_order_id: 42 }, 'push', 'id-3')),
    { pathname: '/(technician)/work-orders', params: { workOrderId: '42' } },
  );
  assert.equal(targetFor(eventFromData({}, 'push', 'id-4')), null);
});

// MOB-003: Notifications.getLastNotificationResponseAsync() keeps returning
// the same cached response until the app relaunches. resolveNotificationResponse
// is what NotificationSyncProvider.handleResponse relies on to make sure that
// re-processing that same stale response (same request.identifier) never
// resolves to a navigable target a second time — otherwise the app would
// bounce back to the same screen right after the user closed it.
test('the same notification response is only ever accepted once', () => {
  const deduper = new NotificationEventDeduper();
  const response = notificationResponse('resp-1', { work_order_id: 55 });

  const first = resolveNotificationResponse(response, deduper);
  assert.equal(first.accepted, true);
  assert.deepEqual(first.accepted && first.target, { pathname: '/(technician)/work-orders', params: { workOrderId: '55' } });

  const second = resolveNotificationResponse(response, deduper);
  assert.equal(second.accepted, false);

  // Simulate the listener-setup effect re-subscribing and re-querying
  // getLastNotificationResponseAsync() several more times (e.g. because of
  // unrelated re-renders): still must not re-accept the same response.
  for (let i = 0; i < 5; i += 1) {
    assert.equal(resolveNotificationResponse(response, deduper).accepted, false);
  }
});

test('a different notification response (new identifier) is still processed normally', () => {
  const deduper = new NotificationEventDeduper();
  const first = resolveNotificationResponse(notificationResponse('resp-a', { ticket_id: 1 }), deduper);
  const second = resolveNotificationResponse(notificationResponse('resp-b', { ticket_id: 2 }), deduper);
  assert.equal(first.accepted, true);
  assert.equal(second.accepted, true);
});

test('a response with no resolvable entity accepts but yields no navigation target', () => {
  const deduper = new NotificationEventDeduper();
  const resolution = resolveNotificationResponse(notificationResponse('resp-generic', {}), deduper);
  assert.equal(resolution.accepted, true);
  assert.equal(resolution.accepted && resolution.target, null);
});
