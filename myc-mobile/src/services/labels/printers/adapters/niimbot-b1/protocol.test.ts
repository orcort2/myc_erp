import assert from 'node:assert/strict';
import test from 'node:test';

import {
  NIIMBOT_BLE_CHARACTERISTIC_UUID,
  NIIMBOT_BLE_SERVICE_UUID,
  NIIMBOT_REQUEST,
  NiimbotFrameAssembler,
  NiimbotFrameError,
  NiimbotPageStatusError,
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
  countV3WhitePixels,
  decodeNiimbotPacket,
  encodeNiimbotPacket,
  encodeRowPacket,
  parsePrintStatusResult,
} from './protocol';

function hex(bytes: Uint8Array): string {
  return Array.from(bytes)
    .map((byte) =>
      byte
        .toString(16)
        .padStart(2, '0'),
    )
    .join(' ');
}

test('UUIDs BLE coinciden con las fuentes auditadas', () => {
  assert.equal(
    NIIMBOT_BLE_SERVICE_UUID,
    'e7810a71-73ae-499d-8c15-faa9aef0c3f2',
  );

  assert.equal(
    NIIMBOT_BLE_CHARACTERISTIC_UUID,
    'bef8d6c9-9c21-4c9e-b632-bd58c1009f9f',
  );
});

test('encodeNiimbotPacket: Connect coincide byte a byte con el framing NIIMBOT', () => {
  const encoded =
    encodeNiimbotPacket(
      buildConnectPacket(),
    );

  assert.equal(
    hex(encoded),
    '55 55 c1 01 01 c1 aa aa',
  );
});

test('checksum = cmd XOR len XOR todos los bytes de datos', () => {
  const packet = {
    command: 0x21,
    data: Uint8Array.of(3),
  };

  const encoded =
    encodeNiimbotPacket(packet);

  assert.equal(
    encoded[5],
    0x23,
  );
});

test('encode/decode es un roundtrip exacto', () => {
  const packet = {
    command: 0x85,
    data: Uint8Array.of(
      0,
      5,
      0,
      0,
      0,
      1,
      0b10101010,
      0b00001111,
    ),
  };

  const decoded =
    decodeNiimbotPacket(
      encodeNiimbotPacket(packet),
    );

  assert.equal(
    decoded.command,
    packet.command,
  );

  assert.deepEqual(
    Array.from(decoded.data),
    Array.from(packet.data),
  );
});

test('decodeNiimbotPacket rechaza encabezado, checksum y pie inválidos', () => {
  const good =
    encodeNiimbotPacket({
      command: 0x01,
      data: Uint8Array.of(1),
    });

  const badHeader =
    Uint8Array.from(good);

  badHeader[0] = 0x00;

  assert.throws(
    () =>
      decodeNiimbotPacket(
        badHeader,
      ),
    NiimbotFrameError,
  );

  const badChecksum =
    Uint8Array.from(good);

  badChecksum[5] ^= 0xff;

  assert.throws(
    () =>
      decodeNiimbotPacket(
        badChecksum,
      ),
    NiimbotFrameError,
  );

  const badFooter =
    Uint8Array.from(good);

  badFooter[
    badFooter.length - 1
  ] = 0x00;

  assert.throws(
    () =>
      decodeNiimbotPacket(
        badFooter,
      ),
    NiimbotFrameError,
  );

  assert.throws(
    () =>
      decodeNiimbotPacket(
        Uint8Array.of(
          0x55,
          0x55,
          0x01,
        ),
      ),
    NiimbotFrameError,
  );
});

test('countV3WhitePixels cuenta blancos por segmentos de 192 px', () => {
  const black384 =
    new Uint8Array(48);

  black384.fill(0xff);

  assert.deepEqual(
    countV3WhitePixels(
      black384,
      384,
    ),
    [
      0,
      0,
      0,
    ],
  );

  const white384 =
    new Uint8Array(48);

  assert.deepEqual(
    countV3WhitePixels(
      white384,
      384,
    ),
    [
      192,
      192,
      0,
    ],
  );
});

