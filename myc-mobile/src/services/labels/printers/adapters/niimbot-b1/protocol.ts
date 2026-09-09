/**
 * Protocolo BLE NIIMBOT B1 / familia V3.
 *
 * AUDITORÍA ORIGINAL:
 * - NIIMBOT Community Wiki / niimblue
 * - AndBondStyle/niimprint
 * - MultiMote/niimbluelib
 *
 * AUDITORÍA SDK OFICIAL 2026-09-09:
 *
 * Se inspeccionó el SDK oficial incluido en NIIMBOT.app para macOS:
 *
 *   libjcPrinterSdk.dylib
 *
 * La implementación TypeScript NO depende de macOS ni del dylib.
 * El SDK oficial se usa únicamente como fuente para reconstruir el
 * protocolo BLE que habla directamente con la impresora.
 *
 * Funciones V3 inspeccionadas:
 *
 *   cPrinterV3::packageCommand()
 *   cPrinterV3::jcSetPrintAllTime()
 *   cPrinterV3::jcSetPagePrint()
 *   cPrinterV3::jcSetPageInfo(...)
 *   cPrinterV3::jcSetPageTerminal()
 *   cPrinterV3::jcSetPrintTerminal()
 *   cPrinterV3::getPrinterPageStatus(PageStatus&)
 *   cPrinterV3::commitJob()
 *   cPrinterV3::sendPrintData(...)
 *   processOneColorImageData()
 *   packageOneColorData()
 *
 * CONTRATO CONFIRMADO
 * ===================
 *
 * Framing:
 *
 *   55 55 | CMD | LEN | DATA | XOR | AA AA
 *
 * XOR:
 *
 *   CMD XOR LEN XOR cada byte de DATA
 *
 * Control de trabajo/página V3:
 *
 *   PrintStart:
 *     CMD  0x01
 *     DATA [PAGE_COUNT_HI, PAGE_COUNT_LO]
 *     RESP 0x02
 *
 *   PageStart:
 *     CMD  0x03
 *     DATA [0x00]
 *     RESP 0x04
 *
 *   PageInfo / SetPageSize:
 *     CMD  0x13
 *     DATA [
 *       HEIGHT_HI, HEIGHT_LO,
 *       WIDTH_HI,  WIDTH_LO,
 *       COUNT_HI,  COUNT_LO
 *     ]
 *     RESP 0x14
 *
 *   PageTerminal:
 *     CMD  0xE3
 *     DATA [0x00]
 *     RESP 0xE4
 *
 *   PrintStatus:
 *     CMD  0xA3
 *     DATA [0x00]
 *     RESP 0xB3
 *
 *   PrintTerminal:
 *     CMD  0xF3
 *     DATA [0x00]
 *     RESP 0xF4
 *
 * En las rutas oficiales inspeccionadas, las respuestas de control
 * validan además DATA[0] == 0x01 como aceptación.
 *
 * Esa validación pertenece al adapter/request-response, no a este
 * archivo de construcción de paquetes.
 *
 * PrintStatusResult (0xB3) NO es un ACK simple:
 *
 *   LEN debe ser >= 8
 *
 * El SDK oficial parsea los primeros 8 bytes así:
 *
 *   DATA[0..1] -> uint16 BE
 *   DATA[2]    -> uint8
 *   DATA[3]    -> uint8
 *   DATA[4..5] -> uint16 BE
 *   DATA[6]    -> uint8
 *   DATA[7]    -> uint8
 *
 * Esos campos participan en la detección de progreso dentro de commitJob().
 * Por ahora se exponen con nombres neutrales para no inventar semántica
 * que aún no haya sido confirmada.
 *
 * RASTER 0x85
 * ===========
 *
 * El payload monocromático normal comienza con:
 *
 *   ROW_HI
 *   ROW_LO
 *   WHITE_COUNT_0_191
 *   WHITE_COUNT_192_383
 *   WHITE_COUNT_384_PLUS
 *   REPEAT
 *   RASTER...
 *
 * ROW es big-endian.
 *
 * Los contadores se calculan sobre regiones horizontales de 192 px:
 *
 *   0..191
 *   192..383
 *   384..575
 *
 * Representación binaria MYC:
 *
 *   bit 1 = tinta / negro
 *   bit 0 = blanco
 *
 * Por tanto los tres contadores cuentan bits blancos (0).
 *
 * REPEAT:
 *
 *   1 = una fila
 *   2 = dos filas idénticas
 *   ...
 *
 * Durante el bring-up físico se mantiene una fila por paquete con
 * REPEAT=1. La compresión de filas repetidas queda fuera de alcance
 * hasta validar primero el B1 físicamente.
 *
 * El SDK también dispone de 0x84/0x8A para otras representaciones u
 * optimizaciones. Por ahora MYC mantiene 0x85 para todas las filas.
 */

