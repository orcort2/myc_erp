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

test('Catálogo 2026: Calibración y Verificación se dan de alta sin selector de Master', () => {
  assert.doesNotMatch(source, /Master genérico de Verificación/);
  assert.doesNotMatch(source, /Plantilla esperada de certificado/);
  assert.doesNotMatch(source, /Selecciona el Master genérico de Verificación antes de guardar/);
  assert.doesNotMatch(source, /expectedCertificateMasterId/);
  assert.doesNotMatch(source, /certificateMasters/);
  // El catálogo ya no consulta Masters para un selector inexistente.
  assert.doesNotMatch(source, /document_type: 'certificate_master'/);
  // Legacy: el payload omite el campo para no borrar valores históricos al editar.
  assert.doesNotMatch(source, /expected_certificate_master_id:/);
});

test('Escape respeta ConfirmDialog y cierra primero el modal activo', () => {
  assert.match(source, /event\.key !== 'Escape' \|\| confirmDialog/);
  assert.match(source, /if \(unlockPreview\)[\s\S]*else if \(isCatalogImportOpen\)[\s\S]*else if \(isProductModalOpen\)[\s\S]*else if \(isClientPickerOpen\)[\s\S]*else if \(isDetailOpen\)/);
  assert.match(source, /removeEventListener\('keydown', handleEscape\)/);
});
