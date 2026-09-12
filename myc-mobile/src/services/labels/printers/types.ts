import type { RasterLabel } from '../label-types';

/**
 * Contrato genérico de impresora -- ver docs/architecture/lab-label-printing.md.
 * Ningún campo aquí es específico de NIIMBOT: un adaptador nuevo (NELKO,
 * Zebra, Brother, el que siga) implementa exactamente esta forma. Deja de
 * ser MYC/LAB business logic desde este punto hacia abajo (PrinterManager,
 * PrinterRegistry, adapters): sólo reciben un RasterLabel ya compuesto.
 */

export type PrinterTransport = 'ble';

/** Un dispositivo BLE descubierto, antes de saber si es una impresora
 * soportada, reconocida-pero-no-soportada, o ajeno por completo (ver
 * PrinterRegistry.classify). */
export type DiscoveredDevice = {
  id: string;
  name: string | null;
  rssi?: number;
  /** UUIDs de servicio anunciados, si la plataforma los expone durante el
   * scan (algunos SO sólo los entregan tras conectar). */
  advertisedServiceUUIDs?: string[];
  manufacturerData?: string | null; // hex, si el SO lo expone
};

/** El mismo tipo de PrinterAdapter.discover() -- ya identificado como un
 * dispositivo de una familia conocida (o al menos candidato). */
export type PrinterDevice = DiscoveredDevice;

export type PrintOptions = {
  copies?: number;
  /** 1-5 según el rango típico de densidad térmica del hardware actual;
   * cada adaptador valida/ajusta a su propio rango real. */
  density?: number;
};

export type PrinterCapabilities = {
  dpi: number;
  /** Ancho imprimible del cabezal en píxeles a `dpi` -- una capacidad de la
   * IMPRESORA, nunca del LabelProfile (ver label-profile.ts). */
  printableWidthPx: number;
};

export type PrinterAdapterId = 'niimbot-b1' | 'nelko-pm220';

/**
 * Contrato que implementa cada adaptador de impresora concreto. El
 * PrinterManager y la UI programan exclusivamente contra esta interfaz --
 * nunca importan un protocolo o SDK de fabricante directamente.
 *
 * El descubrimiento BLE (scan) NO vive aquí: es un recurso de radio
 * compartido y PrinterManager lo posee una sola vez sobre un único
 * BleTransport, clasificando cada dispositivo encontrado vía
 * PrinterRegistry.classifyDevice (ver printer-manager.ts). El adaptador
 * concreto sólo entra en juego una vez que la UI ya eligió un dispositivo
 * reconocido: de ahí en adelante, connect/print/disconnect.
 */
export interface LabelPrinterAdapter {
  readonly id: PrinterAdapterId;
  readonly displayName: string;
  readonly transport: PrinterTransport;
  readonly capabilities: PrinterCapabilities;

  connect(device: PrinterDevice): Promise<void>;
  disconnect(): Promise<void>;
  isConnected(): boolean;
  print(label: RasterLabel, options?: PrintOptions): Promise<void>;
  /** SOLO QA/desarrollo -- opcional a propósito, ningún adaptador de
   * producción está obligado a implementarlo. Envía una secuencia de
   * paquetes ya construida externamente tal cual (ver
   * niimbot-b1/qa-row-header-variant.ts para el único caso de uso real hoy:
   * comparar variantes documentadas del header de PrintBitmapRow contra
   * hardware físico). Nunca lo usa printLabel() ni print(). */
  printPacketSequenceForQa?(packets: { command: number; data: Uint8Array }[]): Promise<void>;
}

/** Estado de soporte declarado por el registro para un adaptador/familia --
 * ver printer-registry.ts. protocol_pending es el estado explícito de NELKO
 * PM220 hasta que su protocolo BLE se valide contra hardware físico; nunca
 * se reporta como soportado antes de eso. */
export type PrinterSupportStatus = 'supported' | 'protocol_pending' | 'unsupported';

export type PrinterFamilyDescriptor = {
  adapterId: PrinterAdapterId;
  displayName: string;
  modelHint: string;
  supportStatus: PrinterSupportStatus;
};

/** Clasificación de un dispositivo BLE descubierto -- ver
 * PrinterRegistry.classify. `unknown` cubre cualquier periférico BLE que no
 * sea una de las familias reconocidas (audífonos, relojes, etc.): nunca se
 * ofrece como impresora en la UI. */
export type DeviceClassification =
  | { kind: 'recognized'; family: PrinterFamilyDescriptor; device: DiscoveredDevice }
  | { kind: 'unknown'; device: DiscoveredDevice };

/** Impresora preferida persistida por dispositivo -- ver
 * preferred-printer-storage.ts. Guarda lo mínimo necesario para reconectar
 * sin volver a escanear: familia, identificador BLE y nombre para mostrar. */
export type PreferredPrinter = {
  adapterId: PrinterAdapterId;
  deviceId: string;
  deviceName: string | null;
  savedAt: string;
};
