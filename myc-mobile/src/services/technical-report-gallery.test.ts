import assert from 'node:assert/strict';
import test from 'node:test';

import {
  gridColumns,
  indexAfterDelete,
  neighborIndex,
  pageIndexFromOffset,
  planEvidenceGrid,
} from './technical-report-gallery';

test('3 columnas con ancho suficiente y 2 en pantallas estrechas', () => {
  assert.equal(gridColumns(430), 3);
  assert.equal(gridColumns(390), 3);
  assert.equal(gridColumns(360), 3);
  assert.equal(gridColumns(320), 2);
});

test('hasta caber (2 filas) se muestran todas las fotos más la celda Agregar', () => {
  assert.deepEqual(planEvidenceGrid({ count: 0, canAdd: true, columns: 3 }), { visiblePhotos: 0, overflow: 0, addCell: true, addButton: false });
  assert.deepEqual(planEvidenceGrid({ count: 5, canAdd: true, columns: 3 }), { visiblePhotos: 5, overflow: 0, addCell: true, addButton: false });
  assert.deepEqual(planEvidenceGrid({ count: 6, canAdd: false, columns: 3 }), { visiblePhotos: 6, overflow: 0, addCell: false, addButton: false });
});

test('con demasiadas fotos: capacidad-1 miniaturas y una celda +N; Agregar pasa a botón', () => {
  assert.deepEqual(planEvidenceGrid({ count: 9, canAdd: true, columns: 3 }), { visiblePhotos: 5, overflow: 4, addCell: false, addButton: true });
  assert.deepEqual(planEvidenceGrid({ count: 6, canAdd: true, columns: 3 }), { visiblePhotos: 5, overflow: 1, addCell: false, addButton: true });
  assert.deepEqual(planEvidenceGrid({ count: 9, canAdd: true, columns: 2 }), { visiblePhotos: 3, overflow: 6, addCell: false, addButton: true });
  // El límite backend de 20 por reporte cabe en una sola categoría sin romper el layout.
  assert.deepEqual(planEvidenceGrid({ count: 20, canAdd: false, columns: 3 }), { visiblePhotos: 5, overflow: 15, addCell: false, addButton: false });
});

test('navegación del visor: sin dar la vuelta y con selección válida tras borrar', () => {
  assert.equal(neighborIndex(0, -1, 5), 0);
  assert.equal(neighborIndex(4, 1, 5), 4);
  assert.equal(neighborIndex(2, 1, 5), 3);
  assert.equal(indexAfterDelete(0, 0), null);
  assert.equal(indexAfterDelete(2, 2), 1);
  assert.equal(indexAfterDelete(1, 3), 1);
  assert.equal(pageIndexFromOffset(780, 390, 5), 2);
  assert.equal(pageIndexFromOffset(5000, 390, 5), 4);
  assert.equal(pageIndexFromOffset(-20, 390, 5), 0);
  assert.equal(pageIndexFromOffset(100, 0, 5), 0);
});
