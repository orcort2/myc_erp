import assert from 'node:assert/strict';
import test from 'node:test';

import { MYC_50X30, profileCanvasPx, profileSafeAreaPx } from '../label-profile';
import { renderLabel } from '../label-renderer';
import type { LabLabelPayload, RasterLabel } from '../label-types';
import { cropRasterToPrintableWidth, RasterExceedsPrintableWidthError } from './raster-adapt';

const NIIMBOT_B1_PRINTABLE_WIDTH_PX = 384;

const PAYLOAD: LabLabelPayload = {
  calibrationDate: '2026-09-01',
  nextCalibrationDate: '2027-09-01',
  equipmentCode: 'ID-1',
  workOrderFolio: '12345',
  certificateFolio: 'MYCA-0001',
};

function packedPixelAt(row: Uint8Array, x: number): boolean {
  const byteIndex = Math.floor(x / 8);
  const bitIndex = 7 - (x % 8);
  return ((row[byteIndex] ?? 0) >> bitIndex & 1) === 1;
}

function blankRaster(widthPx: number, heightPx: number): RasterLabel {
  const stride = Math.ceil(widthPx / 8);
  return {
    widthPx,
    heightPx,
    bitmap: { widthPx, heightPx, rows: Array.from({ length: heightPx }, () => new Uint8Array(stride)) },
    profileId: 'TEST',
  };
}

function setPixel(raster: RasterLabel, x: number, y: number): void {
  const byteIndex = Math.floor(x / 8);
  const bitIndex = 7 - (x % 8);
  raster.bitmap.rows[y][byteIndex] |= 1 << bitIndex;
}

test('MYC_50X30 sigue siendo 50x30 físico, 1mm de margen -- sin regresión por este cambio', () => {
  assert.equal(MYC_50X30.physicalWidthMm, 50);
  assert.equal(MYC_50X30.physicalHeightMm, 30);
  assert.equal(MYC_50X30.safeMarginMm, 1);
});

test('a 203 dpi el lienzo físico sigue siendo ~400x240 -- sin regresión por este cambio', () => {
  assert.deepEqual(profileCanvasPx(MYC_50X30, 203), { widthPx: 400, heightPx: 240 });
});

test('un raster que ya cabe en el cabezal se devuelve tal cual, sin tocarlo', () => {
  const raster = blankRaster(300, 200);
  const result = cropRasterToPrintableWidth(raster, NIIMBOT_B1_PRINTABLE_WIDTH_PX);
  assert.equal(result, raster);
});

test('una etiqueta MYC real (50x30 @ 203dpi) recortada al cabezal del B1 nunca excede 384px de ancho, en el eje relevante (widthPx, filas por punto de cabezal)', () => {
  const raster = renderLabel(PAYLOAD, MYC_50X30, 203);
  assert.equal(raster.widthPx, 400, 'precondición: el lienzo físico completo es 400px');
  const cropped = cropRasterToPrintableWidth(raster, NIIMBOT_B1_PRINTABLE_WIDTH_PX);
  assert.equal(cropped.widthPx, NIIMBOT_B1_PRINTABLE_WIDTH_PX);
  assert.ok(cropped.widthPx <= NIIMBOT_B1_PRINTABLE_WIDTH_PX);
  for (const row of cropped.bitmap.rows) {
    assert.equal(row.length, Math.ceil(NIIMBOT_B1_PRINTABLE_WIDTH_PX / 8));
  }
});

test('heightPx (eje de avance de papel, sin límite de cabezal) nunca se toca al recortar', () => {
  const raster = renderLabel(PAYLOAD, MYC_50X30, 203);
  const cropped = cropRasterToPrintableWidth(raster, NIIMBOT_B1_PRINTABLE_WIDTH_PX);
  assert.equal(cropped.heightPx, raster.heightPx);
  assert.equal(cropped.bitmap.rows.length, raster.bitmap.rows.length);
});

test('todo el contenido dentro del área segura sobrevive la transformación -- el recorte es exactamente el margen físico ya vacío, nunca contenido', () => {
  const raster = renderLabel(PAYLOAD, MYC_50X30, 203);
  const safeArea = profileSafeAreaPx(MYC_50X30, 203);
  const cropped = cropRasterToPrintableWidth(raster, NIIMBOT_B1_PRINTABLE_WIDTH_PX);

  // El margen recortado (8px por lado en este caso) coincide exactamente
  // con el origen del área segura -- si esto se moviera, la función
  // igual sería correcta (verifica en runtime), pero aquí confirmamos que
  // la coincidencia documentada en raster-adapt.ts se sostiene para el
  // perfil/impresora reales de MYC.
  const marginPx = raster.widthPx - NIIMBOT_B1_PRINTABLE_WIDTH_PX;
  assert.equal(marginPx, safeArea.x * 2);

  // Cada pixel con tinta en el raster original, dentro del área segura,
  // debe seguir presente en el raster recortado en la posición desplazada.
  let inkPixelsChecked = 0;
  for (let y = 0; y < raster.heightPx; y += 1) {
    for (let x = safeArea.x; x < safeArea.x + safeArea.widthPx; x += 1) {
      if (packedPixelAt(raster.bitmap.rows[y], x)) {
        inkPixelsChecked += 1;
        assert.ok(packedPixelAt(cropped.bitmap.rows[y], x - safeArea.x), `pixel de tinta perdido en (${x},${y})`);
      }
    }
  }
  assert.ok(inkPixelsChecked > 0, 'la etiqueta de prueba debe tener tinta real que verificar (badge + texto)');
});

test('la transformación es determinista: mismo raster de entrada produce exactamente el mismo resultado byte a byte', () => {
  const raster = renderLabel(PAYLOAD, MYC_50X30, 203);
  const first = cropRasterToPrintableWidth(raster, NIIMBOT_B1_PRINTABLE_WIDTH_PX);
  const second = cropRasterToPrintableWidth(raster, NIIMBOT_B1_PRINTABLE_WIDTH_PX);
  assert.deepEqual(
    first.bitmap.rows.map((row) => Buffer.from(row).toString('hex')),
    second.bitmap.rows.map((row) => Buffer.from(row).toString('hex')),
  );
});

test('si hubiera contenido real en el margen que se va a recortar, bloquea con un error explícito en vez de recortarlo en silencio', () => {
  const raster = blankRaster(400, 10);
  setPixel(raster, 2, 5); // dentro de lo que sería el margen izquierdo (0..7)
  assert.throws(
    () => cropRasterToPrintableWidth(raster, NIIMBOT_B1_PRINTABLE_WIDTH_PX),
    RasterExceedsPrintableWidthError,
  );
});

test('lo mismo para el margen derecho', () => {
  const raster = blankRaster(400, 10);
  setPixel(raster, 397, 3); // dentro de lo que sería el margen derecho (392..399)
  assert.throws(
    () => cropRasterToPrintableWidth(raster, NIIMBOT_B1_PRINTABLE_WIDTH_PX),
    RasterExceedsPrintableWidthError,
  );
});

test('nunca escala ni distorsiona: el ancho recortado es exactamente printableWidthPx, nunca un valor derivado de una escala', () => {
  const raster = blankRaster(400, 5);
  const cropped = cropRasterToPrintableWidth(raster, NIIMBOT_B1_PRINTABLE_WIDTH_PX);
  assert.equal(cropped.widthPx, NIIMBOT_B1_PRINTABLE_WIDTH_PX);
});
