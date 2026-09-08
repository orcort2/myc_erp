import assert from 'node:assert/strict';
import test from 'node:test';

import {
  NIIMBOT_BLE_CHARACTERISTIC_UUID,
  NIIMBOT_BLE_SERVICE_UUID,
  NIIMBOT_REQUEST,
  NiimbotFrameAssembler,
  NiimbotFrameError,
  buildConnectPacket,
  buildPageEndPacket,
  buildPageStartPacket,
  buildPrintEndPacket,
  buildPrintJobPackets,
  buildPrintStartPacket,
  buildPrintStatusQueryPacket,
  buildSetDensityPacket,
  buildSetLabelTypePacket,
  buildSetPageSizePacket,
  clampDensity,
  decodeNiimbotPacket,
  encodeNiimbotPacket,
  encodeRowPacket,
} from './protocol';

function hex(bytes: Uint8Array): string {
  return Array.from(bytes).map((byte) => byte.toString(16).padStart(2, '0')).join(' ');
}

test('UUIDs BLE coinciden con las 3 fuentes auditadas (niim.blue, niimprint, niimbluelib)', () => {
  assert.equal(NIIMBOT_BLE_SERVICE_UUID, 'e7810a71-73ae-499d-8c15-faa9aef0c3f2');
  assert.equal(NIIMBOT_BLE_CHARACTERISTIC_UUID, 'bef8d6c9-9c21-4c9e-b632-bd58c1009f9f');
});

test('encodeNiimbotPacket: el paquete Connect coincide byte a byte con el vector documentado (55 55 C1 01 01 C1 AA AA)', () => {
  const encoded = encodeNiimbotPacket(buildConnectPacket());
  assert.equal(hex(encoded), '55 55 c1 01 01 c1 aa aa');
});

test('checksum = cmd XOR len XOR todos los bytes de datos (confirmado en niimprint NiimbotPacket)', () => {
  const packet = { command: 0x21, data: Uint8Array.of(3) };
  const encoded = encodeNiimbotPacket(packet);
  // checksum esperado: 0x21 ^ 0x01 ^ 0x03 = 0x23
  assert.equal(encoded[5], 0x23);
});

test('encode/decode es un roundtrip exacto para datos arbitrarios', () => {
  const packet = { command: 0x85, data: Uint8Array.of(0, 5, 0, 0, 0, 1, 0b10101010, 0b00001111) };
  const decoded = decodeNiimbotPacket(encodeNiimbotPacket(packet));
  assert.equal(decoded.command, packet.command);
  assert.deepEqual(Array.from(decoded.data), Array.from(packet.data));
});

test('decodeNiimbotPacket rechaza encabezado, checksum y pie inválidos', () => {
  const good = encodeNiimbotPacket({ command: 0x01, data: Uint8Array.of(1) });

  const badHeader = Uint8Array.from(good);
  badHeader[0] = 0x00;
  assert.throws(() => decodeNiimbotPacket(badHeader), NiimbotFrameError);

  const badChecksum = Uint8Array.from(good);
  badChecksum[5] ^= 0xff;
  assert.throws(() => decodeNiimbotPacket(badChecksum), NiimbotFrameError);

  const badFooter = Uint8Array.from(good);
  badFooter[badFooter.length - 1] = 0x00;
  assert.throws(() => decodeNiimbotPacket(badFooter), NiimbotFrameError);

  assert.throws(() => decodeNiimbotPacket(Uint8Array.of(0x55, 0x55, 0x01)), NiimbotFrameError);
});

test('encodeRowPacket: header de 6 bytes (fila BE de 16 bits, 3 ceros, repetición=1) + bytes de fila', () => {
  const row = Uint8Array.of(0xff, 0x00, 0b10000000);
  const packet = encodeRowPacket(0x0102, row);
  assert.equal(packet.command, NIIMBOT_REQUEST.PrintBitmapRow);
  assert.deepEqual(Array.from(packet.data.slice(0, 6)), [0x01, 0x02, 0x00, 0x00, 0x00, 0x01]);
  assert.deepEqual(Array.from(packet.data.slice(6)), Array.from(row));
});