test('encodeRowPacket usa header V3 oficial: fila BE + 3 conteos blancos + repeat=1', () => {
  const row =
    Uint8Array.of(
      0xff,
      0x00,
      0b10000000,
    );

  const packet =
    encodeRowPacket(
      0x0102,
      row,
      24,
    );

  assert.equal(
    packet.command,
    NIIMBOT_REQUEST.PrintBitmapRow,
  );

  /*
   * 24 píxeles:
   *
   * FF       -> 8 negros
   * 00       -> 8 blancos
   * 10000000 -> 1 negro + 7 blancos
   *
   * Total blancos = 15.
   */
  assert.deepEqual(
    Array.from(
      packet.data.slice(
        0,
        6,
      ),
    ),
    [
      0x01,
      0x02,
      15,
      0,
      0,
      1,
    ],
  );

  assert.deepEqual(
    Array.from(
      packet.data.slice(6),
    ),
    Array.from(row),
  );
});

test('encodeRowPacket serializa una fila negra B1 de 384 px como 00 00 00 en los contadores', () => {
  const row =
    new Uint8Array(48);

  row.fill(0xff);

  const packet =
    encodeRowPacket(
      0,
      row,
      384,
    );

  assert.equal(
    packet.data.length,
    54,
  );

  assert.deepEqual(
    Array.from(
      packet.data.subarray(
        0,
        6,
      ),
    ),
    [
      0x00,
      0x00,
      0x00,
      0x00,
      0x00,
      0x01,
    ],
  );
});

test('encodeRowPacket serializa una fila blanca B1 de 384 px como C0 C0 00', () => {
  const row =
    new Uint8Array(48);

  const packet =
    encodeRowPacket(
      0,
      row,
      384,
    );

  assert.deepEqual(
    Array.from(
      packet.data.subarray(
        0,
        6,
      ),
    ),
    [
      0x00,
      0x00,
      0xc0,
      0xc0,
      0x00,
      0x01,
    ],
  );
});

test('encodeRowPacket respeta widthPx real y no cuenta padding como blanco', () => {
  const row =
    Uint8Array.of(
      0xff,
      0xff,
      0xf0,
    );

  const packet =
    encodeRowPacket(
      0,
      row,
      20,
    );

  assert.deepEqual(
    Array.from(
      packet.data.subarray(
        0,
        6,
      ),
    ),
    [
      0,
      0,
      0,
      0,
      0,
      1,
    ],
  );
});

test('NiimbotFrameAssembler reensambla un frame fragmentado', () => {
  const frame =
    encodeNiimbotPacket({
      command: 0x02,
      data: Uint8Array.of(1),
    });

  const assembler =
    new NiimbotFrameAssembler();

  const firstChunk =
    frame.slice(0, 3);

  const secondChunk =
    frame.slice(3);

  assert.deepEqual(
    assembler.push(
      firstChunk,
    ),
    [],
  );

  const packets =
    assembler.push(
      secondChunk,
    );

  assert.equal(
    packets.length,
    1,
  );

  assert.equal(
    packets[0].command,
    0x02,
  );
});

test('NiimbotFrameAssembler entrega varios frames concatenados', () => {
  const first =
    encodeNiimbotPacket({
      command: 0x04,
      data: Uint8Array.of(1),
    });

  const second =
    encodeNiimbotPacket({
      command: 0xb5,
      data: Uint8Array.of(
        9,
        9,
      ),
    });

  const combined =
    new Uint8Array(
      first.length +
        second.length,
    );

  combined.set(
    first,
    0,
  );

  combined.set(
    second,
    first.length,
  );

  const packets =
    new NiimbotFrameAssembler()
      .push(combined);

  assert.equal(
    packets.length,
    2,
  );

  assert.equal(
    packets[0].command,
    0x04,
  );

  assert.equal(
    packets[1].command,
    0xb5,
  );

  assert.deepEqual(
    Array.from(
      packets[1].data,
    ),
    [
      9,
      9,
    ],
  );
});

