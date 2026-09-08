/**
 * Protocolo BLE NIIMBOT (variante "b1", protocolo v3, 203 dpi -- usada por
 * B1/B21/D11, distinta de la variante v4 de impresoras más nuevas a 300
 * dpi). Ningún comando aquí se inventó: cada uno está cruzado contra al
 * menos dos implementaciones open-source independientes y activamente
 * mantenidas antes de escribirse (ver AUDITORÍA DE FUENTES abajo). Aun así,
 * NINGÚN byte de este archivo se ha validado contra hardware B1 físico
 * todavía -- eso es exactamente el gate de QA física de la Fase 29 de la
 * misión, no algo que este archivo pueda resolver por sí solo.
 *
 * AUDITORÍA DE FUENTES (2026-09-07):
 * 1. https://printers.niim.blue/interfacing/ (NIIMBOT Community Wiki,
 *    proyecto MultiMote/niimblue) -- documenta framing, checksum, UUIDs BLE,
 *    tabla completa de opcodes "b1", y el orden de la secuencia de
 *    impresión incluyendo el handshake posterior a conectar y el poll de
 *    estado antes de PrintEnd.
 * 2. https://github.com/AndBondStyle/niimprint (Python, probado
 *    explícitamente contra B1 según su propio README) -- confirma
 *    exactamente el mismo framing/checksum (NiimbotPacket.to_bytes/
 *    from_bytes) y los mismos valores de opcode (RequestCodeEnum), pero
 *    implementa la codificación de fila SIN el conteo real de píxeles
 *    negros ni la optimización de fila vacía (envía cada fila
 *    individualmente con conteos en cero y repetición=1) -- ver
 *    encodeRowPacket abajo: se adoptó deliberadamente esta variante más
 *    simple y confirmada-funcional en vez de la optimización de
 *    niim.blue, para reducir superficie de riesgo del primer bring-up.
 * 3. https://github.com/MultiMote/niimbluelib (TypeScript, "la
 *    implementación open-source más precisa del protocolo" según su propia
 *    descripción) -- confirma el mismo UUID de servicio/característica, el
 *    mismo orden connect->identify->heartbeat periódico (una sola vez por
 *    conexión, NUNCA repetido por cada trabajo de impresión) y la misma
 *    secuencia de impresión (density->labelType->printStart->[pageStart->
 *    pageSize->filas->pageEnd]->poll de estado).
 *
 * Divergencia NO resuelta entre fuentes (marcada explícitamente, no
 * silenciada): niim.blue documenta un conteo real de píxeles negros de 16
 * bits en el header de fila; niimprint (probado en B1 real) siempre manda
 * ceros ahí y funciona. Se siguió la variante de niimprint por ser la única
 * confirmada contra hardware real. Validar durante QA física.
 */

export const NIIMBOT_BLE_SERVICE_UUID = 'e7810a71-73ae-499d-8c15-faa9aef0c3f2';
export const NIIMBOT_BLE_CHARACTERISTIC_UUID = 'bef8d6c9-9c21-4c9e-b632-bd58c1009f9f';

export const NIIMBOT_REQUEST = {
  Connect: 0xc1,
  ConnectResult: 0xc2,
  PrinterStatusData: 0xa5,
  PrinterStatusDataResult: 0xb5,
  PrinterInfo: 0x40,
  Heartbeat: 0xdc,
  HeartbeatResult: 0xd9,
  SetDensity: 0x21,
  SetDensityResult: 0x31,
  SetLabelType: 0x23,
  SetLabelTypeResult: 0x33,
  PrintStart: 0x01,
  PrintStartResult: 0x02,
  PageStart: 0x03,
  PageStartResult: 0x04,
  SetPageSize: 0x13,
  SetPageSizeResult: 0x14,
  PrintBitmapRow: 0x85,
  PageEnd: 0xe3,
  PageEndResult: 0xe4,
  PrintStatus: 0xa3,
  PrintStatusResult: 0xb3,
  PrintEnd: 0xf3,
  PrintEndResult: 0xf4,
} as const;

export type NiimbotRequestCode = (typeof NIIMBOT_REQUEST)[keyof typeof NIIMBOT_REQUEST];

export type NiimbotPacket = { command: number; data: Uint8Array };
export type DecodedNiimbotPacket = { command: number; data: Uint8Array };

const HEADER_BYTE = 0x55;
const FOOTER_BYTE = 0xaa;
const MAX_DATA_LENGTH = 255;

function checksumOf(command: number, data: Uint8Array): number {
  let checksum = (command ^ data.length) & 0xff;
  for (const byte of data) checksum ^= byte;
  return checksum & 0xff;
}

/** [0x55,0x55, cmd, len, ...data, checksum, 0xAA,0xAA] -- checksum = cmd XOR
 * len XOR (todos los bytes de datos). Confirmado idéntico en las 3 fuentes
 * auditadas arriba. */