test('NiimbotFrameAssembler reensambla un frame partido en varios trozos BLE (fragmentación)', () => {
  const frame = encodeNiimbotPacket({ command: 0x02, data: Uint8Array.of(1) });
  const assembler = new NiimbotFrameAssembler();
  const firstChunk = frame.slice(0, 3);
  const secondChunk = frame.slice(3);
  assert.deepEqual(assembler.push(firstChunk), []);
  const packets = assembler.push(secondChunk);
  assert.equal(packets.length, 1);
  assert.equal(packets[0].command, 0x02);
});

test('NiimbotFrameAssembler entrega varios frames concatenados en una sola notificación', () => {
  const first = encodeNiimbotPacket({ command: 0x04, data: Uint8Array.of(1) });
  const second = encodeNiimbotPacket({ command: 0xb5, data: Uint8Array.of(9, 9) });
  const combined = new Uint8Array(first.length + second.length);
  combined.set(first, 0);
  combined.set(second, first.length);

  const packets = new NiimbotFrameAssembler().push(combined);
  assert.equal(packets.length, 2);
  assert.equal(packets[0].command, 0x04);
  assert.equal(packets[1].command, 0xb5);
  assert.deepEqual(Array.from(packets[1].data), [9, 9]);
});

test('NiimbotFrameAssembler descarta basura previa al encabezado sin perder el frame real que sigue', () => {
  const frame = encodeNiimbotPacket({ command: 0x33, data: Uint8Array.of(1) });
  const withGarbage = new Uint8Array(3 + frame.length);
  withGarbage.set([0x00, 0xff, 0x12], 0);
  withGarbage.set(frame, 3);

  const packets = new NiimbotFrameAssembler().push(withGarbage);
  assert.equal(packets.length, 1);
  assert.equal(packets[0].command, 0x33);
});

test('NiimbotFrameAssembler descarta un frame con checksum corrupto pero sigue encontrando el siguiente frame válido', () => {
  const corrupted = encodeNiimbotPacket({ command: 0x14, data: Uint8Array.of(1) });
  corrupted[corrupted.length - 3] ^= 0xff; // corrompe el byte de checksum
  const valid = encodeNiimbotPacket({ command: 0xe4, data: Uint8Array.of(1) });
  const combined = new Uint8Array(corrupted.length + valid.length);
  combined.set(corrupted, 0);
  combined.set(valid, corrupted.length);

  const packets = new NiimbotFrameAssembler().push(combined);
  assert.equal(packets.length, 1);
  assert.equal(packets[0].command, 0xe4);
});

test('NiimbotFrameAssembler no falla ante un 0x55 suelto al final del buffer -- lo conserva para el próximo push', () => {
  const assembler = new NiimbotFrameAssembler();
  assert.deepEqual(assembler.push(Uint8Array.of(0x01, 0x02, 0x55)), []);
  const frame = encodeNiimbotPacket({ command: 0xd9, data: Uint8Array.of(4) });
  const packets = assembler.push(frame.slice(1)); // ya se guardó un 0x55, falta el resto
  assert.equal(packets.length, 1);
  assert.equal(packets[0].command, 0xd9);
});

test('clampDensity: por defecto 3, siempre dentro de 1-5', () => {
  assert.equal(clampDensity(undefined), 3);
  assert.equal(clampDensity(0), 1);
  assert.equal(clampDensity(10), 5);
  assert.equal(clampDensity(4.6), 5);
});

test('buildSetPageSizePacket: header/width en el orden height,width (confirmado en niim.blue y niimprint set_dimension)', () => {
  const packet = buildSetPageSizePacket(400, 240);
  // heightHi,heightLo,widthHi,widthLo,0,1
  assert.deepEqual(Array.from(packet.data), [0x00, 0xf0, 0x01, 0x90, 0x00, 0x01]);
});

