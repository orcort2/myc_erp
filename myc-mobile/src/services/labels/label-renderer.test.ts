import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

import { MYC_50X30, mmToPx, profileCanvasPx, profileSafeAreaPx } from './label-profile';
import {
  LabelRenderError,
  buildLabelLines,
  fitLineToWidth,
  renderLabel,
} from './label-renderer';
import type { LabLabelPayload } from './label-types';

const BASE_PAYLOAD: LabLabelPayload = {
  calibrationDate: '2026-09-01',
  nextCalibrationDate: '2027-09-01',
  equipmentCode: 'ID-1',
  workOrderFolio: '12345',
  certificateFolio: 'MYCA-0001',
};

test('mm->px: 1mm a 203 dpi es ~8px, 50mm ~400px, 30mm ~240px', () => {
  assert.equal(mmToPx(1, 203), 8);
  assert.equal(mmToPx(50, 203), 400);
  assert.equal(mmToPx(30, 203), 240);
});

test('MYC_50X30 es el tamaño físico del medio, nunca 48x28 (eso es el área segura)', () => {
  assert.equal(MYC_50X30.physicalWidthMm, 50);
  assert.equal(MYC_50X30.physicalHeightMm, 30);
  assert.equal(MYC_50X30.safeMarginMm, 1);
});

test('a 203 dpi, el lienzo físico es determinista 400x240 y el área segura ~384x224', () => {
  const canvas = profileCanvasPx(MYC_50X30, 203);
  assert.deepEqual(canvas, { widthPx: 400, heightPx: 240 });
  const safeArea = profileSafeAreaPx(MYC_50X30, 203);
  assert.deepEqual(safeArea, { x: 8, y: 8, widthPx: 384, heightPx: 224 });
});

test('el área segura escala con el DPI -- 203 dpi no es una suposición fija del perfil', () => {
  const canvasAt300 = profileCanvasPx(MYC_50X30, 300);
  assert.notDeepEqual(canvasAt300, profileCanvasPx(MYC_50X30, 203));
  assert.equal(canvasAt300.widthPx, mmToPx(50, 300));
});

test('renderLabel produce dimensiones de raster deterministas iguales al lienzo físico del perfil', () => {
  const raster = renderLabel(BASE_PAYLOAD, MYC_50X30, 203);
  assert.equal(raster.widthPx, 400);
  assert.equal(raster.heightPx, 240);
  assert.equal(raster.profileId, 'MYC_50X30');
  assert.equal(raster.bitmap.rows.length, 240);
  const expectedStride = Math.ceil(400 / 8);
  for (const row of raster.bitmap.rows) assert.equal(row.length, expectedStride);
});

test('renderLabel es determinista: la misma entrada produce el mismo raster byte a byte', () => {
  const first = renderLabel(BASE_PAYLOAD, MYC_50X30, 203);
  const second = renderLabel({ ...BASE_PAYLOAD }, MYC_50X30, 203);
  assert.deepEqual(
    first.bitmap.rows.map((row) => Buffer.from(row).toString('hex')),
    second.bitmap.rows.map((row) => Buffer.from(row).toString('hex')),
  );
});

test('la insignia MYC pinta tinta dentro del lienzo -- nunca un raster completamente en blanco', () => {
  const raster = renderLabel(BASE_PAYLOAD, MYC_50X30, 203);
  const anyInk = raster.bitmap.rows.some((row) => row.some((byte) => byte !== 0));
  assert.ok(anyInk, 'el raster no debe quedar completamente en blanco');
});

test('calibrationKind ya no forma parte del contrato de la etiqueta impresa', () => {
  const lines = buildLabelLines(BASE_PAYLOAD);
  const allText = lines.map((line) => `${line.label} ${line.value}`).join(' ');
  assert.doesNotMatch(allText, /CALIBRADO|VERIFICADO/);
  // @ts-expect-error calibrationKind ya no existe en el contrato
  assert.equal(BASE_PAYLOAD.calibrationKind, undefined);
});

test('buildLabelLines formatea las fechas como DD/MM/YYYY', () => {
  const lines = buildLabelLines(BASE_PAYLOAD);
  const fecha = lines.find((line) => line.label === 'FECHA DE CAL');
  const proxima = lines.find((line) => line.label === 'PROX. CAL');
  assert.equal(fecha?.value, '01/09/2026');
  assert.equal(proxima?.value, '01/09/2027');
});

test('nextCalibrationDate null se imprime como N/A, nunca bloquea ni se omite', () => {
  const lines = buildLabelLines({ ...BASE_PAYLOAD, nextCalibrationDate: null });
  const proxima = lines.find((line) => line.label === 'PROX. CAL');
  assert.equal(proxima?.value, 'N/A');
  // No debe lanzar tampoco al rasterizar.
  assert.doesNotThrow(() => renderLabel({ ...BASE_PAYLOAD, nextCalibrationDate: null }, MYC_50X30, 203));
});