test('NiimbotFrameAssembler descarta basura previa al encabezado', () => {
  const frame =
    encodeNiimbotPacket({
      command: 0x33,
      data: Uint8Array.of(1),
    });

  const withGarbage =
    new Uint8Array(
      3 +
        frame.length,
    );

  withGarbage.set(
    [
      0x00,
      0xff,
      0x12,
    ],
    0,
  );

  withGarbage.set(
    frame,
    3,
  );

  const packets =
    new NiimbotFrameAssembler()
      .push(
        withGarbage,
      );

  assert.equal(
    packets.length,
    1,
  );

  assert.equal(
    packets[0].command,
    0x33,
  );
});

test('NiimbotFrameAssembler descarta frame corrupto y continúa con el siguiente válido', () => {
  const corrupted =
    encodeNiimbotPacket({
      command: 0x14,
      data: Uint8Array.of(1),
    });

  corrupted[
    corrupted.length - 3
  ] ^= 0xff;

  const valid =
    encodeNiimbotPacket({
      command: 0xe4,
      data: Uint8Array.of(1),
    });

  const combined =
    new Uint8Array(
      corrupted.length +
        valid.length,
    );

  combined.set(
    corrupted,
    0,
  );

  combined.set(
    valid,
    corrupted.length,
  );

  const packets =
    new NiimbotFrameAssembler()
      .push(combined);

  assert.equal(
    packets.length,
    1,
  );

  assert.equal(
    packets[0].command,
    0xe4,
  );
});

test('NiimbotFrameAssembler conserva un 0x55 parcial al final del buffer', () => {
  const assembler =
    new NiimbotFrameAssembler();

  assert.deepEqual(
    assembler.push(
      Uint8Array.of(
        0x01,
        0x02,
        0x55,
      ),
    ),
    [],
  );

  const frame =
    encodeNiimbotPacket({
      command: 0xd9,
      data: Uint8Array.of(4),
    });

  const packets =
    assembler.push(
      frame.slice(1),
    );

  assert.equal(
    packets.length,
    1,
  );

  assert.equal(
    packets[0].command,
    0xd9,
  );
});

test('clampDensity: por defecto 3, rango 1-5', () => {
  assert.equal(
    clampDensity(
      undefined,
    ),
    3,
  );

  assert.equal(
    clampDensity(0),
    1,
  );

  assert.equal(
    clampDensity(10),
    5,
  );

  assert.equal(
    clampDensity(4.6),
    5,
  );
});

test('buildPrintStartPacket reproduce jcSetPrintAllTime V3: uint16 BE de 2 bytes', () => {
  const packet =
    buildPrintStartPacket(1);

  assert.equal(
    packet.command,
    NIIMBOT_REQUEST.PrintStart,
  );

  assert.equal(
    packet.data.length,
    2,
  );

  assert.deepEqual(
    Array.from(
      packet.data,
    ),
    [
      0x00,
      0x01,
    ],
  );

  assert.equal(
    hex(
      encodeNiimbotPacket(
        packet,
      ),
    ),
    '55 55 01 02 00 01 02 aa aa',
  );
});

test('buildPrintStartPacket serializa pageCount completo como uint16 BE', () => {
  const packet =
    buildPrintStartPacket(
      0x1234,
    );

  assert.deepEqual(
    Array.from(
      packet.data,
    ),
    [
      0x12,
      0x34,
    ],
  );
});

test('buildPrintStartPacket rechaza cero y valores fuera de uint16', () => {
  assert.throws(
    () =>
      buildPrintStartPacket(0),
    RangeError,
  );

  assert.throws(
    () =>
      buildPrintStartPacket(
        0x10000,
      ),
    RangeError,
  );

  assert.throws(
    () =>
      buildPrintStartPacket(
        -1,
      ),
    RangeError,
  );
});

