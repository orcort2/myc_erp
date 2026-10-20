import assert from 'node:assert/strict';
import test from 'node:test';

import {
  captureEvidenceImage,
  createEvidenceMediaProvider,
  EvidencePermissionError,
  EvidenceProcessingError,
  type EvidenceImagePipelineDeps,
} from './technical-report-image-pipeline';
import type { EvidenceSource } from './technical-report-media';

type Handle = { width: number; height: number; uri: string };

function fakeDeps(overrides: Partial<EvidenceImagePipelineDeps<Handle>> & {
  original?: { width: number; height: number };
  /** Tamaño en bytes del JPEG resultante de cada guardado, en orden. */
  sizes?: (number | null)[];
  granted?: boolean;
  cancelled?: boolean;
  pickedUri?: string;
} = {}) {
  const calls = { permission: [] as EvidenceSource[], pick: [] as EvidenceSource[], load: [] as string[], resize: [] as { width: number; height: number }[], save: [] as number[] };
  const sizes = [...(overrides.sizes ?? [300_000])];
  const original = overrides.original ?? { width: 4032, height: 3024 };
  const deps: EvidenceImagePipelineDeps<Handle> = {
    async requestPermission(source) { calls.permission.push(source); return { granted: overrides.granted ?? true }; },
    async pick(source) { calls.pick.push(source); return overrides.cancelled ? null : { uri: overrides.pickedUri ?? 'file:///original.heic' }; },
    async load(uri) { calls.load.push(uri); return { ...original, uri }; },
    async resize(image, size) { calls.resize.push(size); return { ...size, uri: image.uri }; },
    async saveJpeg(image, quality) { calls.save.push(quality); return { uri: `file:///processed-${calls.save.length}.jpg`, width: image.width, height: image.height }; },
    async fileSize() { return sizes.length > 1 ? sizes.shift()! : sizes[0] ?? null; },
    fileName: () => 'evidencia-1.jpg',
    ...overrides,
  };
  return { deps, calls };
}

test('permiso de cámara concedido: solicita cámara, abre el selector y entrega la imagen procesada', async () => {
  const { deps, calls } = fakeDeps();
  const result = await captureEvidenceImage('camera', deps);
  assert.deepEqual(calls.permission, ['camera']);
  assert.deepEqual(calls.pick, ['camera']);
  assert.ok(result);
});

test('permiso de cámara denegado: error coherente, sin abrir el selector', async () => {
  const { deps, calls } = fakeDeps({ granted: false });
  await assert.rejects(captureEvidenceImage('camera', deps), (error: Error) => {
    assert.ok(error instanceof EvidencePermissionError);
    assert.match(error.message, /cámara/);
    assert.match(error.message, /Ajustes/);
    return true;
  });
  assert.deepEqual(calls.pick, []);
});

test('permiso de galería concedido y denegado', async () => {
  const granted = fakeDeps();
  assert.ok(await captureEvidenceImage('library', granted.deps));
  assert.deepEqual(granted.calls.permission, ['library']);
  const denied = fakeDeps({ granted: false });
  await assert.rejects(captureEvidenceImage('library', denied.deps), (error: Error) => {
    assert.ok(error instanceof EvidencePermissionError);
    assert.match(error.message, /fotos/);
    return true;
  });
  assert.deepEqual(denied.calls.pick, []);
});

test('cancelar el selector devuelve null y no procesa nada', async () => {
  const { deps, calls } = fakeDeps({ cancelled: true });
  assert.equal(await captureEvidenceImage('camera', deps), null);
  assert.deepEqual(calls.load, []);
  assert.deepEqual(calls.save, []);
});

test('JPEG normal: salida JPEG con nombre y mime coherentes, sin depender del nombre original', async () => {
  const { deps } = fakeDeps({ pickedUri: 'file:///IMG_9999.JPG', original: { width: 1200, height: 800 }, sizes: [200_000] });
  const result = await captureEvidenceImage('library', deps);
  assert.ok(result);
  assert.equal(result.mimeType, 'image/jpeg');
  assert.equal(result.fileName, 'evidencia-1.jpg');
  assert.match(result.fileName, /\.jpg$/);
  assert.ok(!result.uri.includes('IMG_9999'));
  assert.equal(result.sizeBytes, 200_000);
});