export const NIIMBOT_BLE_SERVICE_UUID =
  'e7810a71-73ae-499d-8c15-faa9aef0c3f2';

export const NIIMBOT_BLE_CHARACTERISTIC_UUID =
  'bef8d6c9-9c21-4c9e-b632-bd58c1009f9f';

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

export type NiimbotRequestCode =
  (typeof NIIMBOT_REQUEST)[keyof typeof NIIMBOT_REQUEST];

export type NiimbotPacket = {
  command: number;
  data: Uint8Array;
};

export type DecodedNiimbotPacket = {
  command: number;
  data: Uint8Array;
};

export type NiimbotPageStatus = {
  field0: number;
  field1: number;
  field2: number;
  field3: number;
  field4: number;
  field5: number;
  extraLength: number;
  extraData: Uint8Array;
};

const HEADER_BYTE = 0x55;
const FOOTER_BYTE = 0xaa;
const MAX_DATA_LENGTH = 255;

const UINT16_MAX = 0xffff;

const MIN_PAGE_STATUS_DATA_LENGTH = 8;

/**
 * El SDK V3 divide horizontalmente la imagen en regiones de 192 píxeles
 * para los tres contadores del header 0x85.
 */
const ROW_COUNTER_SEGMENT_WIDTH = 192;
const ROW_COUNTER_SEGMENTS = 3;

const MAX_ROW_COUNTER_WIDTH =
  ROW_COUNTER_SEGMENT_WIDTH * ROW_COUNTER_SEGMENTS;

function assertUint16(
  value: number,
  label: string,
): void {
  if (
    !Number.isInteger(value) ||
    value < 0 ||
    value > UINT16_MAX
  ) {
    throw new RangeError(
      `${label} NIIMBOT inválido: ${value}`,
    );
  }
}

function checksumOf(
  command: number,
  data: Uint8Array,
): number {
  let checksum =
    (command ^ data.length) & 0xff;

  for (const byte of data) {
    checksum ^= byte;
  }

  return checksum & 0xff;
}

function readUint16Be(
  bytes: Uint8Array,
  offset: number,
): number {
  return (
    (bytes[offset] << 8) |
    bytes[offset + 1]
  );
}

/**
 * Frame V3:
 *
 *   [55,55,CMD,LEN,...DATA,XOR,AA,AA]
 *
 * Confirmado contra cPrinterV3::packageCommand().
 */
export function encodeNiimbotPacket(
  packet: NiimbotPacket,
): Uint8Array {
  const { command, data } = packet;

  if (data.length > MAX_DATA_LENGTH) {
    throw new RangeError(
      `Paquete NIIMBOT: datos exceden ${MAX_DATA_LENGTH} bytes (${data.length})`,
    );
  }

  const out =
    new Uint8Array(data.length + 7);

  out[0] = HEADER_BYTE;
  out[1] = HEADER_BYTE;
  out[2] = command & 0xff;
  out[3] = data.length & 0xff;

  out.set(data, 4);

  out[4 + data.length] =
    checksumOf(command, data);

  out[5 + data.length] =
    FOOTER_BYTE;

  out[6 + data.length] =
    FOOTER_BYTE;

  return out;
}

export class NiimbotFrameError extends Error {}

export class NiimbotPageStatusError extends Error {}

/**
 * Decodifica exactamente un frame NIIMBOT completo.
 */
export function decodeNiimbotPacket(
  bytes: Uint8Array,
): DecodedNiimbotPacket {
  if (bytes.length < 7) {
    throw new NiimbotFrameError(
      'Paquete NIIMBOT demasiado corto',
    );
  }

  if (
    bytes[0] !== HEADER_BYTE ||
    bytes[1] !== HEADER_BYTE
  ) {
    throw new NiimbotFrameError(
      'Encabezado NIIMBOT inválido',
    );
  }

  const command = bytes[2];
  const length = bytes[3];

  if (bytes.length !== length + 7) {
    throw new NiimbotFrameError(
      'Longitud de paquete NIIMBOT inconsistente',
    );
  }

  const data =
    bytes.slice(4, 4 + length);

  const checksumByte =
    bytes[4 + length];

  if (
    bytes[5 + length] !== FOOTER_BYTE ||
    bytes[6 + length] !== FOOTER_BYTE
  ) {
    throw new NiimbotFrameError(
      'Pie NIIMBOT inválido',
    );
  }

  if (
    checksumByte !==
    checksumOf(command, data)
  ) {
    throw new NiimbotFrameError(
      'Checksum NIIMBOT inválido',
    );
  }

  return {
    command,
    data,
  };
}

