/**
 * Herramienta de QA/desarrollo -- NUNCA usada por printLabel() ni por ningún
 * flujo de producción. Existe exclusivamente para la próxima sesión de QA
 * física del B1 (ver docs/architecture/LAB_LABEL_PRINTING.md, "Gate de QA
 * física"): la primera prueba real confirmó conexión, aceptación y ejecución
 * del trabajo, pero SIN contenido impreso -- una divergencia ya documentada
 * en protocol.ts ("Divergencia NO resuelta") sobre el header de
 * PrintBitmapRow es la sospecha principal.
 *
 * protocol.ts::encodeRowPacket() (el camino de PRODUCCIÓN, usado por
 * printLabel() vía buildPrintJobPackets()) sigue exactamente igual, sin
 * tocar: header de 6 bytes con conteo en cero (niimprint, la única fuente
 * confirmada contra hardware B1 real). Este archivo NO cambia esa decisión
 * a ciegas -- construye, por separado, ambas variantes documentadas para
 * que alguien con impresora física en mano pueda comparar cuál realmente
 * imprime contenido:
 *   A. 'zero_count'                 -- exactamente lo que ya hace producción.
 *   B. 'documented_black_pixel_count' -- la variante que documenta niim.blue
 *      (conteo real de píxeles negros de 16 bits en el header de fila).
 *
 * El raster usado (buildQaBlackBarRaster) es deliberadamente mínimo y obvio
 * -- un bloque negro sólido, sin texto ni layout -- para que el resultado de
 * la comparación nunca pueda confundirse con un problema de renderer/fuente/
 * maquetación de LabelRenderer.
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
} from './protocol';

export type RowHeaderVariant = 'zero_count' | 'documented_black_pixel_count';

/** Bitmap monocromático mínimo, mismo convenio que MonochromeBitmap
 * (label-types.ts): 1 bit por píxel, MSB primero, 1 = tinta/negro. Este
 * archivo no importa label-types.ts a propósito -- el raster de QA es
 * completamente independiente de LabelRenderer/LabelProfile, nunca pasa por
 * ese código, así que un bug de QA nunca podría confundirse con uno de
 * renderer real. */
export type QaRaster = { widthPx: number; heightPx: number; rows: Uint8Array[] };

/** Cuenta los bits en 1 (píxeles negros) de una fila ya empaquetada -- los
 * bits de relleno más allá de widthPx en el último byte de la fila siempre
 * son 0 (nunca "tinta"), así que un popcount simple sobre el buffer completo
 * ya es exacto, sin necesitar widthPx para enmascarar nada. */
export function countBlackPixels(packedRowBytes: Uint8Array): number {
  let count = 0;
  for (const byte of packedRowBytes) {
    let value = byte;
    while (value) {
      count += value & 1;
      value >>= 1;
    }
  }
  return count;
}

/** Bloque negro sólido, sin texto, sin layout: 384px de ancho (el máximo
 * imprimible del B1, ver capabilities.printableWidthPx) por una franja de
 * alto moderado -- claramente un bloque, no la etiqueta completa (30mm a
 * 203dpi son ~240px de alto; 64px deja margen blanco arriba/abajo visible
 * para confirmar registro/posición además de sólo "¿salió tinta?"). */
export function buildQaBlackBarRaster(options?: { widthPx?: number; heightPx?: number }): QaRaster {
  const widthPx = options?.widthPx ?? 384;
  const heightPx = options?.heightPx ?? 64;
  const strideBytes = Math.ceil(widthPx / 8);
  const fullByteCount = Math.floor(widthPx / 8);
  const remainderBits = widthPx % 8;
  const row = new Uint8Array(strideBytes);
  row.fill(0xff, 0, fullByteCount);
  if (remainderBits > 0) {
    // Sólo los remainderBits más significativos del último byte son parte
    // del ancho real -- el resto es relleno de stride, debe quedar en 0.
    row[fullByteCount] = 0xff << (8 - remainderBits) & 0xff;
  }
  return { widthPx, heightPx, rows: Array.from({ length: heightPx }, () => row.slice()) };
}

function encodeRowPacketForVariant(rowIndex: number, packedRowBytes: Uint8Array, variant: RowHeaderVariant): NiimbotPacket {
  const header = new Uint8Array(6);
  header[0] = (rowIndex >> 8) & 0xff;
  header[1] = rowIndex & 0xff;
  if (variant === 'documented_black_pixel_count') {
    const blackPixelCount = countBlackPixels(packedRowBytes);
    header[2] = (blackPixelCount >> 8) & 0xff;
    header[3] = blackPixelCount & 0xff;
  }
  // header[2]/[3] ya quedan en 0 para 'zero_count' (Uint8Array nace en
  // ceros) -- header[4] (reservado) y header[5] (repetición=1) son
  // idénticos en ambas variantes: la divergencia documentada es
  // específicamente sobre el conteo, nunca sobre estos dos bytes.
  header[4] = 0;
  header[5] = 1;
  const data = new Uint8Array(header.length + packedRowBytes.length);
  data.set(header, 0);
  data.set(packedRowBytes, header.length);
  return { command: NIIMBOT_REQUEST.PrintBitmapRow, data };
}

/** Secuencia completa de comandos para UNA variante del header de fila,
 * usando exactamente los mismos sub-paquetes que buildPrintJobPackets()
 * (producción) importados sin cambios -- SetDensity/SetLabelType/
 * PrintStart/PageStart/SetPageSize/PageEnd nunca están en duda, sólo el
 * header de PrintBitmapRow. Nunca reemplaza a buildPrintJobPackets(): es una
 * función hermana, exclusiva de esta herramienta de QA. */
export function buildQaPrintJobPackets(
  raster: QaRaster,
  variant: RowHeaderVariant,
  options?: { density?: number },
): NiimbotPacket[] {
  const packets: NiimbotPacket[] = [
    buildSetDensityPacket(options?.density),
    buildSetLabelTypePacket(),
    buildPrintStartPacket(1),
    buildPageStartPacket(),
    buildSetPageSizePacket(raster.widthPx, raster.heightPx),
  ];
  raster.rows.forEach((row, index) => packets.push(encodeRowPacketForVariant(index, row, variant)));
  packets.push(buildPageEndPacket());
  return packets;
}
