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

test('Fase 5: Operativo Jr no adquiere autoridad de cierre técnico (work_orders.close)', () => {
  // Perfil real de external_operator_jr (backend/app/services/portal/permission_service.py):
  // conserva work_orders.execute (operación ordinaria/captura) pero nunca work_orders.close.
  const capabilities = deriveMobileCapabilities(user('client', [
    'mobile.access',
    'work_orders.read_organization',
    'work_orders.execute',
    'equipment.read',
    'equipment.write',
    'field_sheets.read',
    'field_sheets.capture',
    'field_sheet_templates.read',
    'lab_clients.read',
    'lab_clients.create',
    'signatures.capture',
    'mobile_tickets.create',
    'mobile_tickets.read',
  ]));
  assert.equal(capabilities.canExecuteWorkOrders, true);
  assert.equal(capabilities.canCaptureFieldSheets, true);
  assert.equal(capabilities.canCaptureSignatures, true);
  assert.equal(capabilities.canCloseWorkOrders, false);
});

test('Fase 5 (corregido post-auditoría): Operativo Sr externo hereda las capacidades de Jr pero NUNCA cierre técnico interno', () => {
  // Perfil real de external_operator_sr (backend/app/services/portal/permission_service.py):
  // mismas capacidades de Jr más work_orders.group.request/communications --
  // work_orders.close es cierre técnico interno de MYC y no se le asigna a
  // ningún rol externo/portal, ni Jr ni Sr. Tampoco adquiere capacidades
  // reservadas a actor_type === 'internal' (grupos directos, importación de
  // clientes LAB, revisión de tickets, etc.), ni un wildcard '*'.
  const capabilities = deriveMobileCapabilities(user('client', [
    'mobile.access',
    'work_orders.read_organization',
    'work_orders.execute',
    'work_orders.group.request',
    'communications.view',
    'communications.create',
    'equipment.read',
    'equipment.write',
    'field_sheets.read',
    'field_sheets.capture',
    'field_sheet_templates.read',
    'lab_clients.read',
    'lab_clients.create',
    'signatures.capture',
    'mobile_tickets.create',
    'mobile_tickets.read',
  ]));
  assert.equal(capabilities.canExecuteWorkOrders, true);
  assert.equal(capabilities.canCaptureFieldSheets, true);
  assert.equal(capabilities.canCloseWorkOrders, false);
  assert.equal(capabilities.canRequestWorkOrderGroups, true);
  // Capacidades exclusivas de staff interno: nunca se conceden a un actor 'client'.
  assert.equal(capabilities.canCreateWorkOrderGroupsDirect, false);
  assert.equal(capabilities.canReadWorkOrderGroupRequests, false);
  assert.equal(capabilities.canClaimWorkOrderGroupRequests, false);
  assert.equal(capabilities.canDecideWorkOrderGroupRequests, false);
  assert.equal(capabilities.canImportLabClients, false);
  assert.equal(capabilities.canReviewTickets, false);
});

test('sólo la capacidad explícita habilita solicitudes de grupos anticipados', () => {
  assert.equal(deriveMobileCapabilities(user('client', ['work_orders.create'])).canRequestWorkOrderGroups, false);
  assert.equal(deriveMobileCapabilities(user('client', ['work_orders.group.request'])).canRequestWorkOrderGroups, true);
  assert.equal(deriveMobileCapabilities(user('internal', ['*'])).canRequestWorkOrderGroups, false);
});

test('creación directa de grupo exige actor internal y permiso explícito', () => {
  assert.equal(deriveMobileCapabilities(user('client', ['lab_work_order_groups.create'])).canCreateWorkOrderGroupsDirect, false);
  assert.equal(deriveMobileCapabilities(user('internal', ['lab_work_order_groups.create'])).canCreateWorkOrderGroupsDirect, true);
  assert.equal(deriveMobileCapabilities(user('internal', ['*'])).canCreateWorkOrderGroupsDirect, true);
});