/**
 * Parser del payload B3 oficial de cPrinterV3::getPrinterPageStatus().
 *
 * El SDK requiere LEN >= 8.
 *
 * Layout fijo:
 *
 *   DATA[0..1] -> uint16 BE
 *   DATA[2]    -> uint8
 *   DATA[3]    -> uint8
 *   DATA[4..5] -> uint16 BE
 *   DATA[6]    -> uint8
 *   DATA[7]    -> uint8
 *
 * Si LEN > 8:
 *
 *   DATA[8]    -> longitud N
 *   DATA[9..]  -> N bytes adicionales
 */
export function parsePrintStatusResult(
  packet: DecodedNiimbotPacket,
): NiimbotPageStatus {
  if (
    packet.command !==
    NIIMBOT_REQUEST.PrintStatusResult
  ) {
    throw new NiimbotPageStatusError(
      `Se esperaba PrintStatusResult 0x${NIIMBOT_REQUEST.PrintStatusResult
        .toString(16)
        .padStart(2, '0')}, recibido 0x${packet.command
        .toString(16)
        .padStart(2, '0')}.`,
    );
  }

  if (
    packet.data.length <
    MIN_PAGE_STATUS_DATA_LENGTH
  ) {
    throw new NiimbotPageStatusError(
      `PrintStatusResult B3 demasiado corto: ${packet.data.length} bytes; se requieren al menos ${MIN_PAGE_STATUS_DATA_LENGTH}.`,
    );
  }

  const field0 =
    readUint16Be(
      packet.data,
      0,
    );

  const field1 =
    packet.data[2];

  const field2 =
    packet.data[3];

  const field3 =
    readUint16Be(
      packet.data,
      4,
    );

  const field4 =
    packet.data[6];

  const field5 =
    packet.data[7];

  let extraLength =
    0;

  let extraData =
    new Uint8Array();

  if (
    packet.data.length >
    MIN_PAGE_STATUS_DATA_LENGTH
  ) {
    extraLength =
      packet.data[8];

    const availableExtraBytes =
      Math.max(
        0,
        packet.data.length - 9,
      );

    if (
      extraLength >
      availableExtraBytes
    ) {
      throw new NiimbotPageStatusError(
        `PrintStatusResult B3 declara ${extraLength} bytes extra, pero sólo contiene ${availableExtraBytes}.`,
      );
    }

    extraData =
      packet.data.slice(
        9,
        9 + extraLength,
      );
  }

  return {
    field0,
    field1,
    field2,
    field3,
    field4,
    field5,
    extraLength,
    extraData,
  };
}

/**
 * Reensamblador con estado para notificaciones BLE fragmentadas.
 */
export class NiimbotFrameAssembler {
  private buffer: number[] = [];

  push(
    chunk: Uint8Array,
  ): DecodedNiimbotPacket[] {
    for (const byte of chunk) {
      this.buffer.push(byte);
    }

    const packets:
      DecodedNiimbotPacket[] = [];

    for (;;) {
      const headerIndex =
        this.indexOfHeader();

      if (headerIndex === -1) {
        this.buffer = [];
        break;
      }

      if (headerIndex > 0) {
        this.buffer.splice(
          0,
          headerIndex,
        );
      }

      if (this.buffer.length < 4) {
        break;
      }

      const length =
        this.buffer[3];

      const totalLength =
        length + 7;

      if (
        this.buffer.length <
        totalLength
      ) {
        break;
      }

      const frame =
        Uint8Array.from(
          this.buffer.slice(
            0,
            totalLength,
          ),
        );

      this.buffer.splice(
        0,
        totalLength,
      );

      try {
        packets.push(
          decodeNiimbotPacket(
            frame,
          ),
        );
      } catch {
        // Frame corrupto:
        // descartar y continuar buscando
        // el siguiente encabezado.
      }
    }

    return packets;
  }

  reset(): void {
    this.buffer = [];
  }

