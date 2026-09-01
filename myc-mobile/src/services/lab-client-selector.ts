export type LabClientOption = {
  id: number;
  company: string;
  address: string;
  attention: string;
};

/** Máximo de resultados que el selector renderiza a la vez (Fase 2A: "no
 * mostrar cientos de registros simultáneamente"). El backend ya filtra por
 * término de búsqueda; esto es sólo el tope visual del propio selector. */
export const MAX_VISIBLE_RESULTS = 20;

export function limitVisibleResults(results: LabClientOption[]): LabClientOption[] {
  return results.slice(0, MAX_VISIBLE_RESULTS);
}

/** Query string para GET /lab-clients. include_inactive nunca se envía como
 * true desde la búsqueda normal del selector -- los clientes inactivos sólo
 * se listan desde una pantalla administrativa dedicada (fuera de esta fase). */
export function buildLabClientSearchQuery(term: string): string {
  const trimmed = term.trim();
  const params = new URLSearchParams();
  if (trimmed) params.set('search', trimmed);
  return params.toString();
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