export function encodeNiimbotPacket(packet: NiimbotPacket): Uint8Array {
  const { command, data } = packet;
  if (data.length > MAX_DATA_LENGTH) {
    throw new RangeError(`Paquete NIIMBOT: datos exceden ${MAX_DATA_LENGTH} bytes (${data.length})`);
  }
  const out = new Uint8Array(data.length + 7);
  out[0] = HEADER_BYTE;
  out[1] = HEADER_BYTE;
  out[2] = command & 0xff;
  out[3] = data.length & 0xff;
  out.set(data, 4);
  out[4 + data.length] = checksumOf(command, data);
  out[5 + data.length] = FOOTER_BYTE;
  out[6 + data.length] = FOOTER_BYTE;
  return out;
}

export class NiimbotFrameError extends Error {}

/** Decodifica EXACTAMENTE un frame completo (bytes.length debe ser
 * precisamente len+7). Para flujos BLE reales, donde una notificación puede
 * traer un frame parcial o varios concatenados, usar NiimbotFrameAssembler
 * en vez de esta función directamente. */
export function decodeNiimbotPacket(bytes: Uint8Array): DecodedNiimbotPacket {
  if (bytes.length < 7) throw new NiimbotFrameError('Paquete NIIMBOT demasiado corto');
  if (bytes[0] !== HEADER_BYTE || bytes[1] !== HEADER_BYTE) {
    throw new NiimbotFrameError('Encabezado NIIMBOT inválido');
  }
  const command = bytes[2];
  const length = bytes[3];
  if (bytes.length !== length + 7) {
    throw new NiimbotFrameError('Longitud de paquete NIIMBOT inconsistente');
  }
  const data = bytes.slice(4, 4 + length);
  const checksumByte = bytes[4 + length];
  if (bytes[5 + length] !== FOOTER_BYTE || bytes[6 + length] !== FOOTER_BYTE) {
    throw new NiimbotFrameError('Pie NIIMBOT inválido');
  }
  if (checksumByte !== checksumOf(command, data)) {
    throw new NiimbotFrameError('Checksum NIIMBOT inválido');
  }
  return { command, data };
}

/**
 * Reensamblador con estado para notificaciones BLE fragmentadas -- tanto
 * BLE clásico como serie pueden partir un frame lógico en varios paquetes
 * de radio (ver "Fragmentation Warning" en niim.blue/interfacing). Nunca
 * asume que una notificación == un frame completo: acumula bytes, descarta
 * basura previa al primer 0x55 0x55, y sólo entrega paquetes una vez que el
 * frame completo (según su propio campo de longitud) está disponible. Un
 * frame con checksum/pie inválido se descarta y se sigue buscando el
 * próximo encabezado, en vez de tirar todo el buffer.
 */
export class NiimbotFrameAssembler {
  private buffer: number[] = [];

  push(chunk: Uint8Array): DecodedNiimbotPacket[] {
    for (const byte of chunk) this.buffer.push(byte);
    const packets: DecodedNiimbotPacket[] = [];
    for (;;) {
      const headerIndex = this.indexOfHeader();
      if (headerIndex === -1) {
        // Sin ningún candidato a encabezado en todo el buffer: es basura.
        this.buffer = [];
        break;
      }
      if (headerIndex > 0) this.buffer.splice(0, headerIndex);
      if (this.buffer.length < 4) break; // aún no llega ni el byte de longitud
      const length = this.buffer[3];
      const totalLength = length + 7;
      if (this.buffer.length < totalLength) break; // frame incompleto, esperar más datos
      const frame = Uint8Array.from(this.buffer.slice(0, totalLength));
      this.buffer.splice(0, totalLength);
      try {
        packets.push(decodeNiimbotPacket(frame));
      } catch {
        // Frame corrupto (checksum/pie inválido): se descarta y se continúa
        // buscando el próximo encabezado dentro de lo que ya quedó en buffer.
      }
    }
    return packets;
  }

  reset(): void {
    this.buffer = [];
  }

  private indexOfHeader(): number {
    for (let i = 0; i < this.buffer.length - 1; i += 1) {
      if (this.buffer[i] === HEADER_BYTE && this.buffer[i + 1] === HEADER_BYTE) return i;
    }
    // Un único 0x55 colgando al final podría ser el inicio de un encabezado
    // que aún no terminó de llegar -- se conserva en vez de descartarse.
    if (this.buffer.length >= 1 && this.buffer[this.buffer.length - 1] === HEADER_BYTE) {
      return this.buffer.length - 1;
    }
    return -1;
  }
}

