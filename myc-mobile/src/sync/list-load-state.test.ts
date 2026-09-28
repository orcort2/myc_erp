import assert from 'node:assert/strict';
import test from 'node:test';

import {
  beginListFetch,
  canLoadMore,
  initialListLoadState,
  settleListFetch,
  showsInitialSpinner,
  type ListLoadState,
} from './list-load-state';

const USER = 7;

function loaded(): ListLoadState {
  const { next } = beginListFetch(initialListLoadState(), 'background', USER);
  return settleListFetch(next, 'success', USER);
}

test('sin datos previos, la primera carga muestra el spinner de pantalla', () => {
  const state = initialListLoadState();
  assert.equal(showsInitialSpinner(state), true);
  const { next, discardData } = beginListFetch(state, 'background', USER);
  assert.equal(discardData, false);
  assert.equal(showsInitialSpinner(next), true);
  assert.equal(next.refetching, false);
});

test('primera carga exitosa ata los datos a la identidad y apaga el spinner', () => {
  const state = loaded();
  assert.equal(state.loadedFor, USER);
  assert.equal(showsInitialSpinner(state), false);
});

test('refetch en fondo con datos válidos conserva la lista: nunca vuelve al spinner', () => {
  const { next, discardData } = beginListFetch(loaded(), 'background', USER);
  assert.equal(discardData, false);
  assert.equal(next.refetching, true);
  assert.equal(next.initialLoading, false);
  assert.equal(showsInitialSpinner(next), false);
});

test('pull-to-refresh usa su propio indicador y conserva la lista', () => {
  const { next } = beginListFetch(loaded(), 'pull', USER);
  assert.equal(next.pullRefreshing, true);
  assert.equal(next.refetching, false);
  assert.equal(showsInitialSpinner(next), false);
});

test('error durante un refetch conserva los datos del mismo usuario', () => {
  const { next } = beginListFetch(loaded(), 'background', USER);
  const settled = settleListFetch(next, 'error', USER);
  assert.equal(settled.loadedFor, USER);
  assert.equal(settled.refetching, false);
  assert.equal(showsInitialSpinner(settled), false);
});

test('error en la primera carga no deja un spinner eterno: muestra el área de contenido (error + reintento)', () => {
  const { next } = beginListFetch(initialListLoadState(), 'background', USER);
  const settled = settleListFetch(next, 'error', USER);
  assert.equal(settled.loadedFor, null);
  assert.equal(showsInitialSpinner(settled), false);
});

test('paginación: loadingMore sólo afecta "Cargar más" y no compite con una recarga', () => {
  const base = loaded();
  assert.equal(canLoadMore(base), true);
  const { next } = beginListFetch(base, 'more', USER);
  assert.equal(next.loadingMore, true);
  assert.equal(next.refetching, false);
  assert.equal(showsInitialSpinner(next), false);
  assert.equal(canLoadMore(next), false);
  assert.equal(canLoadMore(beginListFetch(base, 'background', USER).next), false);
  assert.equal(canLoadMore(beginListFetch(base, 'pull', USER).next), false);
});

test('la liquidación limpia todos los indicadores (la petición más reciente manda)', () => {
  const pulling = beginListFetch(loaded(), 'pull', USER).next;
  const superseded = beginListFetch(pulling, 'background', USER).next;
  const settled = settleListFetch(superseded, 'success', USER);
  assert.deepEqual(
    [settled.initialLoading, settled.refetching, settled.pullRefreshing, settled.loadingMore],
    [false, false, false, false],
  );
});

test('cambio real de usuario descarta los datos previos y vuelve a primera carga', () => {
  const { next, discardData } = beginListFetch(loaded(), 'background', 99);
  assert.equal(discardData, true);
  assert.equal(next.loadedFor, null);
  assert.equal(showsInitialSpinner(next), true);
});

test('cambio de usuario también convierte "Cargar más" en una primera carga (offset 0)', () => {
  const { next, discardData } = beginListFetch(loaded(), 'more', 99);
  assert.equal(discardData, true);
  assert.equal(next.loadingMore, false);
  assert.equal(next.initialLoading, true);
});

test('un error tras cambio de usuario nunca rehabilita los datos del usuario anterior', () => {
  const { next } = beginListFetch(loaded(), 'background', 99);
  const settled = settleListFetch(next, 'error', 99);
  assert.equal(settled.loadedFor, null);
});
