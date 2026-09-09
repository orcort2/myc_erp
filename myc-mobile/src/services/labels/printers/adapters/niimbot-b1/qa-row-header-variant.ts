/**
 * Herramienta exclusiva de QA física para NIIMBOT B1.
 *
 * NO forma parte del camino normal de printLabel().
 *
 * Después de inspeccionar el SDK oficial NIIMBOT V3 se añadió una tercera
 * variante de header:
 *
 *   official_v3_white_counts
 *
 * que reproduce el formato observado en packageOneColorData():
 *
 *   ROW_HI
 *   ROW_LO
 *   WHITE_COUNT_0_191
 *   WHITE_COUNT_192_383
 *   WHITE_COUNT_384_PLUS
 *   REPEAT
 *   RASTER...
 *
 * Se conservan temporalmente las dos variantes QA anteriores para no romper
 * los consumidores existentes mientras se migran archivo por archivo:
 *
 *   zero_count
 *   documented_black_pixel_count
 *
 * La siguiente etapa retirará esos nombres del UI una vez que todos sus
 * consumidores hayan sido actualizados.
 */

import type { NiimbotPacket } from './protocol';

import {
  NIIMBOT_REQUEST,
  buildPageEndPacket,
  buildPageStartPacket,
  buildPrintStartPacket,
  buildSetDensityPacket,
  buildSetLabelTypePacket,
  buildSetPageSizePacket,
  countV3WhitePixels,
} from './protocol';

export type RowHeaderVariant =
  | 'zero_count'
  | 'documented_black_pixel_count'
  | 'official_v3_white_counts';

export type QaRaster = {
  widthPx: number;
  heightPx: number;
  rows: Uint8Array[];
};

/**
 * Compatibilidad temporal con la QA anterior.
 *
 * Cuenta bits 1 del raster:
 *
 *   1 = negro/tinta
 *
 * Se mantiene exportada porque label-print-service.ts y los tests actuales
 * todavía la importan.
 */
export function countBlackPixels(
  packedRowBytes: Uint8Array,
): number {
  let count = 0;

  for (const byte of packedRowBytes) {
    let value = byte;

    while (value !== 0) {
      count += value & 1;
      value >>>= 1;
    }
  }

  return count;
}

/**
 * Barra negra sólida independiente del renderer de etiquetas.
 *
 * 384 px = ancho imprimible B1.
 * 64 px de alto = prueba visible pero pequeña.
 */
export function buildQaBlackBarRaster(
  options?: {
    widthPx?: number;
    heightPx?: number;
  },
): QaRaster {
  const widthPx =
    options?.widthPx ?? 384;

  const heightPx =
    options?.heightPx ?? 64;

  if (
    !Number.isInteger(widthPx) ||
    widthPx <= 0
  ) {
    throw new RangeError(
      `QA NIIMBOT: widthPx inválido (${widthPx})`,
    );
  }

  if (
    !Number.isInteger(heightPx) ||
    heightPx <= 0
  ) {
    throw new RangeError(
      `QA NIIMBOT: heightPx inválido (${heightPx})`,
    );
  }

  const strideBytes =
    Math.ceil(widthPx / 8);

  const fullByteCount =
    Math.floor(widthPx / 8);

  const remainderBits =
    widthPx % 8;

  const row =
    new Uint8Array(strideBytes);

  row.fill(
    0xff,
    0,
    fullByteCount,
  );

  if (remainderBits > 0) {
    row[fullByteCount] =
      (0xff << (8 - remainderBits)) & 0xff;
  }

  return {
    widthPx,
    heightPx,
    rows: Array.from(
      { length: heightPx },
      () => row.slice(),
    ),
  };
}

/**
 * Raster diagnóstico que permite distinguir realmente los headers.
 *
 * Una fila 100% negra NO permite diferenciar zero_count de la variante
 * oficial, porque en ambos casos los tres contadores son 00 00 00.
 *
 * Por eso este raster contiene bandas:
 *
 * 1. negra completa;
 * 2. blanca completa;
 * 3. mitad izquierda negra / mitad derecha blanca;
 * 4. mitad izquierda blanca / mitad derecha negra.
 */
