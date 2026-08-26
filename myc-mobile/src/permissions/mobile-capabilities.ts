import { hasPermission } from '@/src/permissions/permissions';
import type { AuthUser } from '@/src/types/auth';

export type MobileCapabilities = {
  canAccessMobile: boolean;
  canReadWorkOrders: boolean;
  canCreateWorkOrders: boolean;
  canExecuteWorkOrders: boolean;
  canManageEquipment: boolean;
  canCaptureFieldSheets: boolean;
  canCaptureSignatures: boolean;
  canCreateTickets: boolean;
  canReadTickets: boolean;
  canUseCommunications: boolean;
  canRequestWorkOrderGroups: boolean;
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
    canManageEquipment: hasLegacyLabAccess
      || hasPermission(permissions, 'equipment.write'),
    canCaptureFieldSheets: hasLegacyLabAccess
      || hasPermission(permissions, 'field_sheets.capture'),
    canCaptureSignatures: hasLegacyLabAccess
      || hasPermission(permissions, 'signatures.capture'),
    canCreateTickets: hasPermission(permissions, 'tickets.create')
      || hasPermission(permissions, 'mobile_tickets.create'),
    canReadTickets: hasPermission(permissions, 'tickets.view_own')
      || hasPermission(permissions, 'mobile_tickets.read'),
    canUseCommunications: Boolean(user && (
      user.actor_type === 'internal'
      || hasPermission(permissions, 'communications.view')
      || hasPermission(permissions, 'communications.create')
    )),
    canRequestWorkOrderGroups: hasPermission(permissions, 'work_orders.group.request'),
  };
}