  private indexOfHeader(): number {
    for (
      let i = 0;
      i < this.buffer.length - 1;
      i += 1
    ) {
      if (
        this.buffer[i] ===
          HEADER_BYTE &&
        this.buffer[i + 1] ===
          HEADER_BYTE
      ) {
        return i;
      }
    }

    if (
      this.buffer.length >= 1 &&
      this.buffer[
        this.buffer.length - 1
      ] === HEADER_BYTE
    ) {
      return (
        this.buffer.length - 1
      );
    }

    return -1;
  }
}

export type NiimbotV3WhitePixelCounts = [
  number,
  number,
  number,
];

/**
 * Calcula los tres contadores que el SDK oficial V3 coloca en el header
 * de PrintBitmapRow (0x85).
 *
 * El bitmap recibido por MYC ya está empaquetado:
 *
 *   MSB first
 *   1 = negro/tinta
 *   0 = blanco
 *
 * Regiones:
 *
 *   count[0] -> 0..191
 *   count[1] -> 192..383
 *   count[2] -> 384..575
 */
export function countV3WhitePixels(
  packedRowBytes: Uint8Array,
  widthPx: number,
): NiimbotV3WhitePixelCounts {
  if (
    !Number.isInteger(widthPx) ||
    widthPx < 0
  ) {
    throw new RangeError(
      `Ancho NIIMBOT inválido: ${widthPx}`,
    );
  }

  const availableBits =
    packedRowBytes.length * 8;

  if (widthPx > availableBits) {
    throw new RangeError(
      `La fila NIIMBOT sólo contiene ${availableBits} bits, pero widthPx=${widthPx}`,
    );
  }

  if (
    widthPx >
    MAX_ROW_COUNTER_WIDTH
  ) {
    throw new RangeError(
      `El header V3 sólo representa hasta ${MAX_ROW_COUNTER_WIDTH} píxeles, recibido ${widthPx}`,
    );
  }

  const counts:
    NiimbotV3WhitePixelCounts =
      [0, 0, 0];

  for (
    let x = 0;
    x < widthPx;
    x += 1
  ) {
    const byteIndex =
      Math.floor(x / 8);

    const bitIndex =
      7 - (x % 8);

    const isBlack =
      ((
        packedRowBytes[
          byteIndex
        ] >> bitIndex
      ) & 0x01) === 1;

    if (isBlack) {
      continue;
    }

    const segment =
      Math.floor(
        x /
          ROW_COUNTER_SEGMENT_WIDTH,
      );

    counts[segment] += 1;
  }

  return counts;
}

/**
 * Empaqueta una fila del raster como PrintBitmapRow (0x85).
 *
 * Payload oficial V3:
 *
 *   [0] ROW_HI
 *   [1] ROW_LO
 *   [2] blancos 0..191
 *   [3] blancos 192..383
 *   [4] blancos 384..575
 *   [5] repeat
 *   [6...] raster MSB-first
 */
export function encodeRowPacket(
  rowIndex: number,
  packedRowBytes: Uint8Array,
  widthPx:
    number =
      packedRowBytes.length * 8,
): NiimbotPacket {
  assertUint16(
    rowIndex,
    'Índice de fila',
  );

  const [
    whiteCount0,
    whiteCount1,
    whiteCount2,
  ] = countV3WhitePixels(
    packedRowBytes,
    widthPx,
  );

  const header =
    new Uint8Array(6);

  header[0] =
    (rowIndex >> 8) & 0xff;

  header[1] =
    rowIndex & 0xff;

  header[2] =
    whiteCount0 & 0xff;

  header[3] =
    whiteCount1 & 0xff;

  header[4] =
    whiteCount2 & 0xff;

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
      NIIMBOT_REQUEST
        .PrintBitmapRow,
    data,
  };
}

export function buildConnectPacket(): NiimbotPacket {
  return {
    command:
      NIIMBOT_REQUEST.Connect,
    data: Uint8Array.of(1),
  };
}

export function buildPrinterStatusDataPacket(): NiimbotPacket {
  return {
    command:
      NIIMBOT_REQUEST
        .PrinterStatusData,
    data: Uint8Array.of(1),
  };
}

export function buildPrinterInfoPacket(
  subCode: number,
): NiimbotPacket {
  return {
    command:
      NIIMBOT_REQUEST.PrinterInfo,
    data: Uint8Array.of(
      subCode & 0xff,
    ),
  };
}