test('buildPageStartPacket reproduce jcSetPagePrint V3: 03 01 00', () => {
  const packet =
    buildPageStartPacket();

  assert.equal(
    packet.command,
    NIIMBOT_REQUEST.PageStart,
  );

  assert.deepEqual(
    Array.from(
      packet.data,
    ),
    [
      0x00,
    ],
  );

  assert.equal(
    hex(
      encodeNiimbotPacket(
        packet,
      ),
    ),
    '55 55 03 01 00 02 aa aa',
  );
});

test('buildSetPageSizePacket reproduce jcSetPageInfo V3: height,width,count como uint16 BE', () => {
  const packet =
    buildSetPageSizePacket(
      400,
      240,
      1,
    );

  assert.equal(
    packet.command,
    NIIMBOT_REQUEST.SetPageSize,
  );

  assert.deepEqual(
    Array.from(
      packet.data,
    ),
    [
      0x00,
      0xf0,
      0x01,
      0x90,
      0x00,
      0x01,
    ],
  );
});

test('buildSetPageSizePacket mantiene printCount=1 por defecto', () => {
  const packet =
    buildSetPageSizePacket(
      400,
      240,
    );

  assert.deepEqual(
    Array.from(
      packet.data,
    ),
    [
      0x00,
      0xf0,
      0x01,
      0x90,
      0x00,
      0x01,
    ],
  );
});

test('buildSetPageSizePacket serializa printCount como uint16 BE', () => {
  const packet =
    buildSetPageSizePacket(
      384,
      240,
      0x0102,
    );

  assert.deepEqual(
    Array.from(
      packet.data.slice(
        4,
        6,
      ),
    ),
    [
      0x01,
      0x02,
    ],
  );
});

test('buildSetPageSizePacket rechaza dimensiones o copias inválidas', () => {
  assert.throws(
    () =>
      buildSetPageSizePacket(
        0,
        240,
      ),
    RangeError,
  );

  assert.throws(
    () =>
      buildSetPageSizePacket(
        384,
        0,
      ),
    RangeError,
  );

  assert.throws(
    () =>
      buildSetPageSizePacket(
        384,
        240,
        0,
      ),
    RangeError,
  );
});

test('buildPageEndPacket reproduce jcSetPageTerminal V3: E3 01 00', () => {
  const packet =
    buildPageEndPacket();

  assert.equal(
    packet.command,
    NIIMBOT_REQUEST.PageEnd,
  );

  assert.deepEqual(
    Array.from(
      packet.data,
    ),
    [
      0x00,
    ],
  );

  assert.equal(
    hex(
      encodeNiimbotPacket(
        packet,
      ),
    ),
    '55 55 e3 01 00 e2 aa aa',
  );
});

test('buildPrintStatusQueryPacket reproduce getPrinterPageStatus V3: A3 01 00', () => {
  const packet =
    buildPrintStatusQueryPacket();

  assert.equal(
    packet.command,
    NIIMBOT_REQUEST.PrintStatus,
  );

  assert.deepEqual(
    Array.from(
      packet.data,
    ),
    [
      0x00,
    ],
  );

  assert.equal(
    hex(
      encodeNiimbotPacket(
        packet,
      ),
    ),
    '55 55 a3 01 00 a2 aa aa',
  );
});

test('parsePrintStatusResult parsea los 8 bytes fijos del PageStatus V3', () => {
  const status =
    parsePrintStatusResult({
      command:
        NIIMBOT_REQUEST.PrintStatusResult,
      data:
        Uint8Array.of(
          0x12,
          0x34,
          0x56,
          0x78,
          0x9a,
          0xbc,
          0xde,
          0xf0,
        ),
    });

  assert.equal(
    status.field0,
    0x1234,
  );

  assert.equal(
    status.field1,
    0x56,
  );

  assert.equal(
    status.field2,
    0x78,
  );

  assert.equal(
    status.field3,
    0x9abc,
  );

  assert.equal(
    status.field4,
    0xde,
  );

  assert.equal(
    status.field5,
    0xf0,
  );

  assert.equal(
    status.extraLength,
    0,
  );

  assert.deepEqual(
    Array.from(
      status.extraData,
    ),
    [],
  );
});

