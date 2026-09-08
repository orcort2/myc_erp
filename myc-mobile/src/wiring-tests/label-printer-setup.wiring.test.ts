import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

/**
 * Verificación de cableado de la pantalla de configuración de impresora de
 * etiquetas (mismo patrón de inspección estática que el resto de
 * wiring-tests de pantallas de app/(technician): estos archivos importan
 * react-native, que tsx/esbuild no puede transformar fuera de Metro -- se
 * inspecciona el código fuente como texto en vez de montar el componente).
 */
const source = readFileSync(
  resolve(dirname(fileURLToPath(import.meta.url)), '../../app/(technician)/label-printer-setup.tsx'),
  'utf8',
);

test('la pantalla exige canCaptureFieldSheets -- misma autoridad que ya gatea el botón de impresión en LabTechnicalCapture, sin permiso nuevo inventado', () => {
  assert.match(source, /if \(!capabilities\.canCaptureFieldSheets\) return <Redirect href="\/\(technician\)" \/>;/);
});

test('el escaneo nunca ofrece un dispositivo BLE desconocido como impresora', () => {
  const fn = source.slice(source.indexOf('const startScan'), source.indexOf('const connectTo'));
  assert.match(fn, /if \(classification\.kind === 'unknown'\) return;/);
});

test('el escaneo deduplica por id de dispositivo', () => {
  const fn = source.slice(source.indexOf('const startScan'), source.indexOf('const connectTo'));
  assert.match(fn, /seenDeviceIds\.current\.has\(classification\.device\.id\)/);
});

test('sólo un dispositivo con supportStatus "supported" ofrece "Conectar" -- protocol_pending nunca ofrece conexión real', () => {
  assert.match(source, /classification\.family\.supportStatus === 'supported' && \(\s*<PrimaryButton\s*label="Conectar"/);
  assert.doesNotMatch(source, /supportStatus === 'protocol_pending'[\s\S]{0,80}label="Conectar"/);
});

test('el diagnóstico NELKO es exclusivo de actor interno y nunca aparece para un dispositivo ya soportado', () => {
  const gateIndex = source.indexOf("classification.family.supportStatus === 'protocol_pending' && user.actor_type === 'internal'");
  assert.notEqual(gateIndex, -1);
});

test('connectAndRemember sólo se llama para un dispositivo reconocido y soportado -- nunca para protocol_pending/unknown', () => {
  // El tipo de estado `devices: RecognizedDevice[]` ya excluye "unknown" en
  // tiempo de compilación (ver startScan: un unknown nunca llega a
  // guardarse) -- lo único que queda por gatear en runtime es supportStatus.
  assert.match(source, /type RecognizedDevice = Extract<DeviceClassification, \{ kind: 'recognized' \}>;/);
  const fn = source.slice(source.indexOf('const connectTo'), source.indexOf('const runDiagnostics'));
  assert.match(fn, /if \(classification\.family\.supportStatus !== 'supported'\) return;/);
  assert.match(fn, /printerManager\.connectAndRemember\(classification\.family\.adapterId, classification\.device\)/);
});

test('la prueba de impresión usa buildTestPrintPayload -- nunca inventa un folio de certificado real', () => {
  const fn = source.slice(source.indexOf('const testPrint'), source.indexOf('const forget'));
  assert.match(fn, /printLabel\(buildTestPrintPayload\(\)\)/);
});

test('"Olvidar impresora" desconecta y borra la preferida vía PrinterManager.forget, nunca borra sólo el estado local', () => {
  const fn = source.slice(source.indexOf('const forget'), source.indexOf('if (isLoading)'));
  assert.match(fn, /await printerManager\.forget\(\)/);
});
