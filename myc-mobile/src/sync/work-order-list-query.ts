/**
 * Consulta server-side del listado de OT LAB (búsqueda `q` + estado + página).
 *
 * La búsqueda nunca se resuelve filtrando localmente la página visible: el
 * backend pagina, así que cada cambio de `q`/estado es una consulta nueva que
 * arranca en offset 0 y REEMPLAZA la lista. "Cargar más" sólo anexa cuando la
 * página cargada pertenece exactamente a la misma consulta.
 *
 * El backend confirma que aplicó `q` con la cabecera
 * `X-MYC-Search-Applied: q`. Un servidor que no conoce `q` lo ignora en
 * silencio (FastAPI descarta parámetros desconocidos) y devolvería el
 * listado completo como si fuera el resultado de la búsqueda; ese desfase de
 * versión se reporta en lugar de mostrarse como resultado.
 */
export const WORK_ORDER_SEARCH_DEBOUNCE_MS = 400;
export const SEARCH_APPLIED_HEADER = 'X-MYC-Search-Applied';

export type WorkOrderListStatus = 'all' | 'open' | 'completed';

export type WorkOrderListQuery = {
  status: WorkOrderListStatus;
  /** Texto ya recortado y con debounce aplicado. */
  q: string;
};

export type WorkOrderListPage = {
  append: boolean;
  offset: number;
};

export function workOrderListKey(query: WorkOrderListQuery): string {
  return JSON.stringify([query.status, query.q]);
}

export function buildWorkOrderListPath(
  query: WorkOrderListQuery,
  page: WorkOrderListPage,
  limit: number,
): string {
  const params = [
    `limit=${limit}`,
    `offset=${page.offset}`,
    `status=${query.status}`,
    query.q ? `q=${encodeURIComponent(query.q)}` : '',
  ].filter(Boolean).join('&');
  return `/mobile/v1/technician/lab-work-orders?${params}`;
}

/**
 * `more` anexa sólo sobre la misma consulta ya cargada; cualquier otro caso
 * (nueva búsqueda, nuevo estado, recarga) reinicia en offset 0 y reemplaza.
 */
export function planWorkOrderListPage(input: {
  trigger: 'background' | 'pull' | 'more';
  requestedKey: string;
  loadedKey: string | null;
  loadedCount: number;
}): WorkOrderListPage {
  if (input.trigger === 'more' && input.loadedKey === input.requestedKey) {
    return { append: true, offset: input.loadedCount };
  }
  return { append: false, offset: 0 };
}

export function mergeWorkOrderPage<T>(current: T[], next: T[], page: WorkOrderListPage): T[] {
  return page.append ? [...current, ...next] : next;
}

export function searchIgnoredByServer(query: WorkOrderListQuery, appliedHeader: string | null): boolean {
  return Boolean(query.q) && appliedHeader !== 'q';
}

export function emptyListMessage(query: WorkOrderListQuery): string {
  return query.q
    ? `Sin resultados para “${query.q}”.`
    : 'No hay órdenes que coincidan con los filtros.';
}