test('parsePrintStatusResult conserva extensión variable declarada después de los 8 bytes fijos', () => {
  const status =
    parsePrintStatusResult({
      command:
        NIIMBOT_REQUEST.PrintStatusResult,
      data:
        Uint8Array.of(
          0x00,
          0x02,
          0x01,
          0x03,
          0x00,
          0x04,
          0x05,
          0x06,
          0x03,
          0xaa,
          0xbb,
          0xcc,
        ),
    });

  assert.equal(
    status.field0,
    2,
  );

  assert.equal(
    status.field1,
    1,
  );

  assert.equal(
    status.field2,
    3,
  );

  assert.equal(
    status.field3,
    4,
  );

  assert.equal(
    status.field4,
    5,
  );

  assert.equal(
    status.field5,
    6,
  );

  assert.equal(
    status.extraLength,
    3,
  );

  assert.deepEqual(
    Array.from(
      status.extraData,
    ),
    [
      0xaa,
      0xbb,
      0xcc,
    ],
  );
});

test('parsePrintStatusResult rechaza un opcode distinto de B3', () => {
  assert.throws(
    () =>
      parsePrintStatusResult({
        command:
          NIIMBOT_REQUEST.PageEndResult,
        data:
          new Uint8Array(8),
      }),
    NiimbotPageStatusError,
  );
});

test('parsePrintStatusResult rechaza B3 con menos de 8 bytes', () => {
  assert.throws(
    () =>
      parsePrintStatusResult({
        command:
          NIIMBOT_REQUEST.PrintStatusResult,
        data:
          new Uint8Array(7),
      }),
    NiimbotPageStatusError,
  );
});

test('parsePrintStatusResult rechaza extensión B3 truncada', () => {
  assert.throws(
    () =>
      parsePrintStatusResult({
        command:
          NIIMBOT_REQUEST.PrintStatusResult,
        data:
          Uint8Array.of(
            0x00,
            0x01,
            0x02,
            0x03,
            0x00,
            0x04,
            0x05,
            0x06,
            0x03,
            0xaa,
          ),
      }),
    NiimbotPageStatusError,
  );
});

test('buildPrintEndPacket reproduce jcSetPrintTerminal V3: F3 01 00', () => {
  const packet =
    buildPrintEndPacket();

  assert.equal(
    packet.command,
    NIIMBOT_REQUEST.PrintEnd,
  );

  assert.deepEqual(
    Array.from(
      packet.data,
    ),
    [
      0x00,
    ],
  );

  assert.equal(
    hex(
      encodeNiimbotPacket(
        packet,
      ),
    ),
    '55 55 f3 01 00 f2 aa aa',
  );
});

test('buildPrintJobPackets produce la secuencia V3 esperada', () => {
  const raster = {
    widthPx: 8,
    heightPx: 2,
    bitmap: {
      rows: [
        Uint8Array.of(
          0xff,
        ),
        Uint8Array.of(
          0x00,
        ),
      ],
    },
  };

  const packets =
    buildPrintJobPackets(
      raster,
      {
        density: 3,
      },
    );

  const commands =
    packets.map(
      (packet) =>
        packet.command,
    );

  assert.ok(
    !commands.includes(
      NIIMBOT_REQUEST.Connect,
    ),
  );

  assert.ok(
    !commands.includes(
      NIIMBOT_REQUEST.PrintEnd,
    ),
  );

  assert.deepEqual(
    commands,
    [
      NIIMBOT_REQUEST.SetDensity,
      NIIMBOT_REQUEST.SetLabelType,
      NIIMBOT_REQUEST.PrintStart,
      NIIMBOT_REQUEST.PageStart,
      NIIMBOT_REQUEST.SetPageSize,
      NIIMBOT_REQUEST.PrintBitmapRow,
      NIIMBOT_REQUEST.PrintBitmapRow,
      NIIMBOT_REQUEST.PageEnd,
    ],
  );

  assert.deepEqual(
    Array.from(
      packets[2].data,
    ),
    [
      0x00,
      0x01,
    ],
  );

  assert.deepEqual(
    Array.from(
      packets[3].data,
    ),
    [
      0x00,
    ],
  );

  assert.deepEqual(
    Array.from(
      packets[4].data,
    ),
    [
      0x00,
      0x02,
      0x00,
      0x08,
      0x00,
      0x01,
    ],
  );

  assert.deepEqual(
    Array.from(
      packets[
        packets.length - 1
      ].data,
    ),
    [
      0x00,
    ],
  );
});

