import { hasPermission } from '@/src/permissions/permissions';
import type { AuthUser } from '@/src/types/auth';

export type MobileCapabilities = {
  canAccessMobile: boolean;
  canReadWorkOrders: boolean;
  canCreateWorkOrders: boolean;
  canExecuteWorkOrders: boolean;
  canCloseWorkOrders: boolean;
  canManageEquipment: boolean;
  canCaptureFieldSheets: boolean;
  canCaptureSignatures: boolean;
  canCreateTickets: boolean;
  canReadTickets: boolean;
  canReviewTickets: boolean;
  canUseCommunications: boolean;
  canRequestWorkOrderGroups: boolean;
  canCreateWorkOrderGroupsDirect: boolean;
  canReadWorkOrderGroupRequests: boolean;
  canClaimWorkOrderGroupRequests: boolean;
  canDecideWorkOrderGroupRequests: boolean;
  canDownloadLabPackages: boolean;
  canManageLabClients: boolean;
  canImportLabClients: boolean;
  canReadLabClients: boolean;
  canEditLabClients: boolean;
  canDeactivateLabClients: boolean;
};

export function deriveMobileCapabilities(user: AuthUser | null): MobileCapabilities {
  const permissions = user?.permissions ?? [];
  const hasLegacyLabAccess = hasPermission(permissions, 'lab_work_orders.use');
  return {
    canAccessMobile: hasPermission(permissions, 'mobile.access'),
    canReadWorkOrders: hasLegacyLabAccess
      || hasPermission(permissions, 'work_orders.read_organization'),
    canCreateWorkOrders: user?.actor_type === 'internal' && (
      hasLegacyLabAccess || hasPermission(permissions, 'work_orders.create')
    ),
    canExecuteWorkOrders: hasLegacyLabAccess
      || hasPermission(permissions, 'work_orders.execute'),
    // Fase 5 (corregido post-auditoría): cierre técnico (ready_to_close ->
    // completed) es autoridad exclusivamente interna de MYC -- ningún actor
    // externo/portal (Operativo Jr ni Sr) recibe work_orders.close; hoy sólo
    // staff interno vía lab_work_orders.use puede cerrar. Backend es la
    // autoridad real (ver app/routers/lab_work_orders.py); esto sólo evita
    // ofrecer un botón que el backend rechazará.
    canCloseWorkOrders: hasLegacyLabAccess
      || hasPermission(permissions, 'work_orders.close'),
    canManageEquipment: hasLegacyLabAccess
      || hasPermission(permissions, 'equipment.write'),
    // Fase 3: lab_field_sheets.capture es el permiso mínimo de Captura --
    // sólo habilita capturar FieldSheets LAB (después de received_signed),
    // deliberadamente distinto de field_sheets.capture/lab_work_orders.use
    // (esos también habilitan mutar equipo/servicio/cliente documental y
    // firmar/cerrar en el backend -- ver app/routers/lab_work_orders.py).
    canCaptureFieldSheets: hasLegacyLabAccess
      || hasPermission(permissions, 'field_sheets.capture')
      || hasPermission(permissions, 'lab_field_sheets.capture'),
    canCaptureSignatures: hasLegacyLabAccess
      || hasPermission(permissions, 'signatures.capture'),
    canCreateTickets: hasPermission(permissions, 'tickets.create')
      || hasPermission(permissions, 'mobile_tickets.create'),
    canReadTickets: hasPermission(permissions, 'tickets.view_own')
      || hasPermission(permissions, 'tickets.view_all')
      || hasPermission(permissions, 'mobile_tickets.read'),
    canReviewTickets: user?.actor_type === 'internal'
      && hasPermission(permissions, 'tickets.review'),
    canUseCommunications: Boolean(user && (
      user.actor_type === 'internal'
      || hasPermission(permissions, 'communications.view')
      || hasPermission(permissions, 'communications.create')
    )),
    canRequestWorkOrderGroups: user?.actor_type === 'client'
      && hasPermission(permissions, 'work_orders.group.request'),
    canCreateWorkOrderGroupsDirect: user?.actor_type === 'internal'
      && hasPermission(permissions, 'lab_work_order_groups.create'),
    canReadWorkOrderGroupRequests: user?.actor_type === 'internal'
      && hasPermission(permissions, 'lab_work_order_groups.requests.read'),
    canClaimWorkOrderGroupRequests: user?.actor_type === 'internal'
      && hasPermission(permissions, 'lab_work_order_groups.requests.claim'),
    canDecideWorkOrderGroupRequests: user?.actor_type === 'internal'
      && hasPermission(permissions, 'lab_work_order_groups.requests.decide'),
    canDownloadLabPackages: hasPermission(permissions, 'lab_packages.download')
      || hasPermission(permissions, 'work_orders.read_organization')
      || hasLegacyLabAccess,
    canManageLabClients: hasPermission(permissions, 'lab_clients.create')
      || hasPermission(permissions, 'work_orders.group.request')
      || hasLegacyLabAccess,
    canImportLabClients: user?.actor_type === 'internal'
      && hasPermission(permissions, 'lab_clients.import'),
    // Mismo permiso que exige el GET backend (lab_clients.py:20-34): read u
    // work_orders.read_organization -- gatea si "Clientes" aparece en Inicio.
    canReadLabClients: hasPermission(permissions, 'lab_clients.read')
      || hasPermission(permissions, 'work_orders.read_organization')
      || hasLegacyLabAccess,
    canEditLabClients: hasPermission(permissions, 'lab_clients.update')
      || hasLegacyLabAccess,
    // Cierre UX 2026-09: backend exige actor_type === 'internal' además de
    // este permiso explícito (lab_clients.py:79-101) -- deliberadamente sin
    // hasLegacyLabAccess aquí, mismo criterio restringido que el backend
    // (hoy sólo Administrador/Desarrollador lo tienen).
    canDeactivateLabClients: user?.actor_type === 'internal'
      && hasPermission(permissions, 'lab_clients.deactivate'),
  };
}
