import assert from 'node:assert/strict';
import test from 'node:test';

import {
  catalogOperationalCategoryOptions,
  operationalCategoryFromCatalogForm
} from './catalog.js';

test('Tipo comercial no altera la categoría operacional Venta', () => {
  assert.equal(
    operationalCategoryFromCatalogForm({ type: 'Producto', operationalCategory: 'sale' }),
    'sale'
  );
  assert.equal(
    operationalCategoryFromCatalogForm({ type: 'Servicio', operationalCategory: 'sale' }),
    'sale'
  );
});

test('Producto conserva una categoría operacional distinta de Venta', () => {
  assert.equal(
    operationalCategoryFromCatalogForm({ type: 'Producto', operationalCategory: 'verification' }),
    'verification'
  );
});

test('el selector expone todas las identidades operacionales canónicas', () => {
  assert.deepEqual(
    catalogOperationalCategoryOptions.map((option) => option.value),
    [
      'calibration',
      'maintenance',
      'repair',
      'verification',
      'qualification',
      'validation',
      'training',
      'consulting',
      'general_service',
      'sale',
      'other'
    ]
  );
});
