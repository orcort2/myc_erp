import type { RasterLabel } from '../label-types';
import type { BleTransport } from './ble-transport';
import { classifyDevice } from './printer-registry';
import type {
  DeviceClassification,
  LabelPrinterAdapter,
  PreferredPrinter,
  PrintOptions,
  PrinterAdapterId,
  PrinterDevice,
} from './types';

/**
 * Puerto de persistencia inyectado -- PrinterManager NUNCA importa
 * preferred-printer-storage.ts (expo-secure-store) directamente. Esa
 * importación arrastra 'react-native' incluso en un archivo que sólo se
 * ejecutaría en Node para pruebas (confirmado: tsx/esbuild no puede
 * transformar react-native/index.js fuera del bundler de Metro), así que
 * mantiene a PrinterManager 100% testeable con un store en memoria. La
 * composición de producción (ver label-print-service.ts) inyecta
 * preferred-printer-storage.ts real; los tests inyectan un fake.
 */
export type PreferredPrinterStore = {
  read(): Promise<PreferredPrinter | null>;
  write(printer: PreferredPrinter): Promise<void>;
  clear(): Promise<void>;
};

/**
 * Orquestador central: dueño único del BleTransport (el radio BLE es un
 * recurso compartido -- ver types.ts) y de qué adaptador está activo.
 * La UI y LabelPrintService programan contra esta clase, nunca contra un
 * adaptador concreto ni contra BleTransport directamente.
 */

const DEFAULT_SCAN_TIMEOUT_MS = 8_000;

export type AdapterFactory = (ble: BleTransport) => LabelPrinterAdapter;

export class PrinterNotReadyError extends Error {}
export class PrinterBusyError extends Error {}
export class UnknownPrinterAdapterError extends Error {}

export class PrinterManager {
  private readonly ble: BleTransport;
  private readonly adapters: Map<PrinterAdapterId, LabelPrinterAdapter>;
  private activeAdapter: LabelPrinterAdapter | null = null;
  private activeDevice: PrinterDevice | null = null;
  private printing = false;

  constructor(
    ble: BleTransport,
    adapterFactories: Partial<Record<PrinterAdapterId, AdapterFactory>>,
    private readonly store: PreferredPrinterStore,
  ) {
    this.ble = ble;
    this.adapters = new Map(
      Object.entries(adapterFactories).map(([id, factory]) => [id as PrinterAdapterId, factory!(ble)]),
    );
  }

  /** Escanea dispositivos BLE cercanos, clasificándolos vía PrinterRegistry
   * a medida que aparecen. La UI decide qué hacer con `unknown` (nunca
   * ofrecerlo como impresora) y con `protocol_pending` (ofrecer sólo
   * diagnóstico, nunca "Conectar" -- ver mission section 15/16). */
  async scan(onDeviceFound: (classification: DeviceClassification) => void, timeoutMs = DEFAULT_SCAN_TIMEOUT_MS): Promise<void> {
    const seen = new Set<string>();
    await this.ble.startScan((device) => {
      if (seen.has(device.id)) return;
      seen.add(device.id);
      onDeviceFound(classifyDevice(device));
    }, timeoutMs);
  }

  async stopScan(): Promise<void> {
    await this.ble.stopScan();
  }

  isReady(): boolean {
    return this.activeAdapter?.isConnected() ?? false;
  }

  activePrinterDisplayName(): string | null {
    return this.activeAdapter?.displayName ?? null;
  }

  /** Capacidades (dpi, ancho imprimible) del adaptador activo -- el
   * renderer las necesita para producir un RasterLabel al tamaño correcto
   * (ver label-print-service.ts). Ninguna suposición fija de 203 dpi vive
   * aquí: se pregunta a quien esté realmente conectado. */
  activeCapabilities(): LabelPrinterAdapter['capabilities'] | null {
    return this.activeAdapter?.capabilities ?? null;
  }

  /** Conecta un dispositivo ya elegido en la UI y lo guarda como preferido
   * -- llamadas futuras de connectPreferred() lo reconectan sin escanear. */
  async connectAndRemember(adapterId: PrinterAdapterId, device: PrinterDevice): Promise<void> {
    const adapter = this.requireAdapter(adapterId);
    await adapter.connect(device);
    this.activeAdapter = adapter;
    this.activeDevice = device;
    const preferred: PreferredPrinter = {
      adapterId,
      deviceId: device.id,
      deviceName: device.name,
      savedAt: new Date().toISOString(),
    };
    await this.store.write(preferred);
  }

  /** Reconecta la impresora preferida guardada, si hay una y su adaptador
   * sigue disponible. Devuelve false (nunca lanza) si no hay preferida --
   * eso es una condición normal, no un error de conexión. */
  async connectPreferred(): Promise<boolean> {
    const preferred = await this.store.read();
    if (!preferred) return false;
    const adapter = this.adapters.get(preferred.adapterId);
    if (!adapter) return false;
    const device: PrinterDevice = { id: preferred.deviceId, name: preferred.deviceName };
    await adapter.connect(device);
    this.activeAdapter = adapter;
    this.activeDevice = device;
    return true;
  }

  async disconnect(): Promise<void> {
    await this.activeAdapter?.disconnect();
    this.activeAdapter = null;
    this.activeDevice = null;
  }

  /** Desconecta y borra la impresora preferida guardada -- "olvidar
   * impresora" en la UI. */
  async forget(): Promise<void> {
    await this.disconnect();
    await this.store.clear();
  }

  async print(label: RasterLabel, options?: PrintOptions): Promise<void> {
    if (!this.activeAdapter || !this.activeAdapter.isConnected()) {
      throw new PrinterNotReadyError('No hay una impresora conectada.');
    }
    if (this.printing) {
      throw new PrinterBusyError('Ya hay una impresión en curso; espera a que termine.');
    }
    this.printing = true;
    try {
      await this.activeAdapter.print(label, options);
    } finally {
      this.printing = false;
    }
  }

  private requireAdapter(adapterId: PrinterAdapterId): LabelPrinterAdapter {
    const adapter = this.adapters.get(adapterId);
    if (!adapter) {
      throw new UnknownPrinterAdapterError(`No hay adaptador registrado para "${adapterId}".`);
    }
    return adapter;
  }
}