test('buildPrintStartPacket codifica el conteo de páginas en big-endian dentro de un payload de 7 bytes', () => {
  const packet = buildPrintStartPacket(1);
  assert.equal(packet.data.length, 7);
  assert.deepEqual(Array.from(packet.data), [0x00, 0x01, 0, 0, 0, 0, 0]);
});

test('buildPrintJobPackets produce exactamente la secuencia densidad->tipo->inicio->página->tamaño->filas->fin de página, en ese orden', () => {
  const raster = {
    widthPx: 8,
    heightPx: 2,
    bitmap: { rows: [Uint8Array.of(0xff), Uint8Array.of(0x00)] },
  };
  const packets = buildPrintJobPackets(raster, { density: 3 });
  const commands: number[] = packets.map((packet) => packet.command);
  // Nunca incluye el handshake de conexión ni el poll/PrintEnd finales --
  // esos son inherentemente interactivos y viven en el adaptador runtime.
  // (Los checks .includes() van ANTES del deepEqual de abajo a propósito:
  // node:assert/strict tipa deepEqual como "asserts actual is T", que
  // estrecha el tipo de `commands` al literal del array esperado para el
  // resto del scope y rompería estas dos comparaciones si fueran después.)
  assert.ok(!commands.includes(NIIMBOT_REQUEST.Connect));
  assert.ok(!commands.includes(NIIMBOT_REQUEST.PrintEnd));
  assert.deepEqual(commands, [
    NIIMBOT_REQUEST.SetDensity,
    NIIMBOT_REQUEST.SetLabelType,
    NIIMBOT_REQUEST.PrintStart,
    NIIMBOT_REQUEST.PageStart,
    NIIMBOT_REQUEST.SetPageSize,
    NIIMBOT_REQUEST.PrintBitmapRow,
    NIIMBOT_REQUEST.PrintBitmapRow,
    NIIMBOT_REQUEST.PageEnd,
  ]);
});

test('buildPrintJobPackets es determinista: mismo raster y densidad producen exactamente los mismos bytes', () => {
  const raster = { widthPx: 8, heightPx: 1, bitmap: { rows: [Uint8Array.of(0x0f)] } };
  const first = buildPrintJobPackets(raster, { density: 4 }).map((packet) => hex(encodeNiimbotPacket(packet)));
  const second = buildPrintJobPackets(raster, { density: 4 }).map((packet) => hex(encodeNiimbotPacket(packet)));
  assert.deepEqual(first, second);
});

test('cada fila del raster produce su propio paquete PrintBitmapRow con el índice de fila correcto', () => {
  const raster = {
    widthPx: 8,
    heightPx: 3,
    bitmap: { rows: [Uint8Array.of(1), Uint8Array.of(2), Uint8Array.of(3)] },
  };
  const rowPackets = buildPrintJobPackets(raster).filter((packet) => packet.command === NIIMBOT_REQUEST.PrintBitmapRow);
  assert.equal(rowPackets.length, 3);
  rowPackets.forEach((packet, index) => {
    const rowIndex = (packet.data[0] << 8) | packet.data[1];
    assert.equal(rowIndex, index);
  });
});

test('los helpers de comandos sueltos (page start/end, print end, status query, label type) usan los opcodes auditados', () => {
  assert.equal(buildPageStartPacket().command, NIIMBOT_REQUEST.PageStart);
  assert.equal(buildPageEndPacket().command, NIIMBOT_REQUEST.PageEnd);
  assert.equal(buildPrintEndPacket().command, NIIMBOT_REQUEST.PrintEnd);
  assert.equal(buildPrintStatusQueryPacket().command, NIIMBOT_REQUEST.PrintStatus);
  assert.equal(buildSetLabelTypePacket().command, NIIMBOT_REQUEST.SetLabelType);
  assert.deepEqual(Array.from(buildSetDensityPacket(2).data), [2]);
});
