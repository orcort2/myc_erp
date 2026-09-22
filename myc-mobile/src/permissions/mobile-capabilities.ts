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
  canResolveLabFolios: boolean;
  canResolveOwnLabFolios: boolean;
  canReopenFieldSheetDirectly: boolean;
  canOverrideReceptionDate: boolean;
  canRegisterLabDelivery: boolean;
  canVoidLabDelivery: boolean;
  canVoidLabEquipmentEntry: boolean;
  canRequestPartialDelivery: boolean;
  // DEV-0: gates the "Desarrollador" Home card/screen. The backend re-checks
  // developer.access + internal actor on every Developer call (see
  // require_internal_mobile_permission in security.py) -- this only decides
  // whether to offer the entry point.
  canAccessDeveloper: boolean;
};

export function deriveMobileCapabilities(user: AuthUser | null): MobileCapabilities {
  const permissions = user?.permissions ?? [];
  const hasLegacyLabAccess = hasPermission(permissions, 'lab_work_orders.use');
  return {
    canResolveOwnLabFolios: user?.actor_type === 'internal'
      && user.can_resolve_own_lab_folios === true
      && hasPermission(permissions, 'lab_folios.resolve'),
    canAccessMobile: hasPermission(permissions, 'mobile.access'),
    canAccessDeveloper: user?.actor_type === 'internal'
      && hasPermission(permissions, 'developer.access'),
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
    canResolveLabFolios: user?.actor_type === 'internal'
      && hasPermission(permissions, 'lab_folios.resolve'),
    // BUG fix 2026-09: reapertura/desbloqueo directo de UNA FieldSheet
    // completed (backend: reopen_lab_field_sheet_directly) reutiliza
    // exactamente lab_folios.resolve -- la misma autoridad que ya exige
    // resolve_operational_ticket para ejecutar el ticket
    // field_sheet_reopen (ver operational_tickets.py). Deliberadamente
    // igual a canResolveLabFolios; nombre propio para que
    // LabTechnicalCapture no dependa de un capability de folios para una
    // decisión de UX de FieldSheet.
    canReopenFieldSheetDirectly: user?.actor_type === 'internal'
      && hasPermission(permissions, 'lab_folios.resolve'),
    canOverrideReceptionDate: user?.actor_type === 'internal' && (
      hasPermission(permissions, 'work_orders.create')
      || hasPermission(permissions, 'lab_work_orders.use')
    ),
    canRegisterLabDelivery: user?.actor_type === 'internal' && hasLegacyLabAccess,
    canVoidLabDelivery: user?.actor_type === 'internal'
      && hasPermission(permissions, 'lab_work_orders.cancel'),
    // PENDIENTE 5 (encargo de corrección LAB): "Anular ingreso" de un equipo
    // usaba directamente canCancel (== hasPermission(lab_work_orders.cancel),
    // sin exigir actor interno) para gatear su UI. El backend
    // (POST .../equipment/{id}/void) sí exige actor_type == "internal" además
    // del permiso -- esta capability dedicada refleja esa misma autoridad
    // real, mismo patrón exacto que canVoidLabDelivery. lab_work_orders.cancel
    // sigue siendo la autoridad base; no se creó ningún permiso nuevo.
    canVoidLabEquipmentEntry: user?.actor_type === 'internal'
      && hasPermission(permissions, 'lab_work_orders.cancel'),
    // La entrega parcial es EXCEPCIONAL: sólo solicita autorización (ticket
    // type=partial_delivery); la aprobación reutiliza canReviewTickets
    // (tickets.review, mismo permiso ya usado por approve/reject de tickets).
    canRequestPartialDelivery: user?.actor_type === 'internal' && hasLegacyLabAccess,
  };
}

/** Presentación de la resolución; el endpoint vuelve a verificar autoridad. */
export function canResolveOperationalTicket(user: AuthUser | null, ticket: {
  type: string; status: string; requested_by_user_id: number;
} | null): boolean {
  if (!user || !ticket || ticket.status !== 'pending') return false;
  const capabilities = deriveMobileCapabilities(user);
  const canResolveType = ticket.type === 'reception_date_change'
    ? capabilities.canOverrideReceptionDate : capabilities.canResolveLabFolios;
  return canResolveType && (ticket.requested_by_user_id !== user.id || (
    capabilities.canResolveOwnLabFolios && ['linked_folio', 'manual_myc_folio'].includes(ticket.type)
  ));
}
