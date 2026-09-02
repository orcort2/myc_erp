import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

import {
  applyCreatedClient,
  buildLabClientListQuery,
  buildLabClientSearchQuery,
  cancelInlineCreate,
  initialSelectorState,
  limitVisibleResults,
  mergeLabClientPage,
  MAX_VISIBLE_RESULTS,
  openInlineCreate,
  selectClient,
  shouldSearchLabClients,
  shouldResetFormAfterSubmit,
} from './lab-client-selector';
import type { LabClientOption } from './lab-client-selector';

function client(id: number): LabClientOption {
  return {
    id, company: `Cliente ${id}`, address: '', attention: '',
    postal_code: null, city: null, state: null,
  };
}

test('1. la búsqueda arma el query contra el backend por término (empresa/atención/dirección ya cubiertos ahí)', () => {
  assert.equal(buildLabClientSearchQuery('Saverglass'), 'search=Saverglass&limit=5');
  assert.equal(buildLabClientSearchQuery('  '), '');
  assert.equal(buildLabClientSearchQuery(''), '');
  assert.equal(buildLabClientSearchQuery('a'), '');
  assert.equal(shouldSearchLabClients(' a '), false);
  assert.equal(shouldSearchLabClients(' au '), true);
});

test('14. la búsqueda normal nunca solicita clientes inactivos', () => {
  const query = buildLabClientSearchQuery('Cliente');
  assert.equal(query.includes('include_inactive'), false);
});

test('el módulo administrativo pagina 25 en backend y conserva búsqueda/include_inactive', () => {
  assert.equal(
    buildLabClientListQuery(' audi ', 25, true),
    'search=audi&limit=25&offset=25&include_inactive=true',
  );
  assert.equal(buildLabClientListQuery('', 0, false), 'limit=25&offset=0');
});

test('reset de búsqueda reemplaza la página y cargar más agrega sin duplicar', () => {
  assert.deepEqual(mergeLabClientPage([client(1)], [client(2)], false), [client(2)]);
  assert.deepEqual(
    mergeLabClientPage([client(1), client(2)], [client(2), client(3)], true).map((item) => item.id),
    [1, 2, 3],
  );
});

test('el módulo Clientes conecta búsqueda remota, páginas de 25 y Cargar más por offset', () => {
  const source = readFileSync(
    resolve(dirname(fileURLToPath(import.meta.url)), '../../app/(technician)/clients.tsx'),
    'utf8',
  );
  assert.match(source, /buildLabClientListQuery\(term, offset, includeInactive\)/);
  assert.match(source, /page\.length === LAB_CLIENTS_PAGE_SIZE/);
  assert.match(source, /label="Cargar más"/);
  assert.match(source, /results\.length, true/);
});

test('el toggle de inactivos sólo aparece para Admin cuando el conteo scoped es mayor que cero', () => {
  const source = readFileSync(
    resolve(dirname(fileURLToPath(import.meta.url)), '../../app/(technician)/clients.tsx'),
    'utf8',
  );
  assert.match(source, /if \(!canDeactivateLabClients\) return 0/);
  assert.match(source, /lab-clients\/inactive-count/);
  assert.match(source, /canDeactivateLabClients && inactiveCount > 0/);
  assert.match(source, /active && nextInactiveCount === 0 \? false : showInactive/);
  assert.match(source, /loadInactiveCount\(\)/);
});

test('el selector nunca renderiza más de MAX_VISIBLE_RESULTS de golpe', () => {
  const many = Array.from({ length: 200 }, (_, index) => client(index));
  const visible = limitVisibleResults(many);
  assert.equal(visible.length, MAX_VISIBLE_RESULTS);
  assert.equal(visible[0].id, 0);
});

test('cierre UX 2026-09: el máximo visible es exactamente 5, no una lista gigante', () => {
  assert.equal(MAX_VISIBLE_RESULTS, 5);
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
