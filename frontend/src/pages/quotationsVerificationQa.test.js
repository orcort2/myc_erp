import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const source = readFileSync(new URL('./QuotationsPage.jsx', import.meta.url), 'utf8');

test('Cotizaciones no crea ETS manualmente y ofrece abrir el ETS materializado', () => {
  assert.doesNotMatch(source, /createServiceOrder/);
  assert.doesNotMatch(source, /Generar orden de servicio/);
  assert.match(source, /selectedQuotation\.service_order_id/);
  assert.match(source, />\s*Ver ETS\s*</);
});

test('Verificación muestra y exige su Master genérico fuera del bloque de Calibración', () => {
  assert.match(source, /Master genérico de Verificación/);
  assert.match(source, /required=\{productForm\.operationalCategory === 'verification'\}/);
  assert.match(source, /Este Master se incluye inicialmente en el paquete de Captura/);
  assert.match(source, /Verificación no puede operar sin un Master genérico válido/);
});

test('Escape respeta ConfirmDialog y cierra primero el modal activo', () => {
  assert.match(source, /event\.key !== 'Escape' \|\| confirmDialog/);
  assert.match(source, /if \(unlockPreview\)[\s\S]*else if \(isCatalogImportOpen\)[\s\S]*else if \(isProductModalOpen\)[\s\S]*else if \(isClientPickerOpen\)[\s\S]*else if \(isDetailOpen\)/);
  assert.match(source, /removeEventListener\('keydown', handleEscape\)/);
});
