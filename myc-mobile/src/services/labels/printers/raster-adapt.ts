import type { RasterLabel } from '../label-types';

/**
 * Adaptación de un RasterLabel físico (dimensiones del LabelProfile, ver
 * label-profile.ts) al ancho REAL imprimible del cabezal de una impresora
 * concreta -- ver docs/architecture/LAB_LABEL_PRINTING.md, "B1 50x30 ->
 * printable-raster mapping".
 *
 * Por qué WIDTH es el eje limitado por el cabezal (nunca height): en el
 * protocolo NIIMBOT auditado (ver adapters/niimbot-b1/protocol.ts), cada
 * fila transmitida vía PrintBitmapRow lleva un índice de fila (creciente
 * 0..heightPx-1, uno por avance de papel) y una tira de bits de
 * `ceil(widthPx/8)` bytes -- confirmado en niimprint (_encode_image: itera
 * `range(img.height)` filas, cada una con `ceil(img.width/8)` bytes). El
 * cabezal físico es una fila FIJA de puntos térmicos perpendicular al avance
 * del papel: ese número fijo de puntos es exactamente lo que limita
 * `widthPx` (píxeles por fila). `heightPx` (cuántas filas se mandan) no
 * tiene límite de cabezal, sólo de largo de rollo/página.
 *
 * MYC_50X30.physicalWidthMm (50mm) es por lo tanto el eje que debe caber en
 * el cabezal: a 203 dpi, 384px imprimibles ~= 48.06mm, que coincide con el
 * "área segura" ~48mm que ya usa LabelRenderer -- no es casualidad, es
 * exactamente el margen físico ~1mm por lado que LabelRenderer ya deja en
 * blanco alrededor del contenido (ver label-profile.ts profileSafeAreaPx).
 * Por eso el recorte de este archivo es seguro por construcción para
 * MYC_50X30 a 203dpi: source.widthPx(400) - printableWidthPx(384) = 16px =
 * exactamente el margen izquierdo+derecho (8px cada uno) que el renderer ya
 * deja sin tinta.
 *
 * Este archivo NUNCA asume esa coincidencia ciegamente: verifica bit a bit
 * que las columnas que va a recortar estén realmente vacías antes de
 * recortarlas, y si no lo están (p.ej. un perfil/impresora futuros donde el
 * margen no alcance), bloquea con un error explícito en vez de recortar
 * contenido real en silencio. Nunca escala ni distorsiona -- sólo recorta
 * margen físico ya vacío.
 */

export class RasterExceedsPrintableWidthError extends Error {}

function packedPixelAt(row: Uint8Array, x: number): boolean {
  const byteIndex = Math.floor(x / 8);
  const bitIndex = 7 - (x % 8);
  return ((row[byteIndex] ?? 0) >> bitIndex & 1) === 1;
}

/**
 * Recorta un RasterLabel al ancho imprimible real de un cabezal, quitando
 * únicamente margen físico ya vacío en ambos bordes (repartido lo más
 * simétrico posible). heightPx (eje de avance de papel) nunca se toca.
 * Si el raster ya cabe (widthPx <= printableWidthPx), lo devuelve tal cual.
 */
export function cropRasterToPrintableWidth(raster: RasterLabel, printableWidthPx: number): RasterLabel {
  if (raster.widthPx <= printableWidthPx) return raster;

  const totalMarginPx = raster.widthPx - printableWidthPx;
  const leftMarginPx = Math.floor(totalMarginPx / 2);
  const rightMarginPx = totalMarginPx - leftMarginPx;
  const contentStartPx = leftMarginPx;
  const contentEndPx = raster.widthPx - rightMarginPx; // exclusivo

  for (const row of raster.bitmap.rows) {
    for (let x = 0; x < contentStartPx; x += 1) {
      if (packedPixelAt(row, x)) {
        throw new RasterExceedsPrintableWidthError(
          `El contenido de la etiqueta excede el ancho imprimible del cabezal (${printableWidthPx}px); ` +
            `se encontró tinta en el margen izquierdo (columna ${x}) que se esperaba vacío.`,
        );
      }
    }
    for (let x = contentEndPx; x < raster.widthPx; x += 1) {
      if (packedPixelAt(row, x)) {
        throw new RasterExceedsPrintableWidthError(
          `El contenido de la etiqueta excede el ancho imprimible del cabezal (${printableWidthPx}px); ` +
            `se encontró tinta en el margen derecho (columna ${x}) que se esperaba vacío.`,
        );
      }
    }
  }

  const newStride = Math.ceil(printableWidthPx / 8);
  const newRows = raster.bitmap.rows.map((row) => {
    const newRow = new Uint8Array(newStride);
    for (let x = 0; x < printableWidthPx; x += 1) {
      if (!packedPixelAt(row, x + contentStartPx)) continue;
      const byteIndex = Math.floor(x / 8);
      const bitIndex = 7 - (x % 8);
      newRow[byteIndex] |= 1 << bitIndex;
    }
    return newRow;
  });

  return {
    widthPx: printableWidthPx,
    heightPx: raster.heightPx,
    bitmap: { widthPx: printableWidthPx, heightPx: raster.heightPx, rows: newRows },
    profileId: raster.profileId,
  };
}