test('permisos productivos genéricos de Captura (field_sheets.create/update) no filtran a capacidades LAB', () => {
  // Perfil real del rol Captura (app/core/permissions.py): incluye field_sheets.create
  // y field_sheets.update para el ERP Web productivo, pero ninguno de los códigos
  // que el motor LAB exige para mutar (lab_work_orders.use, work_orders.execute/create,
  // equipment.write, field_sheets.capture, signatures.capture).
  const capabilities = deriveMobileCapabilities(user('internal', [
    'mobile.access',
    'work_orders.read_organization',
    'lab_packages.download',
    'lab_clients.read',
    'field_sheets.read',
    'field_sheets.create',
    'field_sheets.update',
  ]));
  assert.equal(capabilities.canReadWorkOrders, true);
  assert.equal(capabilities.canDownloadLabPackages, true);
  assert.equal(capabilities.canCreateWorkOrders, false);
  assert.equal(capabilities.canExecuteWorkOrders, false);
  assert.equal(capabilities.canManageEquipment, false);
  assert.equal(capabilities.canCaptureFieldSheets, false);
  assert.equal(capabilities.canCaptureSignatures, false);
  assert.equal(capabilities.canCreateWorkOrderGroupsDirect, false);
});

test('Fase 2: Captura no ve el alta integrada de equipo (mismo gate que "Añadir equipo")', () => {
  // La nueva pantalla de alta integrada (equipo + cliente documental + servicio)
  // se gatea con la MISMA capacidad canManageEquipment que ya usa "+ Añadir
  // equipo" -- no se introduce una capacidad nueva más permisiva.
  const capabilities = deriveMobileCapabilities(user('internal', [
    'mobile.access',
    'work_orders.read_organization',
    'field_sheets.create',
    'field_sheets.update',
  ]));
  assert.equal(capabilities.canManageEquipment, false);
});

test('Fase 2 hardening: el mismo gate bloquea también abrir "Editar equipo" (LabEquipmentForm mode=edit)', () => {
  // showEquipmentEditor(item) para un equipo YA guardado usa la misma
  // capacidad canManageEquipment que el alta -- un usuario sin permisos no
  // puede abrir el formulario de edición, ni siquiera en modo lectura.
  const capabilities = deriveMobileCapabilities(user('internal', [
    'mobile.access',
    'work_orders.read_organization',
    'field_sheets.create',
    'field_sheets.update',
  ]));
  assert.equal(capabilities.canManageEquipment, false);
});

test('staff conserva compatibilidad LAB y Comunicaciones', () => {
  const capabilities = deriveMobileCapabilities(user('internal', [
    'mobile.access',
    'lab_work_orders.use',
  ]));
  assert.equal(capabilities.canReadWorkOrders, true);
  assert.equal(capabilities.canCreateWorkOrders, true);
  assert.equal(capabilities.canExecuteWorkOrders, true);
  assert.equal(capabilities.canCloseWorkOrders, true);
  assert.equal(capabilities.canUseCommunications, true);
});

test('cierre UX 2026-09: canReadLabClients gatea la tarjeta Clientes en Inicio', () => {
  const withRead = deriveMobileCapabilities(user('internal', ['mobile.access', 'lab_clients.read']));
  assert.equal(withRead.canReadLabClients, true);

  const withOrgRead = deriveMobileCapabilities(user('internal', ['mobile.access', 'work_orders.read_organization']));
  assert.equal(withOrgRead.canReadLabClients, true);

  const withoutEither = deriveMobileCapabilities(user('internal', ['mobile.access']));
  assert.equal(withoutEither.canReadLabClients, false);
});

test('cierre UX 2026-09: canEditLabClients requiere lab_clients.update explícito (o legado lab_work_orders.use)', () => {
  const withUpdate = deriveMobileCapabilities(user('internal', ['mobile.access', 'lab_clients.update']));
  assert.equal(withUpdate.canEditLabClients, true);

  const withOnlyCreate = deriveMobileCapabilities(user('internal', ['mobile.access', 'lab_clients.create']));
  assert.equal(withOnlyCreate.canEditLabClients, false);

  const legacy = deriveMobileCapabilities(user('internal', ['mobile.access', 'lab_work_orders.use']));
  assert.equal(legacy.canEditLabClients, true);
});
