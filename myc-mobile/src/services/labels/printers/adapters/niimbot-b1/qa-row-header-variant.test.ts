import assert from 'node:assert/strict';
import test from 'node:test';

import {
  buildQaBlackBarRaster,
  buildQaPrintJobPackets,
  countBlackPixels,
} from './qa-row-header-variant';
import { NIIMBOT_REQUEST, buildPrintJobPackets, decodeNiimbotPacket, encodeNiimbotPacket } from './protocol';

test('countBlackPixels cuenta exactamente los bits en 1 -- 0xFF son 8 píxeles negros, 0x00 son cero', () => {
  assert.equal(countBlackPixels(Uint8Array.of(0xff)), 8);
  assert.equal(countBlackPixels(Uint8Array.of(0x00)), 0);
  assert.equal(countBlackPixels(Uint8Array.of(0xff, 0xff)), 16);
});

test('countBlackPixels cuenta bits individuales sin importar su posición dentro del byte', () => {
  assert.equal(countBlackPixels(Uint8Array.of(0b10000000)), 1);
  assert.equal(countBlackPixels(Uint8Array.of(0b00000001)), 1);
  assert.equal(countBlackPixels(Uint8Array.of(0b10101010)), 4);
  assert.equal(countBlackPixels(Uint8Array.of(0b11110000, 0b00001111)), 8);
});

test('buildQaBlackBarRaster produce un bloque negro sólido de 384x64 por default -- 384px es el máximo imprimible del B1', () => {
  const raster = buildQaBlackBarRaster();
  assert.equal(raster.widthPx, 384);
  assert.equal(raster.heightPx, 64);
  assert.equal(raster.rows.length, 64);
  const expectedStride = Math.ceil(384 / 8);
  for (const row of raster.rows) {
    assert.equal(row.length, expectedStride);
    assert.equal(countBlackPixels(row), 384, 'cada fila debe ser negra en todo su ancho, sin relleno de stride contando como tinta');
  }
});

test('buildQaBlackBarRaster acepta dimensiones explícitas y maneja un ancho no múltiplo de 8 sin filtrar relleno como tinta', () => {
  const raster = buildQaBlackBarRaster({ widthPx: 20, heightPx: 3 });
  assert.equal(raster.widthPx, 20);
  assert.equal(raster.heightPx, 3);
  assert.equal(raster.rows.length, 3);
  const expectedStride = Math.ceil(20 / 8);
  assert.equal(expectedStride, 3);
  for (const row of raster.rows) {
    assert.equal(row.length, 3);
    // 20 bits negros reales; los 4 bits de relleno del último byte deben
    // quedar en 0 -- si countBlackPixels devolviera 24, el relleno se
    // estaría contando como tinta por error.
    assert.equal(countBlackPixels(row), 20);
  }
});

test('cada fila del raster de QA es una copia independiente -- mutar una no debe afectar a las demás', () => {
  const raster = buildQaBlackBarRaster({ widthPx: 8, heightPx: 2 });
  raster.rows[0][0] = 0x00;
  assert.equal(countBlackPixels(raster.rows[0]), 0);
  assert.equal(countBlackPixels(raster.rows[1]), 8, 'la fila 1 nunca debe verse afectada por mutar la fila 0');
});

test('la variante "zero_count" reproduce EXACTAMENTE la secuencia de producción (buildPrintJobPackets) para el mismo raster -- nunca diverge del camino real', () => {
  const raster = buildQaBlackBarRaster({ widthPx: 16, heightPx: 4 });
  const qaPackets = buildQaPrintJobPackets(raster, 'zero_count');
  const productionPackets = buildPrintJobPackets({ widthPx: raster.widthPx, heightPx: raster.heightPx, bitmap: { rows: raster.rows } });

  assert.equal(qaPackets.length, productionPackets.length);
  for (let index = 0; index < qaPackets.length; index += 1) {
    assert.equal(qaPackets[index].command, productionPackets[index].command, `comando distinto en el paquete ${index}`);
    assert.deepEqual(
      Array.from(qaPackets[index].data),
      Array.from(productionPackets[index].data),
      `bytes distintos en el paquete ${index}`,
    );
  }
});

