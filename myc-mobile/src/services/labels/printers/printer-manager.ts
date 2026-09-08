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
  private currentScanSession: { nativeStarted: boolean; cancelled: boolean } | null = null;

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
   * accionable, sin dejar nunca un "cargando" infinito en la UI.
   *
   * AUDITORÍA 2026-09-08 (ronda 2): ensureBleReady() puede tardar tiempo
   * real -- el diálogo nativo de permiso de Android no resuelve al
   * instante. Si la pantalla se desmonta (stopScan() vía cleanup, ver
   * label-printer-setup.tsx) MIENTRAS esa espera sigue pendiente, antes no
   * había nada que cancelar: el scan nativo arrancaba de todas formas en
   * cuanto el permiso se resolvía, aunque quien lo pidió ya se hubiera ido.
   * currentScanSession trackea esto -- stopScan() marca `cancelled` si el
   * scan nativo todavía no arrancó, y scan() lo revisa justo antes de
   * tocar BLE para rendirse sin arrancar nada. */
  async scan(onDeviceFound: (classification: DeviceClassification) => void, timeoutMs = DEFAULT_SCAN_TIMEOUT_MS): Promise<void> {
    const session = { nativeStarted: false, cancelled: false };
    this.currentScanSession = session;
    try {
      await this.ensureBleReady();
      if (session.cancelled) return;
      const seen = new Set<string>();
      session.nativeStarted = true;
      await this.ble.startScan((device) => {
        if (seen.has(device.id)) return;
        seen.add(device.id);
        onDeviceFound(classifyDevice(device));
      }, timeoutMs);
    } finally {
      if (this.currentScanSession === session) this.currentScanSession = null;
    }
  }

  /** AUDITORÍA 2026-09-08 (ronda 2): antes llamaba this.ble.stopScan() sin
   * condición. Si scan() seguía esperando permiso/Bluetooth (ningún scan
   * nativo había arrancado todavía), no había nada real que detener --
   * cuando ese readiness finalmente resolvía, scan() arrancaba el escaneo
   * de todas formas, ignorando la cancelación ya pedida. Ahora, mientras
   * el scan nativo no haya arrancado, sólo se marca la sesión activa como
   * cancelada (ver scan()); una vez que sí arrancó, se delega a
   * this.ble.stopScan() como siempre. Sin sesión activa (nunca se llamó a
   * scan(), o ya terminó), sigue siendo un no-op seguro. */
  async stopScan(): Promise<void> {
    const session = this.currentScanSession;
    if (session && !session.nativeStarted) {
      session.cancelled = true;
      return;
    }
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
   * -- llamadas futuras de connectPreferred() lo reconectan sin escanear.
   *
   * AUDITORÍA 2026-09-08 (ronda 2): antes llamaba adapter.connect(device)
   * directo, sin el mismo chequeo de permiso/Bluetooth que ya exige scan()
   * -- si Android revocó el permiso entre sesiones, esto fallaba con un
   * error nativo genérico en vez de BluetoothPermissionDeniedError/
   * BluetoothDisabledError. También podía conectar una impresora nueva
   * mientras otra seguía físicamente conectada (deviceId pasaba a
   * representar la nueva sin que la anterior se soltara nunca). Ahora
   * ambos casos están cubiertos: ensureBleReady() antes de tocar BLE, y
   * disconnectActiveIfAny() -- después de confirmar que el intento puede
   * proceder -- para nunca dejar dos impresoras físicamente vivas ni
   * soltar la actual si el intento de conectar la nueva va a fallar. */
  async connectAndRemember(adapterId: PrinterAdapterId, device: PrinterDevice): Promise<void> {
    const adapter = this.requireAdapter(adapterId);
    this.assertNotPrinting();
    await this.ensureBleReady();
    await this.disconnectActiveIfAny();
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
   * eso es una condición normal, no un error de conexión. Si SÍ hay una
   * preferida guardada, exige el mismo readiness BLE que connectAndRemember()
   * / scan() (ver AUDITORÍA 2026-09-08, ronda 2) -- sin impresora guardada,
   * nunca llega a pedir permiso ni tocar Bluetooth. */
  async connectPreferred(): Promise<boolean> {
    const preferred = await this.store.read();
    if (!preferred) return false;
    const adapter = this.adapters.get(preferred.adapterId);
    if (!adapter) return false;
    this.assertNotPrinting();
    await this.ensureBleReady();
    await this.disconnectActiveIfAny();
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

  /** Único punto de chequeo de permiso/Bluetooth -- AUDITORÍA 2026-09-08
   * (ronda 2): antes sólo scan() lo hacía; connectAndRemember() y
   * connectPreferred() llamaban adapter.connect() directo. Cualquier
   * camino que vaya a tocar BLE nativo pasa por aquí. */
  private async ensureBleReady(): Promise<void> {
    const permitted = await this.ble.requestPermissions();
    if (!permitted) {
      throw new BluetoothPermissionDeniedError('MYC necesita permiso de Bluetooth para buscar la impresora.');
    }
    const bluetoothOn = await this.ble.isBluetoothOn();
    if (!bluetoothOn) {
      throw new BluetoothDisabledError('Enciende Bluetooth para buscar la impresora.');
    }
  }

  /** AUDITORÍA 2026-09-08 (ronda 2): evita que una impresión en curso se
   * corte a mitad de camino porque el usuario decidió cambiar de impresora
   * al mismo tiempo -- se comprueba ANTES de tocar BLE o desconectar nada,
   * así la impresora en uso nunca se suelta por un intento de cambio que
   * de todas formas hay que rechazar. */
  private assertNotPrinting(): void {
    if (this.printing) {
      throw new PrinterBusyError('Ya hay una impresión en curso; espera a que termine antes de cambiar de impresora.');
    }
  }

  /** AUDITORÍA 2026-09-08 (ronda 2): si ya hay una impresora físicamente
   * conectada, se suelta antes de establecer la nueva -- nunca deben
   * quedar dos conexiones físicas vivas a la vez con deviceId apuntando
   * sólo a la más reciente. Se llama recién después de ensureBleReady()
   * para no soltar la impresora activa si el intento de conectar la nueva
   * va a fallar de todas formas por permiso/Bluetooth. */
  private async disconnectActiveIfAny(): Promise<void> {
    if (this.activeAdapter?.isConnected()) {
      await this.disconnect();
    }
  }
}
