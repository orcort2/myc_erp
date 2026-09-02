import type { LabWorkOrderGroupRequest } from '@/src/types/lab-work-order';
import type { OperationalTicket } from '@/src/types/operational-ticket';

export type RequestInboxKind = 'all' | 'reopenings' | 'groups';

/** Cierre UX 2026-09: "Reaperturas" agrupa los dos tipos de ticket que
 * desbloquean trabajo ya cerrado -- reopen_work_order (OT completa) y
 * field_sheet_reopen (una sola hoja) -- sin mezclarlos con folio/cierre
 * parcial/plantilla, que son conceptos distintos. No son la misma
 * autoridad ni el mismo flujo de aprobación; sólo comparten la categoría
 * de filtro en esta bandeja. */
const REOPENING_TICKET_TYPES = new Set<OperationalTicket['type']>([
  'reopen_work_order',
  'field_sheet_reopen',
]);

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

/** El chip "Reaperturas" antes sólo ocultaba/mostraba TODA la sección de
 * tickets (visibleRequestKinds), sin filtrar por tipo -- folio, cierre
 * parcial y solicitud de plantilla aparecían igual bajo "Reaperturas". Este
 * filtro es el que de verdad distingue por tipo dentro de la sección. */
export function filterTicketsByKind(
  tickets: OperationalTicket[],
  kind: RequestInboxKind,
): OperationalTicket[] {
  if (kind !== 'reopenings') return tickets;
  return tickets.filter((item) => REOPENING_TICKET_TYPES.has(item.type));
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
