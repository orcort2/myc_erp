import assert from 'node:assert/strict';
import test from 'node:test';

import {
  buildWorkOrderListPath,
  emptyListMessage,
  mergeWorkOrderPage,
  planWorkOrderListPage,
  searchIgnoredByServer,
  workOrderListKey,
} from './work-order-list-query';

const search = { status: 'all', q: '6438' } as const;

test('la request incluye q codificado, estado y la página solicitada', () => {
  assert.equal(
    buildWorkOrderListPath({ status: 'open', q: 'cliente ejemplo' }, { append: false, offset: 0 }, 25),
    '/mobile/v1/technician/lab-work-orders?limit=25&offset=0&status=open&q=cliente%20ejemplo',
  );
  assert.equal(
    buildWorkOrderListPath({ status: 'all', q: '' }, { append: false, offset: 0 }, 25),
    '/mobile/v1/technician/lab-work-orders?limit=25&offset=0&status=all',
  );
});

test('una búsqueda nueva reinicia offset a 0 aunque el disparo sea "Cargar más"', () => {
  const previous = workOrderListKey({ status: 'all', q: '' });
  assert.deepEqual(
    planWorkOrderListPage({ trigger: 'background', requestedKey: workOrderListKey(search), loadedKey: previous, loadedCount: 25 }),
    { append: false, offset: 0 },
  );
  // Carrera: "Cargar más" pulsado justo cuando cambia q -> nunca anexa a la consulta anterior.
  assert.deepEqual(
    planWorkOrderListPage({ trigger: 'more', requestedKey: workOrderListKey(search), loadedKey: previous, loadedCount: 25 }),
    { append: false, offset: 0 },
  );
});

test('"Cargar más" conserva la misma consulta q y continúa en el offset cargado', () => {
  const key = workOrderListKey(search);
  const page = planWorkOrderListPage({ trigger: 'more', requestedKey: key, loadedKey: key, loadedCount: 25 });
  assert.deepEqual(page, { append: true, offset: 25 });
  assert.match(buildWorkOrderListPath(search, page, 25), /offset=25&status=all&q=6438$/);
});

test('cambiar el estado mantiene q y es una consulta distinta', () => {
  const open = { status: 'open', q: '6438' } as const;
  assert.notEqual(workOrderListKey(open), workOrderListKey(search));
  assert.match(buildWorkOrderListPath(open, { append: false, offset: 0 }, 25), /status=open&q=6438$/);
});

test('un cambio de q reemplaza items; sólo "Cargar más" anexa', () => {
  assert.deepEqual(mergeWorkOrderPage([1, 2, 3], [9], { append: false, offset: 0 }), [9]);
  assert.deepEqual(mergeWorkOrderPage([1, 2], [3], { append: true, offset: 2 }), [1, 2, 3]);
  assert.deepEqual(mergeWorkOrderPage([1, 2], [], { append: false, offset: 0 }), []);
});

test('limpiar la búsqueda vuelve al listado normal sin q', () => {
  const cleared = { status: 'all', q: '' } as const;
  assert.doesNotMatch(buildWorkOrderListPath(cleared, { append: false, offset: 0 }, 25), /q=/);
  assert.equal(searchIgnoredByServer(cleared, null), false);
  assert.equal(emptyListMessage(cleared), 'No hay órdenes que coincidan con los filtros.');
});

test('un servidor que ignora q en silencio se detecta en vez de mostrarse como resultado', () => {
  assert.equal(searchIgnoredByServer(search, null), true);
  assert.equal(searchIgnoredByServer(search, 'q'), false);
  assert.equal(emptyListMessage(search), 'Sin resultados para “6438”.');
});