test('la variante "zero_count" nunca cambia el density explícito -- mismo contrato que buildPrintJobPackets', () => {
  const raster = buildQaBlackBarRaster({ widthPx: 8, heightPx: 1 });
  const qaPackets = buildQaPrintJobPackets(raster, 'zero_count', { density: 3 });
  const productionPackets = buildPrintJobPackets(
    { widthPx: raster.widthPx, heightPx: raster.heightPx, bitmap: { rows: raster.rows } },
    { density: 3 },
  );
  assert.deepEqual(Array.from(qaPackets[0].data), Array.from(productionPackets[0].data));
});

test('la variante "documented_black_pixel_count" codifica el conteo real de 16 bits en el header, deja reservado/repetición sin cambios', () => {
  const raster = buildQaBlackBarRaster({ widthPx: 384, heightPx: 2 });
  const packets = buildQaPrintJobPackets(raster, 'documented_black_pixel_count');
  const rowPackets = packets.filter((packet) => packet.command === NIIMBOT_REQUEST.PrintBitmapRow);
  assert.equal(rowPackets.length, 2);
  for (const [index, packet] of rowPackets.entries()) {
    const header = packet.data.subarray(0, 6);
    assert.equal((header[0] << 8) | header[1], index, 'el índice de fila debe seguir siendo big-endian de 16 bits');
    assert.equal((header[2] << 8) | header[3], 384, 'el header debe llevar el conteo real de píxeles negros (16 bits) para un bloque de 384px sólido');
    assert.equal(header[4], 0, 'el byte reservado nunca cambia entre variantes');
    assert.equal(header[5], 1, 'la repetición nunca cambia entre variantes -- la divergencia documentada es sólo sobre el conteo');
  }
});

test('las dos variantes producen headers distintos para el mismo raster -- la comparación A/B tiene sentido', () => {
  const raster = buildQaBlackBarRaster({ widthPx: 384, heightPx: 1 });
  const zeroCountPackets = buildQaPrintJobPackets(raster, 'zero_count');
  const realCountPackets = buildQaPrintJobPackets(raster, 'documented_black_pixel_count');
  const zeroCountRow = zeroCountPackets.find((packet) => packet.command === NIIMBOT_REQUEST.PrintBitmapRow)!;
  const realCountRow = realCountPackets.find((packet) => packet.command === NIIMBOT_REQUEST.PrintBitmapRow)!;
  assert.notDeepEqual(Array.from(zeroCountRow.data), Array.from(realCountRow.data));
  // Ambos deben seguir llevando exactamente los mismos bytes de imagen
  // (bytes 6+) -- la divergencia es sólo en el header, nunca en el
  // contenido de la fila.
  assert.deepEqual(Array.from(zeroCountRow.data.subarray(6)), Array.from(realCountRow.data.subarray(6)));
});

test('ambas variantes sobreviven un round-trip real de encode/decode del framing NIIMBOT -- nunca paquetes inventados fuera del protocolo', () => {
  const raster = buildQaBlackBarRaster({ widthPx: 8, heightPx: 1 });
  for (const variant of ['zero_count', 'documented_black_pixel_count'] as const) {
    const [rowPacket] = buildQaPrintJobPackets(raster, variant).filter((packet) => packet.command === NIIMBOT_REQUEST.PrintBitmapRow);
    const framed = encodeNiimbotPacket(rowPacket);
    const decoded = decodeNiimbotPacket(framed);
    assert.equal(decoded.command, NIIMBOT_REQUEST.PrintBitmapRow);
    assert.deepEqual(Array.from(decoded.data), Array.from(rowPacket.data));
  }
});
