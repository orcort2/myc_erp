import assert from 'node:assert/strict';
import test from 'node:test';

import {
  buildQaBlackBarRaster,
  buildQaDiagnosticRaster,
  buildQaPrintJobPackets,
  countBlackPixels,
} from './qa-row-header-variant';

import {
  NIIMBOT_REQUEST,
  buildPrintJobPackets,
  countV3WhitePixels,
  decodeNiimbotPacket,
  encodeNiimbotPacket,
} from './protocol';

test('countBlackPixels cuenta exactamente los bits en 1', () => {
  assert.equal(
    countBlackPixels(Uint8Array.of(0xff)),
    8,
  );

  assert.equal(
    countBlackPixels(Uint8Array.of(0x00)),
    0,
  );

  assert.equal(
    countBlackPixels(
      Uint8Array.of(
        0b10101010,
      ),
    ),
    4,
  );

  assert.equal(
    countBlackPixels(
      Uint8Array.of(
        0b11110000,
        0b00001111,
      ),
    ),
    8,
  );
});

test('countV3WhitePixels interpreta 1=negro y 0=blanco', () => {
  assert.deepEqual(
    countV3WhitePixels(
      Uint8Array.of(0xff),
      8,
    ),
    [0, 0, 0],
  );

  assert.deepEqual(
    countV3WhitePixels(
      Uint8Array.of(0x00),
      8,
    ),
    [8, 0, 0],
  );

  assert.deepEqual(
    countV3WhitePixels(
      Uint8Array.of(
        0b11110000,
      ),
      8,
    ),
    [4, 0, 0],
  );
});

test('countV3WhitePixels divide una fila B1 de 384 px en regiones de 192/192', () => {
  const white =
    new Uint8Array(48);

  assert.deepEqual(
    countV3WhitePixels(
      white,
      384,
    ),
    [192, 192, 0],
  );

  const black =
    new Uint8Array(48);

  black.fill(0xff);

  assert.deepEqual(
    countV3WhitePixels(
      black,
      384,
    ),
    [0, 0, 0],
  );
});

test('countV3WhitePixels distingue izquierda y derecha en una fila de 384 px', () => {
  const leftBlackRightWhite =
    new Uint8Array(48);

  leftBlackRightWhite.fill(
    0xff,
    0,
    24,
  );

  assert.deepEqual(
    countV3WhitePixels(
      leftBlackRightWhite,
      384,
    ),
    [0, 192, 0],
  );

  const leftWhiteRightBlack =
    new Uint8Array(48);

  leftWhiteRightBlack.fill(
    0xff,
    24,
  );

  assert.deepEqual(
    countV3WhitePixels(
      leftWhiteRightBlack,
      384,
    ),
    [192, 0, 0],
  );
});

test('buildQaBlackBarRaster produce una barra negra sólida de 384x64', () => {
  const raster =
    buildQaBlackBarRaster();

  assert.equal(
    raster.widthPx,
    384,
  );

  assert.equal(
    raster.heightPx,
    64,
  );

  assert.equal(
    raster.rows.length,
    64,
  );

  for (
    const row
    of raster.rows
  ) {
    assert.equal(
      row.length,
      48,
    );

    assert.equal(
      countBlackPixels(row),
      384,
    );

    assert.deepEqual(
      countV3WhitePixels(
        row,
        384,
      ),
      [0, 0, 0],
    );
  }
});

test('buildQaBlackBarRaster respeta relleno cuando el ancho no es múltiplo de 8', () => {
  const raster =
    buildQaBlackBarRaster({
      widthPx: 20,
      heightPx: 3,
    });

  assert.equal(
    raster.rows.length,
    3,
  );

  for (
    const row
    of raster.rows
  ) {
    assert.equal(
      row.length,
      3,
    );

    assert.equal(
      countBlackPixels(row),
      20,
    );

    assert.deepEqual(
      countV3WhitePixels(
        row,
        20,
      ),
      [0, 0, 0],
    );
  }
});

