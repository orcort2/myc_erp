import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const centerSource = readFileSync(new URL('./ResolutionCenterPage.jsx', import.meta.url), 'utf8');
const serviceOrdersSource = readFileSync(new URL('./ServiceOrdersPage.jsx', import.meta.url), 'utf8');

test('Centro presenta las seis vistas institucionales y herramientas declarativas', () => {
  for (const label of ['Pendientes', 'En revisión', 'Requieren autorización', 'Ejecutadas', 'Fallidas', 'Herramientas']) {
    assert.match(centerSource, new RegExp(label));
  }
  assert.match(centerSource, /definition\.family === 'administrative_tools'/);
  assert.doesNotMatch(centerSource, /definition\.domain === 'service_orders'/);
});

test('ETS normal enlaza al Centro y ya no invoca la baja directa', () => {
  assert.match(serviceOrdersSource, /Resolver baja o restauración/);
  assert.match(serviceOrdersSource, /family=administrative_tools/);
  assert.doesNotMatch(serviceOrdersSource, /deleteServiceOrder/);
  assert.doesNotMatch(serviceOrdersSource, /handleDeleteServiceOrder/);
});
