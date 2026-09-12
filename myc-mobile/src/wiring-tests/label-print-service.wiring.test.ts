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
 *
 * Los assertions toleran el formateo multilinea de Prettier/ESLint:
 * verifican estructura y orden semántico, no una representación textual
 * exacta de una sola línea.
 */

const source = readFileSync(
  resolve(
    dirname(fileURLToPath(import.meta.url)),
    '../services/label-print-service.ts',
  ),
  'utf8',
);

test('printLabel valida el payload (buildLabelLines) ANTES de tocar el estado de la impresora o enviar un trabajo BLE', () => {
  const functionStart = source.indexOf(
    'export async function printLabel',
  );

  assert.notEqual(
    functionStart,
    -1,
    'debe existir export async function printLabel',
  );

  const fn = source.slice(functionStart);

  const validationMatch = fn.match(
    /buildLabelLines\s*\(\s*payload\s*\)/,
  );

  const readyCheckMatch = fn.match(
    /printerManager\.isReady\s*\(\s*\)/,
  );

  const printCallMatch = fn.match(
    /printerManager\.print\s*\(\s*raster\s*,\s*options\s*,?\s*\)/,
  );

  assert.notEqual(
    validationMatch?.index,
    undefined,
    'printLabel debe validar buildLabelLines(payload)',
  );

  assert.notEqual(
    readyCheckMatch?.index,
    undefined,
    'printLabel debe comprobar printerManager.isReady()',
  );

  assert.notEqual(
    printCallMatch?.index,
    undefined,
    'printLabel debe delegar finalmente en printerManager.print(raster, options)',
  );

  const validationIndex = validationMatch?.index ?? -1;
  const readyCheckIndex = readyCheckMatch?.index ?? -1;
  const printCallIndex = printCallMatch?.index ?? -1;

  assert.ok(
    validationIndex < readyCheckIndex
      && readyCheckIndex < printCallIndex,
    'buildLabelLines debe correr antes que cualquier intento de conexión/impresión BLE',
  );
});

test('printLabel nunca imprime un placeholder -- ningún fallback de texto para certificateFolio en este archivo', () => {
  assert.doesNotMatch(
    source,
    /PENDIENTE/,
  );

  assert.doesNotMatch(
    source,
    /certificateFolio\s*\?\?/,
    'certificateFolio nunca debe tener un valor por defecto aquí',
  );
});

test('buildTestPrintPayload sigue usando un folio inconfundible con uno real (nunca formato MYCA-/MYCT-)', () => {
  const functionStart = source.indexOf(
    'export function buildTestPrintPayload',
  );

  assert.notEqual(
    functionStart,
    -1,
    'debe existir buildTestPrintPayload',
  );

  const fn = source.slice(functionStart);

  assert.match(
    fn,
    /certificateFolio\s*:\s*'PRUEBA MYC'/,
  );

  assert.doesNotMatch(
    fn,
    /certificateFolio\s*:\s*['"]MYC[AT]-/,
    'la etiqueta de prueba nunca debe aparentar un folio productivo MYCA/MYCT',
  );
});