test('cada fila de buildQaBlackBarRaster es independiente', () => {
  const raster =
    buildQaBlackBarRaster({
      widthPx: 8,
      heightPx: 2,
    });

  raster.rows[0][0] =
    0x00;

  assert.equal(
    countBlackPixels(
      raster.rows[0],
    ),
    0,
  );

  assert.equal(
    countBlackPixels(
      raster.rows[1],
    ),
    8,
  );
});

test('buildQaDiagnosticRaster genera las cuatro bandas diagnósticas esperadas', () => {
  const raster =
    buildQaDiagnosticRaster();

  assert.equal(
    raster.widthPx,
    384,
  );

  assert.equal(
    raster.heightPx,
    64,
  );

  assert.equal(
    raster.rows.length,
    64,
  );

  // Filas 0..15:
  // negro completo.
  assert.deepEqual(
    countV3WhitePixels(
      raster.rows[0],
      384,
    ),
    [0, 0, 0],
  );

  assert.equal(
    countBlackPixels(
      raster.rows[0],
    ),
    384,
  );

  // Filas 16..31:
  // blanco completo.
  assert.deepEqual(
    countV3WhitePixels(
      raster.rows[16],
      384,
    ),
    [192, 192, 0],
  );

  assert.equal(
    countBlackPixels(
      raster.rows[16],
    ),
    0,
  );

  // Filas 32..47:
  // izquierda negra / derecha blanca.
  assert.deepEqual(
    countV3WhitePixels(
      raster.rows[32],
      384,
    ),
    [0, 192, 0],
  );

  // Filas 48..63:
  // izquierda blanca / derecha negra.
  assert.deepEqual(
    countV3WhitePixels(
      raster.rows[48],
      384,
    ),
    [192, 0, 0],
  );
});

test('official_v3_white_counts reproduce exactamente el camino actual de producción', () => {
  const raster =
    buildQaDiagnosticRaster();

  const qaPackets =
    buildQaPrintJobPackets(
      raster,
      'official_v3_white_counts',
      {
        density: 3,
      },
    );

  const productionPackets =
    buildPrintJobPackets(
      {
        widthPx:
          raster.widthPx,

        heightPx:
          raster.heightPx,

        bitmap: {
          rows:
            raster.rows,
        },
      },
      {
        density: 3,
      },
    );

  assert.equal(
    qaPackets.length,
    productionPackets.length,
  );

  for (
    let index = 0;
    index < qaPackets.length;
    index += 1
  ) {
    assert.equal(
      qaPackets[index].command,
      productionPackets[index].command,
      `comando distinto en paquete ${index}`,
    );

    assert.deepEqual(
      Array.from(
        qaPackets[index].data,
      ),
      Array.from(
        productionPackets[index].data,
      ),
      `bytes distintos en paquete ${index}`,
    );
  }
});

test('zero_count conserva deliberadamente el header legado para comparación física', () => {
  const raster =
    buildQaDiagnosticRaster({
      heightPx: 64,
    });

  const packets =
    buildQaPrintJobPackets(
      raster,
      'zero_count',
    );

  const rows =
    packets.filter(
      (packet) =>
        packet.command ===
        NIIMBOT_REQUEST.PrintBitmapRow,
    );

  assert.equal(
    rows.length,
    64,
  );

  // Incluso la fila completamente blanca
  // sigue enviando los contadores históricos
  // en cero.
  const whiteRow =
    rows[16];

  assert.deepEqual(
    Array.from(
      whiteRow.data.subarray(
        2,
        6,
      ),
    ),
    [
      0,
      0,
      0,
      1,
    ],
  );
});

