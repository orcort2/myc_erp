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

/** AUDITORÍA 2026-09-08 (seguimiento): BleTransport ya implementaba
 * requestPermissions()/isBluetoothOn(), pero scan() nunca los llamaba --
 * el permiso de runtime de Android podía nunca llegar a pedirse antes del
 * primer escaneo. Estos dos errores tipados dejan explícito por qué un
 * scan no arrancó, en vez de que la UI reciba un fallo genérico del SDK
 * nativo (o, peor, un scan que nunca encuentra nada porque el permiso
 * jamás se concedió). */
export class BluetoothPermissionDeniedError extends Error {}
export class BluetoothDisabledError extends Error {}

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
   * diagnóstico, nunca "Conectar" -- ver mission section 15/16).
   *
   * AUDITORÍA 2026-09-08 (seguimiento): antes de arrancar el descubrimiento
   * nativo, PrinterManager es quien exige permisos y estado de Bluetooth --
   * nunca cada pantalla por su cuenta (evita permission-checks duplicados
   * en React, y garantiza que ninguna pantalla pueda saltarse el chequeo).
   * Orden exacto: 1) pedir permisos, 2) si se niegan, no arrancar el scan
   * nativo; 3) verificar Bluetooth encendido, 4) si está apagado, tampoco
   * arrancar; 5) recién entonces this.ble.startScan(...). Ninguno de los
   * dos estados se ignora en silencio: cada uno lanza un error tipado y
   * accionable, sin dejar nunca un "cargando" infinito en la UI. */
  async scan(onDeviceFound: (classification: DeviceClassification) => void, timeoutMs = DEFAULT_SCAN_TIMEOUT_MS): Promise<void> {
    const permitted = await this.ble.requestPermissions();
    if (!permitted) {
      throw new BluetoothPermissionDeniedError('MYC necesita permiso de Bluetooth para buscar la impresora.');
    }
    const bluetoothOn = await this.ble.isBluetoothOn();
    if (!bluetoothOn) {
      throw new BluetoothDisabledError('Enciende Bluetooth para buscar la impresora.');
    }
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
