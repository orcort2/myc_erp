import type { LabWorkOrderGroupRequest } from '@/src/types/lab-work-order';
import type { OperationalTicket } from '@/src/types/operational-ticket';

export type RequestInboxKind = 'all' | 'reopenings' | 'groups';

export function actionableRequestCount(
  tickets: OperationalTicket[],
  groups: LabWorkOrderGroupRequest[],
  permissions: { canReviewTickets: boolean; canClaimGroups: boolean },
): number {
  const ticketCount = permissions.canReviewTickets
    ? tickets.filter((item) => item.status === 'pending').length
    : 0;
  const groupCount = permissions.canClaimGroups
    ? groups.filter((item) => item.status === 'pending').length
    : 0;
  return ticketCount + groupCount;
}

export function visibleRequestKinds(
  kind: RequestInboxKind,
): { showTickets: boolean; showGroups: boolean } {
  return {
    showTickets: kind !== 'groups',
    showGroups: kind !== 'reopenings',
  };
}

export function filterGroupRequests(
  groups: LabWorkOrderGroupRequest[],
  status: string,
  search: string,
): LabWorkOrderGroupRequest[] {
  const normalized = search.trim().toLocaleLowerCase('es-MX');
  return groups.filter((item) => {
    const statusMatches = status === 'all'
      || item.status === status
      || (status === 'in_progress' && item.status === 'in_review');
    const searchMatches = !normalized || [
      String(item.id),
      item.operator_client_name,
      item.requested_by_name,
      item.client_name,
      item.handled_by_name ?? '',
    ].some((value) => value.toLocaleLowerCase('es-MX').includes(normalized));
    return statusMatches && searchMatches;
  });
}