test('official_v3_white_counts serializa correctamente una fila completamente negra', () => {
  const raster =
    buildQaBlackBarRaster({
      widthPx: 384,
      heightPx: 1,
    });

  const packets =
    buildQaPrintJobPackets(
      raster,
      'official_v3_white_counts',
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

  assert.equal(
    rowPacket.data.length,
    54,
  );

  assert.deepEqual(
    Array.from(
      rowPacket.data.subarray(
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

  assert.deepEqual(
    Array.from(
      rowPacket.data.subarray(
        6,
      ),
    ),
    Array.from(
      new Uint8Array(48).fill(
        0xff,
      ),
    ),
  );
});

test('official_v3_white_counts serializa C0 C0 00 para una fila completamente blanca de 384 px', () => {
  const raster = {
    widthPx:
      384,

    heightPx:
      1,

    rows: [
      new Uint8Array(
        48,
      ),
    ],
  };

  const packets =
    buildQaPrintJobPackets(
      raster,
      'official_v3_white_counts',
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
      0x00,
      0x00,
      0xc0,
      0xc0,
      0x00,
      0x01,
    ],
  );

  assert.deepEqual(
    Array.from(
      rowPacket.data.subarray(
        6,
      ),
    ),
    Array.from(
      new Uint8Array(48),
    ),
  );
});

test('official_v3_white_counts mantiene el índice de fila big-endian', () => {
  const raster = {
    widthPx:
      8,

    heightPx:
      258,

    rows:
      Array.from(
        {
          length:
            258,
        },
        () =>
          Uint8Array.of(
            0xff,
          ),
      ),
  };

  const packets =
    buildQaPrintJobPackets(
      raster,
      'official_v3_white_counts',
    );

  const rows =
    packets.filter(
      (packet) =>
        packet.command ===
        NIIMBOT_REQUEST.PrintBitmapRow,
    );

  const row257 =
    rows[257];

  assert.equal(
    row257.data[0],
    0x01,
  );

  assert.equal(
    row257.data[1],
    0x01,
  );

  assert.equal(
    row257.data[5],
    0x01,
  );
});

test('legacy y oficial tienen el mismo raster y sólo divergen en los contadores', () => {
  const raster =
    buildQaDiagnosticRaster();

  const legacy =
    buildQaPrintJobPackets(
      raster,
      'zero_count',
    );

  const official =
    buildQaPrintJobPackets(
      raster,
      'official_v3_white_counts',
    );

  const legacyRows =
    legacy.filter(
      (packet) =>
        packet.command ===
        NIIMBOT_REQUEST.PrintBitmapRow,
    );

  const officialRows =
    official.filter(
      (packet) =>
        packet.command ===
        NIIMBOT_REQUEST.PrintBitmapRow,
    );

  assert.equal(
    legacyRows.length,
    officialRows.length,
  );

  // Negro completo:
  // los headers coinciden porque no hay
  // píxeles blancos.
  assert.deepEqual(
    Array.from(
      legacyRows[0].data,
    ),
    Array.from(
      officialRows[0].data,
    ),
  );

  // Blanco completo:
  // ahora sí deben divergir.
  assert.notDeepEqual(
    Array.from(
      legacyRows[16].data,
    ),
    Array.from(
      officialRows[16].data,
    ),
  );

  // El raster debe ser idéntico.
  assert.deepEqual(
    Array.from(
      legacyRows[16].data.subarray(
        6,
      ),
    ),
    Array.from(
      officialRows[16].data.subarray(
        6,
      ),
    ),
  );
});

test('los paquetes QA oficiales sobreviven encode/decode del framing NIIMBOT sin cambiar un byte', () => {
  const raster =
    buildQaDiagnosticRaster({
      heightPx: 4,
    });

  const packets =
    buildQaPrintJobPackets(
      raster,
      'official_v3_white_counts',
    );

  const rows =
    packets.filter(
      (packet) =>
        packet.command ===
        NIIMBOT_REQUEST.PrintBitmapRow,
    );

  for (
    const rowPacket
    of rows
  ) {
    const framed =
      encodeNiimbotPacket(
        rowPacket,
      );

    const decoded =
      decodeNiimbotPacket(
        framed,
      );

    assert.equal(
      decoded.command,
      NIIMBOT_REQUEST.PrintBitmapRow,
    );

    assert.deepEqual(
      Array.from(
        decoded.data,
      ),
      Array.from(
        rowPacket.data,
      ),
    );

    assert.equal(
      framed[0],
      0x55,
    );

    assert.equal(
      framed[1],
      0x55,
    );

    assert.equal(
      framed[
        framed.length - 2
      ],
      0xaa,
    );

    assert.equal(
      framed[
        framed.length - 1
      ],
      0xaa,
    );
  }
});