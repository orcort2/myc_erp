/**
 * Estado de carga de listas remotas de MYC Mobile (OT, tickets, clientes).
 *
 * Distingue la primera carga de un refetch para que una revalidación
 * (filtro, focus, realtime, renovación de sesión, pull-to-refresh) nunca
 * desmonte datos ya válidos:
 *
 * - SIN datos previos para la identidad actual → `initialLoading` (spinner).
 * - CON datos → `refetching` (fondo) o `pullRefreshing` (RefreshControl);
 *   la lista permanece renderizada.
 * - Error durante un refetch → los datos se conservan; el error se muestra
 *   aparte.
 * - Paginación → `loadingMore` sólo afecta "Cargar más".
 *
 * `loadedFor` ata los datos a la identidad real (`user.id`): un cambio de
 * usuario vuelve a la primera carga y exige descartar los datos previos,
 * mientras que una renovación de token del mismo usuario es sólo un refetch.
 */
export type ListLoadState = {
  loadedFor: number | null;
  initialLoading: boolean;
  refetching: boolean;
  pullRefreshing: boolean;
  loadingMore: boolean;
};

export type ListFetchTrigger = 'background' | 'pull' | 'more';

export function initialListLoadState(): ListLoadState {
  return { loadedFor: null, initialLoading: true, refetching: false, pullRefreshing: false, loadingMore: false };
}

export type ListFetchPlan = {
  next: ListLoadState;
  /** true cuando los datos en memoria pertenecen a otra identidad y deben descartarse. */
  discardData: boolean;
};

export function beginListFetch(state: ListLoadState, trigger: ListFetchTrigger, identity: number): ListFetchPlan {
  if (state.loadedFor !== identity) {
    return {
      next: { loadedFor: null, initialLoading: true, refetching: false, pullRefreshing: false, loadingMore: false },
      discardData: state.loadedFor !== null,
    };
  }
  if (trigger === 'more') return { next: { ...state, loadingMore: true }, discardData: false };
  if (trigger === 'pull') return { next: { ...state, pullRefreshing: true }, discardData: false };
  return { next: { ...state, refetching: true }, discardData: false };
}

/** Sólo la petición más reciente liquida el estado (ver secuencia en cada pantalla). */
export function settleListFetch(state: ListLoadState, outcome: 'success' | 'error', identity: number): ListLoadState {
  return {
    loadedFor: outcome === 'success' ? identity : state.loadedFor,
    initialLoading: false,
    refetching: false,
    pullRefreshing: false,
    loadingMore: false,
  };
}

/** El spinner de pantalla completa sólo existe mientras no hay datos para la identidad actual. */
export function showsInitialSpinner(state: ListLoadState): boolean {
  return state.initialLoading && state.loadedFor === null;
}

/** "Cargar más" nunca compite con una recarga completa en curso: su offset quedaría obsoleto. */
export function canLoadMore(state: ListLoadState): boolean {
  return !state.initialLoading && !state.refetching && !state.pullRefreshing && !state.loadingMore;
}