export function buildQaDiagnosticRaster(
  options?: {
    widthPx?: number;
    heightPx?: number;
  },
): QaRaster {
  const widthPx =
    options?.widthPx ?? 384;

  const heightPx =
    options?.heightPx ?? 64;

  if (widthPx !== 384) {
    throw new RangeError(
      'QA diagnóstico V3 está diseñado para widthPx=384',
    );
  }

  if (
    !Number.isInteger(heightPx) ||
    heightPx <= 0
  ) {
    throw new RangeError(
      `QA NIIMBOT: heightPx inválido (${heightPx})`,
    );
  }

  const strideBytes =
    widthPx / 8;

  const blackRow =
    new Uint8Array(strideBytes);

  blackRow.fill(0xff);

  const whiteRow =
    new Uint8Array(strideBytes);

  whiteRow.fill(0x00);

  const leftBlackRightWhite =
    new Uint8Array(strideBytes);

  leftBlackRightWhite.fill(
    0xff,
    0,
    24,
  );

  leftBlackRightWhite.fill(
    0x00,
    24,
  );

  const leftWhiteRightBlack =
    new Uint8Array(strideBytes);

  leftWhiteRightBlack.fill(
    0x00,
    0,
    24,
  );

  leftWhiteRightBlack.fill(
    0xff,
    24,
  );

  const templates = [
    blackRow,
    whiteRow,
    leftBlackRightWhite,
    leftWhiteRightBlack,
  ];

  const rows =
    Array.from(
      { length: heightPx },
      (_, index) =>
        templates[
          Math.floor(index / 16) %
          templates.length
        ].slice(),
    );

  return {
    widthPx,
    heightPx,
    rows,
  };
}

export function encodeQaRowPacket(
  rowIndex: number,
  packedRowBytes: Uint8Array,
  widthPx: number,
  variant: RowHeaderVariant,
): NiimbotPacket {
  if (
    !Number.isInteger(rowIndex) ||
    rowIndex < 0 ||
    rowIndex > 0xffff
  ) {
    throw new RangeError(
      `QA NIIMBOT: rowIndex inválido (${rowIndex})`,
    );
  }

  const header =
    new Uint8Array(6);

  header[0] =
    (rowIndex >> 8) & 0xff;

  header[1] =
    rowIndex & 0xff;

  if (
    variant ===
    'documented_black_pixel_count'
  ) {
    /**
     * Variante histórica de QA.
     *
     * Se conserva sin alterar hasta migrar sus tests/consumidores.
     */
    const blackPixelCount =
      countBlackPixels(
        packedRowBytes,
      );

    header[2] =
      (blackPixelCount >> 8) &
      0xff;

    header[3] =
      blackPixelCount &
      0xff;

    header[4] = 0;
  } else if (
    variant ===
    'official_v3_white_counts'
  ) {
    const [
      count0,
      count1,
      count2,
    ] = countV3WhitePixels(
      packedRowBytes,
      widthPx,
    );

    header[2] = count0;
    header[3] = count1;
    header[4] = count2;
  }

  /**
   * Tanto la QA histórica como el SDK oficial usan:
   *
   * repeat = 1
   *
   * para la primera/única fila del bloque.
   */
  header[5] = 1;

  const data =
    new Uint8Array(
      header.length +
      packedRowBytes.length,
    );

  data.set(
    header,
    0,
  );

  data.set(
    packedRowBytes,
    header.length,
  );

  return {
    command:
      NIIMBOT_REQUEST.PrintBitmapRow,
    data,
  };
}

export function buildQaPrintJobPackets(
  raster: QaRaster,
  variant: RowHeaderVariant,
  options?: {
    density?: number;
  },
): NiimbotPacket[] {
  const packets: NiimbotPacket[] = [
    buildSetDensityPacket(
      options?.density,
    ),
    buildSetLabelTypePacket(),
    buildPrintStartPacket(1),
    buildPageStartPacket(),
    buildSetPageSizePacket(
      raster.widthPx,
      raster.heightPx,
    ),
  ];

  raster.rows.forEach(
    (row, index) => {
      packets.push(
        encodeQaRowPacket(
          index,
          row,
          raster.widthPx,
          variant,
        ),
      );
    },
  );

  packets.push(
    buildPageEndPacket(),
  );

  return packets;
}