test('HEIC se convierte a JPEG: el original nunca se sube, sólo el archivo procesado', async () => {
  const { deps, calls } = fakeDeps({ pickedUri: 'file:///IMG_0001.HEIC' });
  const result = await captureEvidenceImage('library', deps);
  assert.ok(result);
  assert.deepEqual(calls.load, ['file:///IMG_0001.HEIC']);
  assert.equal(result.mimeType, 'image/jpeg');
  assert.match(result.uri, /processed-1\.jpg$/);
  assert.notEqual(result.uri, 'file:///IMG_0001.HEIC');
  assert.match(result.fileName, /\.jpg$/);
});

test('apaisada y vertical se reducen a 1800 px de lado mayor conservando proporción', async () => {
  const landscape = fakeDeps({ original: { width: 4032, height: 3024 } });
  await captureEvidenceImage('camera', landscape.deps);
  assert.deepEqual(landscape.calls.resize, [{ width: 1800, height: 1350 }]);
  const portrait = fakeDeps({ original: { width: 3024, height: 4032 } });
  const result = await captureEvidenceImage('camera', portrait.deps);
  assert.deepEqual(portrait.calls.resize, [{ width: 1350, height: 1800 }]);
  assert.deepEqual([result!.width, result!.height], [1350, 1800]);
});

test('una imagen pequeña no se agranda ni se redimensiona', async () => {
  const { deps, calls } = fakeDeps({ original: { width: 800, height: 600 } });
  const result = await captureEvidenceImage('library', deps);
  assert.deepEqual(calls.resize, []);
  assert.deepEqual([result!.width, result!.height], [800, 600]);
});

test('compresión: calidad inicial 0.75 y se detiene al caber en 500 KiB', async () => {
  const { deps, calls } = fakeDeps({ sizes: [480 * 1024] });
  await captureEvidenceImage('camera', deps);
  assert.deepEqual(calls.save, [0.75]);
});

test('si excede 500 KiB hay como máximo tres pasos acotados, siempre desde el original', async () => {
  const { deps, calls } = fakeDeps({ sizes: [900 * 1024, 700 * 1024, 600 * 1024] });
  const result = await captureEvidenceImage('camera', deps);
  assert.deepEqual(calls.save, [0.75, 0.6, 0.6]);
  assert.deepEqual(calls.resize, [{ width: 1800, height: 1350 }, { width: 1800, height: 1350 }, { width: 1400, height: 1050 }]);
  assert.equal(calls.save.length, 3, 'nunca un cuarto paso');
  assert.equal(result!.sizeBytes, 600 * 1024, 'se entrega el último intento aunque siga > 500 KiB');
  assert.equal(calls.load.length, 1, 'el original se carga una sola vez');
});

test('el segundo paso basta si ya cabe', async () => {
  const { deps, calls } = fakeDeps({ sizes: [800 * 1024, 400 * 1024] });
  const result = await captureEvidenceImage('camera', deps);
  assert.deepEqual(calls.save, [0.75, 0.6]);
  assert.equal(result!.sizeBytes, 400 * 1024);
});

test('tamaño desconocido: no recomprime a ciegas', async () => {
  const { deps, calls } = fakeDeps({ sizes: [null] });
  const result = await captureEvidenceImage('camera', deps);
  assert.deepEqual(calls.save, [0.75]);
  assert.equal(result!.sizeBytes, null);
});

test('un resultado por encima de la barrera dura de 5 MiB falla de forma visible', async () => {
  const { deps } = fakeDeps({ sizes: [9 * 1024 * 1024] });
  await assert.rejects(captureEvidenceImage('camera', deps), EvidenceProcessingError);
});

test('fallo de manipulación: error visible y entendible, sin imagen parcial', async () => {
  const { deps } = fakeDeps({ async saveJpeg() { throw new Error('native failure'); } });
  await assert.rejects(captureEvidenceImage('library', deps), (error: Error) => {
    assert.ok(error instanceof EvidenceProcessingError);
    assert.match(error.message, /No fue posible preparar la foto/);
    assert.equal((error.cause as Error).message, 'native failure');
    return true;
  });
});

test('el proveedor expone cámara y galería y delega en el pipeline', async () => {
  const { deps, calls } = fakeDeps();
  const provider = createEvidenceMediaProvider(deps);
  assert.deepEqual([...provider.availableSources], ['camera', 'library']);
  assert.ok(await provider.capture('library'));
  assert.deepEqual(calls.pick, ['library']);
});