test('certificateFolio presente se imprime tal cual como INFORME -- el dato final real, nunca transformado', () => {
  const lines = buildLabelLines({ ...BASE_PAYLOAD, certificateFolio: 'MYCA-0042' });
  const informe = lines.find((line) => line.label === 'INFORME');
  assert.equal(informe?.value, 'MYCA-0042');
});

test('REGLA DE NEGOCIO: certificateFolio null bloquea la impresión final -- nunca "PENDIENTE" ni ningún placeholder', () => {
  assert.throws(
    () => buildLabelLines({ ...BASE_PAYLOAD, certificateFolio: null }),
    (error: unknown) => error instanceof LabelRenderError && error.code === 'missing_certificate_folio',
  );
  assert.throws(
    () => renderLabel({ ...BASE_PAYLOAD, certificateFolio: null }, MYC_50X30, 203),
    (error: unknown) => error instanceof LabelRenderError,
  );
});

test('REGLA DE NEGOCIO: certificateFolio undefined también bloquea la impresión final', () => {
  const { certificateFolio: _omitted, ...withoutFolio } = BASE_PAYLOAD;
  assert.throws(
    () => buildLabelLines(withoutFolio),
    (error: unknown) => error instanceof LabelRenderError && error.code === 'missing_certificate_folio',
  );
});

test('REGLA DE NEGOCIO: certificateFolio vacío/sólo espacios también bloquea -- no basta con "no ser null"', () => {
  for (const value of ['', '   ', '\t\n']) {
    assert.throws(
      () => buildLabelLines({ ...BASE_PAYLOAD, certificateFolio: value }),
      (error: unknown) => error instanceof LabelRenderError && error.code === 'missing_certificate_folio',
      `debe bloquear para certificateFolio=${JSON.stringify(value)}`,
    );
  }
});

test('REGLA DE NEGOCIO: renderLabel nunca genera un raster cuando falta certificateFolio -- no queda ni un canvas parcial que un llamador pueda usar por error', () => {
  assert.throws(() => renderLabel({ ...BASE_PAYLOAD, certificateFolio: null }, MYC_50X30, 203));
  // buildLabelLines es lo primero que corre dentro de renderLabel (ver
  // comentario "Validar ANTES de tocar el canvas"): si esto lanza, ningún
  // RasterLabel se devuelve jamás -- no hay forma de que un llamador reciba
  // un raster para pasarle a PrinterManager.print/BLE.
});

test('el string "PENDIENTE" ya no existe en ningún camino del renderer final', () => {
  const source = readFileSync(resolve(dirname(fileURLToPath(import.meta.url)), './label-renderer.ts'), 'utf8');
  assert.doesNotMatch(source, /PENDIENTE/);
});

test('calibrationDate ausente/vacía bloquea la impresión con un error explícito y tipado, nunca una etiqueta en blanco', () => {
  assert.throws(
    () => buildLabelLines({ ...BASE_PAYLOAD, calibrationDate: '' }),
    (error: unknown) => error instanceof LabelRenderError && error.code === 'missing_calibration_date',
  );
  assert.throws(
    () => renderLabel({ ...BASE_PAYLOAD, calibrationDate: '' }, MYC_50X30, 203),
    (error: unknown) => error instanceof LabelRenderError,
  );
});

test('una fecha malformada se imprime tal cual, nunca se oculta en un raster en blanco', () => {
  const lines = buildLabelLines({ ...BASE_PAYLOAD, calibrationDate: 'no-es-una-fecha' });
  const fecha = lines.find((line) => line.label === 'FECHA DE CAL');
  assert.equal(fecha?.value, 'no-es-una-fecha');
});

test('un CODIGO/O.T./INFORME largo se conserva completo si cabe, o se trunca visiblemente con ">" -- nunca se recorta en silencio', () => {
  const longLine = { label: 'INFORME', value: 'MYCA-000000000000000000000001' };
  const fitted = fitLineToWidth(longLine, 4, 100);
  assert.ok(fitted.value.length < longLine.value.length, 'debe recortarse a un ancho angosto');
  assert.match(fitted.value, />$/, 'el recorte debe marcarse explícitamente, nunca en silencio');

  const untouched = fitLineToWidth(longLine, 1, 5000);
  assert.equal(untouched.value, longLine.value, 'con espacio suficiente no debe recortar nada');
});

test('un equipmentCode/workOrderFolio/certificateFolio extremadamente largos no hacen fallar el render ni desbordan el raster', () => {
  const raster = renderLabel(
    {
      ...BASE_PAYLOAD,
      equipmentCode: 'IDENTIFICACION-EXTREMADAMENTE-LARGA-0000000001',
      workOrderFolio: '999999999999999',
      certificateFolio: 'MYCA-000000000000000000000000000001',
    },
    MYC_50X30,
    203,
  );
  assert.equal(raster.widthPx, 400);
  assert.equal(raster.heightPx, 240);
  const expectedStride = Math.ceil(400 / 8);
  for (const row of raster.bitmap.rows) assert.equal(row.length, expectedStride);
});
