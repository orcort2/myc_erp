import assert from 'node:assert/strict';
import test from 'node:test';

import { deriveMobileCapabilities } from './mobile-capabilities';
import type { AuthUser } from '../types/auth';

function user(
  actorType: AuthUser['actor_type'],
  permissions: string[],
): AuthUser {
  return {
    id: 1,
    email: 'mobile@example.com',
    full_name: 'Mobile User',
    is_active: true,
    permissions,
    actor_type: actorType,
    client_id: actorType === 'client' ? 10 : null,
    membership_id: actorType === 'client' ? 20 : null,
  };
}

test('mobile.access no concede capacidades operativas implícitas', () => {
  const capabilities = deriveMobileCapabilities(user('client', ['mobile.access']));
  assert.equal(capabilities.canAccessMobile, true);
  assert.equal(capabilities.canReadWorkOrders, false);
  assert.equal(capabilities.canCreateWorkOrders, false);
  assert.equal(capabilities.canManageEquipment, false);
  assert.equal(capabilities.canCaptureSignatures, false);
  assert.equal(capabilities.canUseCommunications, false);
  assert.equal(capabilities.canRequestWorkOrderGroups, false);
});

test('Viewer externo sólo habilita lectura organizacional', () => {
  const capabilities = deriveMobileCapabilities(user('client', [
    'mobile.access',
    'work_orders.read_organization',
    'equipment.read',
    'field_sheets.read',
  ]));
  assert.equal(capabilities.canReadWorkOrders, true);
  assert.equal(capabilities.canCreateWorkOrders, false);
  assert.equal(capabilities.canExecuteWorkOrders, false);
  assert.equal(capabilities.canCaptureFieldSheets, false);
});

for (const profile of ['Operativo Jr', 'Operativo Sr']) {
  test(`${profile} habilita operación sin facultades implícitas de folios`, () => {
    const permissions = [
      'mobile.access',
      'work_orders.read_organization',
      'work_orders.create',
      'work_orders.execute',
      'equipment.write',
      'field_sheets.capture',
      'signatures.capture',
      'mobile_tickets.create',
      'mobile_tickets.read',
    ];
    const capabilities = deriveMobileCapabilities(user('client', permissions));
    assert.equal(capabilities.canCreateWorkOrders, false);
    assert.equal(capabilities.canExecuteWorkOrders, true);
    assert.equal(capabilities.canManageEquipment, true);
    assert.equal(capabilities.canCaptureSignatures, true);
    assert.equal(permissions.some((permission) => permission.startsWith('folios.')), false);
  });
}

test('sólo la capacidad explícita habilita solicitudes de grupos anticipados', () => {
  assert.equal(deriveMobileCapabilities(user('client', ['work_orders.create'])).canRequestWorkOrderGroups, false);
  assert.equal(deriveMobileCapabilities(user('client', ['work_orders.group.request'])).canRequestWorkOrderGroups, true);
});

test('staff conserva compatibilidad LAB y Comunicaciones', () => {
  const capabilities = deriveMobileCapabilities(user('internal', [
    'mobile.access',
    'lab_work_orders.use',
  ]));
  assert.equal(capabilities.canReadWorkOrders, true);
  assert.equal(capabilities.canCreateWorkOrders, true);
  assert.equal(capabilities.canExecuteWorkOrders, true);
  assert.equal(capabilities.canUseCommunications, true);
});
