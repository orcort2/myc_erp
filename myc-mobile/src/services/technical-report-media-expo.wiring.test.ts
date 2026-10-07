import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '../..');
const read = (path: string) => readFileSync(resolve(root, path), 'utf8');

test('app.json configura expo-image-picker con textos de MYC y sin micrófono', () => {
  const config = JSON.parse(read('app.json')) as { expo: { plugins: unknown[] } };
  const entry = config.expo.plugins.find((plugin) => Array.isArray(plugin) && plugin[0] === 'expo-image-picker') as [string, Record<string, unknown>] | undefined;
  assert.ok(entry, 'plugin expo-image-picker');
  assert.equal(entry[1].photosPermission, 'MYC Mobile necesita acceso a tus fotos para adjuntar evidencia al reporte técnico.');
  assert.equal(entry[1].cameraPermission, 'MYC Mobile necesita acceso a la cámara para documentar evidencia del servicio.');
  assert.equal(entry[1].microphonePermission, false);
});

test('las dependencias son las resueltas por expo install y no se añadió expo-camera', () => {
  const pkg = JSON.parse(read('package.json')) as { dependencies: Record<string, string> };
  assert.match(pkg.dependencies['expo-image-picker'], /^~17\./);
  assert.match(pkg.dependencies['expo-image-manipulator'], /^~14\./);
  assert.equal(pkg.dependencies['expo-camera'], undefined);
});

test('el adaptador sólo usa picker/manipulator, normaliza a JPEG sin pedir EXIF ni base64, y se registra al arrancar', () => {
  const adapter = read('src/services/technical-report-media-expo.ts');
  assert.match(adapter, /SaveFormat\.JPEG/);
  assert.match(adapter, /exif: false/);
  assert.match(adapter, /base64: false/);
  assert.match(adapter, /allowsEditing: false/);
  assert.doesNotMatch(adapter, /Linking|openSettings/, 'no abre Ajustes automáticamente');
  assert.match(read('app/_layout.tsx'), /setEvidenceMediaProvider\(expoEvidenceMediaProvider\)/);
  // LabInstallationReport no conoce Expo.
  assert.doesNotMatch(read('src/components/lab/LabInstallationReport.tsx'), /expo-image-picker|expo-image-manipulator/);
});