export function buildHeartbeatPacket(): NiimbotPacket {
  return {
    command:
      NIIMBOT_REQUEST.Heartbeat,
    data: Uint8Array.of(4),
  };
}

const MIN_DENSITY = 1;
const MAX_DENSITY = 5;
const DEFAULT_DENSITY = 3;

export function clampDensity(
  density: number | undefined,
): number {
  if (
    density === undefined ||
    Number.isNaN(density)
  ) {
    return DEFAULT_DENSITY;
  }

  return Math.min(
    MAX_DENSITY,
    Math.max(
      MIN_DENSITY,
      Math.round(density),
    ),
  );
}

export function buildSetDensityPacket(
  density: number | undefined,
): NiimbotPacket {
  return {
    command:
      NIIMBOT_REQUEST.SetDensity,

    data: Uint8Array.of(
      clampDensity(density),
    ),
  };
}

export function buildSetLabelTypePacket(): NiimbotPacket {
  return {
    command:
      NIIMBOT_REQUEST.SetLabelType,

    data: Uint8Array.of(1),
  };
}

export function buildPrintStartPacket(
  pageCount: number,
): NiimbotPacket {
  assertUint16(
    pageCount,
    'Cantidad de páginas',
  );

  if (pageCount === 0) {
    throw new RangeError(
      'Cantidad de páginas NIIMBOT debe ser mayor que cero',
    );
  }

  return {
    command:
      NIIMBOT_REQUEST.PrintStart,

    data: Uint8Array.of(
      (pageCount >> 8) & 0xff,
      pageCount & 0xff,
    ),
  };
}

export function buildPageStartPacket(): NiimbotPacket {
  return {
    command:
      NIIMBOT_REQUEST.PageStart,

    data: Uint8Array.of(0),
  };
}

export function buildSetPageSizePacket(
  widthPx: number,
  heightPx: number,
  printCount = 1,
): NiimbotPacket {
  assertUint16(
    widthPx,
    'Ancho de página',
  );

  assertUint16(
    heightPx,
    'Alto de página',
  );

  assertUint16(
    printCount,
    'Cantidad de copias',
  );

  if (
    widthPx === 0 ||
    heightPx === 0
  ) {
    throw new RangeError(
      'Las dimensiones NIIMBOT deben ser mayores que cero',
    );
  }

  if (printCount === 0) {
    throw new RangeError(
      'La cantidad de copias NIIMBOT debe ser mayor que cero',
    );
  }

  return {
    command:
      NIIMBOT_REQUEST.SetPageSize,

    data: Uint8Array.of(
      (heightPx >> 8) & 0xff,
      heightPx & 0xff,

      (widthPx >> 8) & 0xff,
      widthPx & 0xff,

      (printCount >> 8) & 0xff,
      printCount & 0xff,
    ),
  };
}

export function buildPageEndPacket(): NiimbotPacket {
  return {
    command:
      NIIMBOT_REQUEST.PageEnd,

    data: Uint8Array.of(0),
  };
}

/**
 * cPrinterV3::getPrinterPageStatus(PageStatus&)
 *
 * SDK oficial:
 *
 *   CMD  = 0xA3
 *   LEN  = 0x01
 *   DATA = 0x00
 *
 * Respuesta:
 *
 *   CMD  = 0xB3
 *   LEN >= 8
 */
export function buildPrintStatusQueryPacket(): NiimbotPacket {
  return {
    command:
      NIIMBOT_REQUEST.PrintStatus,

    data: Uint8Array.of(0),
  };
}

export function buildPrintEndPacket(): NiimbotPacket {
  return {
    command:
      NIIMBOT_REQUEST.PrintEnd,

    data: Uint8Array.of(0),
  };
}

export function buildPrintJobPackets(
  raster: {
    widthPx: number;
    heightPx: number;
    bitmap: {
      rows: Uint8Array[];
    };
  },
  options?: {
    density?: number;
  },
): NiimbotPacket[] {
  const packets:
    NiimbotPacket[] = [
      buildSetDensityPacket(
        options?.density,
      ),

      buildSetLabelTypePacket(),

      buildPrintStartPacket(1),

      buildPageStartPacket(),

      buildSetPageSizePacket(
        raster.widthPx,
        raster.heightPx,
        1,
      ),
    ];

  raster.bitmap.rows.forEach(
    (row, index) => {
      packets.push(
        encodeRowPacket(
          index,
          row,
          raster.widthPx,
        ),
      );
    },
  );

  packets.push(
    buildPageEndPacket(),
  );

  return packets;
}