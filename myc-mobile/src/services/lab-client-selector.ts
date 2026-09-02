export type LabClientOption = {
  id: number;
  company: string;
  address: string;
  attention: string;
  postal_code: string | null;
  city: string | null;
  state: string | null;
};

/** Máximo de resultados que el selector renderiza a la vez (cierre UX
 * 2026-09: "máximo 5 resultados visibles", navegación táctil cómoda). El
 * backend ya filtra por término de búsqueda; esto es sólo el tope visual
 * del propio selector. */
export const MAX_VISIBLE_RESULTS = 5;
export const LAB_CLIENTS_PAGE_SIZE = 25;

export function limitVisibleResults(results: LabClientOption[]): LabClientOption[] {
  return results.slice(0, MAX_VISIBLE_RESULTS);
}

/** Query string para GET /lab-clients. include_inactive nunca se envía como
 * true desde la búsqueda normal del selector -- los clientes inactivos sólo
 * se listan desde una pantalla administrativa dedicada (fuera de esta fase). */
export function buildLabClientSearchQuery(term: string): string {
  const trimmed = term.trim();
  if (trimmed.length < 2) return '';
  const params = new URLSearchParams();
  params.set('search', trimmed);
  params.set('limit', String(MAX_VISIBLE_RESULTS));
  return params.toString();
}

export function shouldSearchLabClients(term: string): boolean {
  return term.trim().length >= 2;
}

export function buildLabClientListQuery(
  term: string,
  offset: number,
  includeInactive: boolean,
): string {
  const params = new URLSearchParams();
  const trimmed = term.trim();
  if (trimmed) params.set('search', trimmed);
  params.set('limit', String(LAB_CLIENTS_PAGE_SIZE));
  params.set('offset', String(offset));
  if (includeInactive) params.set('include_inactive', 'true');
  return params.toString();
}

export function mergeLabClientPage(
  current: LabClientOption[],
  page: LabClientOption[],
  append: boolean,
): LabClientOption[] {
  if (!append) return page;
  const seen = new Set(current.map((item) => item.id));
  return [...current, ...page.filter((item) => !seen.has(item.id))];
}

export type LabClientSelectorState = {
  mode: 'search' | 'create';
  searchTerm: string;
  results: LabClientOption[];
  selectedClientId: number | null;
};

export function initialSelectorState(): LabClientSelectorState {
  return { mode: 'search', searchTerm: '', results: [], selectedClientId: null };
}

/** Abrir "+ Crear cliente": sólo cambia el modo de la capa del selector.
 * Nunca toca el formulario que lo invocó (OT o equipo). */
export function openInlineCreate(state: LabClientSelectorState): LabClientSelectorState {
  return { ...state, mode: 'create' };
}

/** Cancelar la creación inline: vuelve exactamente al estado de búsqueda
 * previo -- mismo término, mismos resultados, misma selección previa. */
export function cancelInlineCreate(state: LabClientSelectorState): LabClientSelectorState {
  return { ...state, mode: 'search' };
}

/** Guardar el cliente inline: vuelve a 'search' con el nuevo cliente ya
 * seleccionado y visible en resultados, sin reiniciar el término de búsqueda. */
export function applyCreatedClient(
  state: LabClientSelectorState,
  created: LabClientOption,
): LabClientSelectorState {
  return {
    ...state,
    mode: 'search',
    selectedClientId: created.id,
    results: [created, ...state.results.filter((item) => item.id !== created.id)],
  };
}

export function selectClient(state: LabClientSelectorState, clientId: number): LabClientSelectorState {
  return { ...state, selectedClientId: clientId };
}

/** Fase 2 (errores backend no borran el formulario): un submit fallido nunca
 * autoriza a limpiar el formulario -- sólo un submit exitoso lo hace. Los
 * componentes de alta deben consultar esto en vez de resetear en el catch. */
export function shouldResetFormAfterSubmit(outcome: 'success' | 'error'): boolean {
  return outcome === 'success';
}