test('buildPrintJobPackets pasa widthPx real a encodeRowPacket', () => {
  const raster = {
    widthPx: 20,
    heightPx: 1,
    bitmap: {
      rows: [
        Uint8Array.of(
          0xff,
          0xff,
          0xf0,
        ),
      ],
    },
  };

  const packets =
    buildPrintJobPackets(
      raster,
    );

  const rowPacket =
    packets.find(
      (packet) =>
        packet.command ===
        NIIMBOT_REQUEST.PrintBitmapRow,
    );

  assert.ok(
    rowPacket,
  );

  assert.deepEqual(
    Array.from(
      rowPacket.data.subarray(
        0,
        6,
      ),
    ),
    [
      0,
      0,
      0,
      0,
      0,
      1,
    ],
  );
});

test('buildPrintJobPackets es determinista', () => {
  const raster = {
    widthPx: 8,
    heightPx: 1,
    bitmap: {
      rows: [
        Uint8Array.of(
          0x0f,
        ),
      ],
    },
  };

  const first =
    buildPrintJobPackets(
      raster,
      {
        density: 4,
      },
    ).map(
      (packet) =>
        hex(
          encodeNiimbotPacket(
            packet,
          ),
        ),
    );

  const second =
    buildPrintJobPackets(
      raster,
      {
        density: 4,
      },
    ).map(
      (packet) =>
        hex(
          encodeNiimbotPacket(
            packet,
          ),
        ),
    );

  assert.deepEqual(
    first,
    second,
  );
});

test('cada fila produce su propio PrintBitmapRow con índice correcto', () => {
  const raster = {
    widthPx: 8,
    heightPx: 3,
    bitmap: {
      rows: [
        Uint8Array.of(1),
        Uint8Array.of(2),
        Uint8Array.of(3),
      ],
    },
  };

  const rowPackets =
    buildPrintJobPackets(
      raster,
    ).filter(
      (packet) =>
        packet.command ===
        NIIMBOT_REQUEST.PrintBitmapRow,
    );

  assert.equal(
    rowPackets.length,
    3,
  );

  rowPackets.forEach(
    (
      packet,
      index,
    ) => {
      const rowIndex =
        (
          packet.data[0] <<
          8
        ) |
        packet.data[1];

      assert.equal(
        rowIndex,
        index,
      );
    },
  );
});

test('helpers de comandos usan los opcodes auditados', () => {
  assert.equal(
    buildPageStartPacket()
      .command,
    NIIMBOT_REQUEST.PageStart,
  );

  assert.equal(
    buildPageEndPacket()
      .command,
    NIIMBOT_REQUEST.PageEnd,
  );

  assert.equal(
    buildPrintEndPacket()
      .command,
    NIIMBOT_REQUEST.PrintEnd,
  );

  const printStatus =
    buildPrintStatusQueryPacket();

  assert.equal(
    printStatus.command,
    NIIMBOT_REQUEST.PrintStatus,
  );

  assert.deepEqual(
    Array.from(
      printStatus.data,
    ),
    [
      0x00,
    ],
  );

  assert.equal(
    buildSetLabelTypePacket()
      .command,
    NIIMBOT_REQUEST.SetLabelType,
  );

  assert.deepEqual(
    Array.from(
      buildSetDensityPacket(
        2,
      ).data,
    ),
    [
      2,
    ],
  );
});