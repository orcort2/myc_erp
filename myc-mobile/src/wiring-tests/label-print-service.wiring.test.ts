import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

/**
 * label-print-service.ts es el único archivo que conecta las 3 capas
 * reales entre sí (BleManagerTransport nativo, adaptadores concretos,
 * persistencia real) -- importarlo directamente en un test de Node arrastra
 * transitivamente 'react-native' (confirmado: tsx/esbuild no puede
 * transformar react-native/index.js fuera de Metro). Mismo patrón de
 * inspección estática que el resto de wiring-tests del proyecto.
 *
 * AUDITORÍA 2026-09-08: corrección de la regla de negocio de INFORME --
 * una etiqueta final sólo se imprime con certificateFolio real, nunca un
 * placeholder. Este archivo fija que printLabel nunca toca BLE
 * (printerManager.print) antes de validar el payload.
 */
const source = readFileSync(
  resolve(dirname(fileURLToPath(import.meta.url)), '../services/label-print-service.ts'),
  'utf8',
);

test('printLabel valida el payload (buildLabelLines) ANTES de tocar el estado de la impresora o enviar un trabajo BLE', () => {
  const fn = source.slice(source.indexOf('export async function printLabel'), source.length);
  const validationIndex = fn.indexOf('buildLabelLines(payload)');
  const readyCheckIndex = fn.indexOf('printerManager.isReady()');
  const printCallIndex = fn.indexOf('printerManager.print(raster, options)');
  assert.notEqual(validationIndex, -1);
  assert.notEqual(readyCheckIndex, -1);
  assert.notEqual(printCallIndex, -1);
  assert.ok(
    validationIndex < readyCheckIndex && readyCheckIndex < printCallIndex,
    'buildLabelLines debe correr antes que cualquier intento de conexión/impresión BLE',
  );
});

test('printLabel nunca imprime un placeholder -- ningún fallback de texto para certificateFolio en este archivo', () => {
  assert.doesNotMatch(source, /PENDIENTE/);
  assert.doesNotMatch(source, /certificateFolio\s*\?\?/, 'certificateFolio nunca debe tener un valor por defecto aquí');
});

test('buildTestPrintPayload sigue usando un folio inconfundible con uno real (nunca formato MYCA-/MYCT-)', () => {
  const fn = source.slice(source.indexOf('export function buildTestPrintPayload'), source.length);
  assert.match(fn, /certificateFolio: 'PRUEBA MYC'/);
});
