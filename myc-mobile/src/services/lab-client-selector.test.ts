import assert from 'node:assert/strict';
import test from 'node:test';

import {
  applyCreatedClient,
  buildLabClientSearchQuery,
  cancelInlineCreate,
  initialSelectorState,
  limitVisibleResults,
  MAX_VISIBLE_RESULTS,
  openInlineCreate,
  selectClient,
  shouldResetFormAfterSubmit,
} from './lab-client-selector';
import type { LabClientOption } from './lab-client-selector';

function client(id: number): LabClientOption {
  return { id, company: `Cliente ${id}`, address: '', attention: '' };
}

test('1. la búsqueda arma el query contra el backend por término (empresa/atención/dirección ya cubiertos ahí)', () => {
  assert.equal(buildLabClientSearchQuery('Saverglass'), 'search=Saverglass');
  assert.equal(buildLabClientSearchQuery('  '), '');
  assert.equal(buildLabClientSearchQuery(''), '');
});

test('14. la búsqueda normal nunca solicita clientes inactivos', () => {
  const query = buildLabClientSearchQuery('Cliente');
  assert.equal(query.includes('include_inactive'), false);
});

test('el selector nunca renderiza más de MAX_VISIBLE_RESULTS de golpe', () => {
  const many = Array.from({ length: 200 }, (_, index) => client(index));
  const visible = limitVisibleResults(many);
  assert.equal(visible.length, MAX_VISIBLE_RESULTS);
  assert.equal(visible[0].id, 0);
});

test('2. seleccionar un cliente de la lista fija selectedClientId', () => {
  const state = selectClient(initialSelectorState(), 5);
  assert.equal(state.selectedClientId, 5);
});

test('3. abrir "+ Crear cliente" no descarta el término/resultados de búsqueda previos', () => {
  const searching = { ...initialSelectorState(), searchTerm: 'Saverglass', results: [client(1)] };
  const creating = openInlineCreate(searching);
  assert.equal(creating.mode, 'create');
  assert.equal(creating.searchTerm, 'Saverglass');
  assert.deepEqual(creating.results, [client(1)]);
});

test('cancelar la creación inline regresa exactamente al estado de búsqueda previo', () => {
  const searching = { ...initialSelectorState(), searchTerm: 'Saverglass', results: [client(1)], selectedClientId: 1 };
  const creating = openInlineCreate(searching);
  const cancelled = cancelInlineCreate(creating);
  assert.deepEqual(cancelled, searching);
});

test('6. guardar el cliente inline vuelve a búsqueda con el nuevo cliente ya seleccionado', () => {
  const creating = openInlineCreate({ ...initialSelectorState(), searchTerm: 'Nuevo', results: [client(1)] });
  const created = client(99);
  const applied = applyCreatedClient(creating, created);
  assert.equal(applied.mode, 'search');
  assert.equal(applied.selectedClientId, 99);
  assert.equal(applied.searchTerm, 'Nuevo'); // no se reinicia el formulario de búsqueda
  assert.deepEqual(applied.results[0], created);
});

test('12. un error de backend nunca autoriza a limpiar el formulario, sólo un éxito', () => {
  assert.equal(shouldResetFormAfterSubmit('error'), false);
  assert.equal(shouldResetFormAfterSubmit('success'), true);
});