/** Empaqueta una fila del raster como PrintBitmapRow -- header de 6 bytes
 * (índice de fila BE de 16 bits, tres bytes de conteo en cero, repetición
 * fija en 1) seguido de los bytes ya empaquetados MSB-first de la fila. Sin
 * optimización de fila vacía/run-length en v1 (ver AUDITORÍA DE FUENTES). */
export function encodeRowPacket(rowIndex: number, packedRowBytes: Uint8Array): NiimbotPacket {
  const header = new Uint8Array(6);
  header[0] = (rowIndex >> 8) & 0xff;
  header[1] = rowIndex & 0xff;
  header[2] = 0;
  header[3] = 0;
  header[4] = 0;
  header[5] = 1;
  const data = new Uint8Array(header.length + packedRowBytes.length);
  data.set(header, 0);
  data.set(packedRowBytes, header.length);
  return { command: NIIMBOT_REQUEST.PrintBitmapRow, data };
}

export function buildConnectPacket(): NiimbotPacket {
  return { command: NIIMBOT_REQUEST.Connect, data: Uint8Array.of(1) };
}

export function buildPrinterStatusDataPacket(): NiimbotPacket {
  return { command: NIIMBOT_REQUEST.PrinterStatusData, data: Uint8Array.of(1) };
}

export function buildPrinterInfoPacket(subCode: number): NiimbotPacket {
  return { command: NIIMBOT_REQUEST.PrinterInfo, data: Uint8Array.of(subCode & 0xff) };
}

export function buildHeartbeatPacket(): NiimbotPacket {
  return { command: NIIMBOT_REQUEST.Heartbeat, data: Uint8Array.of(4) };
}

const MIN_DENSITY = 1;
const MAX_DENSITY = 5;
const DEFAULT_DENSITY = 3;

export function clampDensity(density: number | undefined): number {
  if (density === undefined || Number.isNaN(density)) return DEFAULT_DENSITY;
  return Math.min(MAX_DENSITY, Math.max(MIN_DENSITY, Math.round(density)));
}

export function buildSetDensityPacket(density: number | undefined): NiimbotPacket {
  return { command: NIIMBOT_REQUEST.SetDensity, data: Uint8Array.of(clampDensity(density)) };
}

export function buildSetLabelTypePacket(): NiimbotPacket {
  return { command: NIIMBOT_REQUEST.SetLabelType, data: Uint8Array.of(1) };
}

export function buildPrintStartPacket(pageCount: number): NiimbotPacket {
  const data = new Uint8Array(7);
  data[0] = (pageCount >> 8) & 0xff;
  data[1] = pageCount & 0xff;
  return { command: NIIMBOT_REQUEST.PrintStart, data };
}

export function buildPageStartPacket(): NiimbotPacket {
  return { command: NIIMBOT_REQUEST.PageStart, data: Uint8Array.of(1) };
}

export function buildSetPageSizePacket(widthPx: number, heightPx: number): NiimbotPacket {
  const data = new Uint8Array(6);
  data[0] = (heightPx >> 8) & 0xff;
  data[1] = heightPx & 0xff;
  data[2] = (widthPx >> 8) & 0xff;
  data[3] = widthPx & 0xff;
  data[4] = 0;
  data[5] = 1;
  return { command: NIIMBOT_REQUEST.SetPageSize, data };
}

export function buildPageEndPacket(): NiimbotPacket {
  return { command: NIIMBOT_REQUEST.PageEnd, data: Uint8Array.of(1) };
}

export function buildPrintStatusQueryPacket(): NiimbotPacket {
  return { command: NIIMBOT_REQUEST.PrintStatus, data: Uint8Array.of(1) };
}

export function buildPrintEndPacket(): NiimbotPacket {
  return { command: NIIMBOT_REQUEST.PrintEnd, data: Uint8Array.of(1) };
}

/**
 * Secuencia completa de comandos (sin contar handshake de conexión ni el
 * poll de PrintStatus/PrintEnd finales, que son inherentemente interactivos
 * -- request/espera respuesta/reintento -- y viven en niimbot-b1-adapter.ts,
 * no aquí). Función pura: mismo raster + misma densidad -> misma secuencia
 * de paquetes, siempre -- esto es lo que hace testeable el protocolo sin
 * hardware ni mocks de BLE.
 */
export function buildPrintJobPackets(
  raster: { widthPx: number; heightPx: number; bitmap: { rows: Uint8Array[] } },
  options?: { density?: number },
): NiimbotPacket[] {
  const packets: NiimbotPacket[] = [
    buildSetDensityPacket(options?.density),
    buildSetLabelTypePacket(),
    buildPrintStartPacket(1),
    buildPageStartPacket(),
    buildSetPageSizePacket(raster.widthPx, raster.heightPx),
  ];
  raster.bitmap.rows.forEach((row, index) => packets.push(encodeRowPacket(index, row)));
  packets.push(buildPageEndPacket());
  return packets;
}
