import assert from 'node:assert/strict';
import test from 'node:test';

import {
  resolveInvoiceConceptDescription,
} from './invoiceConceptDescription.js';

test('usa el nombre del servicio en un concepto nuevo', () => {
  assert.equal(
    resolveInvoiceConceptDescription({
      service_name: 'Calibración de manómetro',
      description: 'Tiempo de entrega de 3 a 5 dias habiles',
    }),
    'Calibración de manómetro'
  );
});

test('conserva una descripción fiscal personalizada', () => {
  assert.equal(
    resolveInvoiceConceptDescription(
      { service_name: 'Calibración de manómetro' },
      { description: 'Servicio de calibración de manómetro digital' }
    ),
    'Servicio de calibración de manómetro digital'
  );
});

test('no comparte descripciones entre partidas', () => {
  const items = [
    { service_name: 'Calibración de báscula' },
    { service_name: 'Calibración de termómetro' },
  ];

  assert.deepEqual(
    items.map((item) => resolveInvoiceConceptDescription(item)),
    ['Calibración de báscula', 'Calibración de termómetro']
  );
});
