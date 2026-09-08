import type { RasterLabel } from '../../../label-types';
import type { BleTransport, Unsubscribe } from '../../ble-transport';
import type { LabelPrinterAdapter, PrintOptions, PrinterCapabilities, PrinterDevice } from '../../types';
import {
  NIIMBOT_BLE_CHARACTERISTIC_UUID,
  NIIMBOT_BLE_SERVICE_UUID,
  NIIMBOT_REQUEST,
  NiimbotFrameAssembler,
  buildConnectPacket,
  buildPrintEndPacket,
  buildPrintJobPackets,
  buildPrintStatusQueryPacket,
  buildPrinterStatusDataPacket,
  encodeNiimbotPacket,
  type DecodedNiimbotPacket,
} from './protocol';

/**
 * Adaptador NIIMBOT B1 -- única impresora con soporte real hoy (ver
 * printer-registry.ts). Sólo depende de la interfaz BleTransport (nunca de
 * react-native-ble-manager directamente): esto es lo que permite probar
 * toda la orquestación (handshake, secuencia de impresión, timeouts,
 * desconexión a mitad de impresión, doble impresión) con un transporte de
 * prueba en niimbot-b1-adapter.test.ts, sin BLE real ni mocks nativos.
 *
 * 384px de ancho imprimible y 203 dpi son los valores públicos conocidos
 * del cabezal B1 (ver mission section 12) -- no se negocian en tiempo real
 * en v1 (ver protocol.ts, "Divergencia NO resuelta" y AUDITORÍA DE
 * FUENTES): la identificación post-conexión (PrinterStatusData) se envía
 * por trazabilidad/diagnóstico, pero un timeout en esa respuesta no bloquea
 * la conexión ni la impresión.
 */

const DEFAULT_TIMEOUTS = {
  connectTimeoutMs: 8_000,
  identifyTimeoutMs: 3_000,
  commandTimeoutMs: 5_000,
  printStatusPollIntervalMs: 300,
  printStatusTimeoutMs: 25_000,
  printEndTimeoutMs: 5_000,
};

export type NiimbotB1AdapterTimeouts = typeof DEFAULT_TIMEOUTS;

export class NiimbotTimeoutError extends Error {}
export class NiimbotDisconnectedError extends Error {}
export class NiimbotPrintInProgressError extends Error {}
export class NiimbotNotConnectedError extends Error {}

type PendingWaiter = { resolve(packet: DecodedNiimbotPacket): void; reject(error: Error): void };

export class NiimbotB1Adapter implements LabelPrinterAdapter {
  readonly id = 'niimbot-b1' as const;
  readonly displayName = 'NIIMBOT B1';
  readonly transport = 'ble' as const;
  readonly capabilities: PrinterCapabilities = { dpi: 203, printableWidthPx: 384 };

  private readonly ble: BleTransport;
  private readonly timeouts: NiimbotB1AdapterTimeouts;
  private deviceId: string | null = null;
  private connected = false;
  private printing = false;
  private frameAssembler = new NiimbotFrameAssembler();
  private waiters = new Map<number, PendingWaiter[]>();
  private unsubscribeNotifications: Unsubscribe | null = null;
  private unsubscribeDisconnect: Unsubscribe | null = null;

  /** timeouts es un override deliberado -- para pruebas de Node (ver
   * niimbot-b1-adapter.test.ts), que no deberían esperar los ~8-25s reales
   * de producción para ejercer un timeout. Producción siempre usa
   * DEFAULT_TIMEOUTS. */
  constructor(ble: BleTransport, timeouts: Partial<NiimbotB1AdapterTimeouts> = {}) {
    this.ble = ble;
    this.timeouts = { ...DEFAULT_TIMEOUTS, ...timeouts };
  }

  isConnected(): boolean {
    return this.connected;
  }

  async connect(device: PrinterDevice): Promise<void> {
    await this.ble.connect(device.id);
    await this.ble.discoverServices(device.id);
    this.deviceId = device.id;
    this.frameAssembler.reset();
    this.unsubscribeNotifications = await this.ble.subscribeNotifications(
      device.id,
      NIIMBOT_BLE_SERVICE_UUID,
      NIIMBOT_BLE_CHARACTERISTIC_UUID,
      (chunk) => this.handleIncoming(chunk),
    );
    this.unsubscribeDisconnect = this.ble.onDisconnected(device.id, () => this.handleUnexpectedDisconnect());
    this.connected = true;

    try {
      await this.sendAndWait(buildConnectPacket(), NIIMBOT_REQUEST.ConnectResult, this.timeouts.connectTimeoutMs);
    } catch (error) {
      await this.teardownConnection();
      throw error;
    }

    // Identificación best-effort: informativa (ver docstring de la clase),
    // nunca bloquea la conexión si la impresora no responde a tiempo.
    try {
      await this.sendAndWait(buildPrinterStatusDataPacket(), NIIMBOT_REQUEST.PrinterStatusDataResult, this.timeouts.identifyTimeoutMs);
    } catch {
      // Ignorado deliberadamente -- ver docstring.
    }
  }

  async disconnect(): Promise<void> {
    await this.teardownConnection();
    if (this.deviceId) await this.ble.disconnect(this.deviceId).catch(() => undefined);
    this.deviceId = null;
  }

  async print(label: RasterLabel, options?: PrintOptions): Promise<void> {
    if (!this.connected || !this.deviceId) {
      throw new NiimbotNotConnectedError('No hay conexión activa con la impresora NIIMBOT B1.');
    }
    if (this.printing) {
      throw new NiimbotPrintInProgressError('Ya hay una impresión en curso; espera a que termine.');
    }
    this.printing = true;
    try {
      const copies = Math.max(1, options?.copies ?? 1);
      const packets = buildPrintJobPackets(label, { density: options?.density });
      for (let copy = 0; copy < copies; copy += 1) {
        for (const packet of packets) {
          await this.write(packet);
        }
        await this.waitForPrintComplete();
        await this.sendAndWait(buildPrintEndPacket(), NIIMBOT_REQUEST.PrintEndResult, this.timeouts.printEndTimeoutMs);
      }
    } finally {
      this.printing = false;
    }
  }

  private async waitForPrintComplete(): Promise<void> {
    const deadline = Date.now() + this.timeouts.printStatusTimeoutMs;
    for (;;) {
      if (!this.connected) throw new NiimbotDisconnectedError('La impresora se desconectó durante la impresión.');
      try {
        // Cualquier PrintStatusResult válido se toma como señal de página
        // lista -- ver docstring de la clase: el layout exacto del byte de
        // conteo de páginas en la respuesta no está confirmado contra
        // hardware físico, así que no se condiciona a un valor puntual.
        await this.sendAndWait(buildPrintStatusQueryPacket(), NIIMBOT_REQUEST.PrintStatusResult, this.timeouts.commandTimeoutMs);
        return;
      } catch (error) {
        if (error instanceof NiimbotDisconnectedError) throw error;
        if (Date.now() >= deadline) {
          throw new NiimbotTimeoutError('La impresora no confirmó el estado de impresión a tiempo.');
        }
        await delay(this.timeouts.printStatusPollIntervalMs);
      }
    }
  }

  private async write(packet: { command: number; data: Uint8Array }): Promise<void> {
    if (!this.deviceId) throw new NiimbotNotConnectedError('No hay conexión activa con la impresora NIIMBOT B1.');
    await this.ble.writeWithoutResponse(
      this.deviceId,
      NIIMBOT_BLE_SERVICE_UUID,
      NIIMBOT_BLE_CHARACTERISTIC_UUID,
      encodeNiimbotPacket(packet),
    );
  }

  private async sendAndWait(
    packet: { command: number; data: Uint8Array },
    expectedResponse: number,
    timeoutMs: number,
  ): Promise<DecodedNiimbotPacket> {
    const responsePromise = this.waitForResponse(expectedResponse, timeoutMs);
    await this.write(packet);
    return responsePromise;
  }

  private waitForResponse(command: number, timeoutMs: number): Promise<DecodedNiimbotPacket> {
    return new Promise((resolve, reject) => {
      const waiter: PendingWaiter = {
        resolve: (packet) => {
          clearTimeout(timer);
          resolve(packet);
        },
        reject: (error) => {
          clearTimeout(timer);
          reject(error);
        },
      };
      const timer = setTimeout(() => {
        this.removeWaiter(command, waiter);
        reject(new NiimbotTimeoutError(`La impresora no respondió a tiempo (comando 0x${command.toString(16)}).`));
      }, timeoutMs);
      const list = this.waiters.get(command) ?? [];
      list.push(waiter);
      this.waiters.set(command, list);
    });
  }

  private removeWaiter(command: number, waiter: PendingWaiter): void {
    const list = this.waiters.get(command);
    if (!list) return;
    const next = list.filter((item) => item !== waiter);
    if (next.length) this.waiters.set(command, next);
    else this.waiters.delete(command);
  }

  private handleIncoming(chunk: Uint8Array): void {
    for (const packet of this.frameAssembler.push(chunk)) {
      const list = this.waiters.get(packet.command);
      if (!list?.length) continue;
      this.waiters.delete(packet.command);
      list.forEach((waiter) => waiter.resolve(packet));
    }
  }

  private handleUnexpectedDisconnect(): void {
    this.connected = false;
    const error = new NiimbotDisconnectedError('La impresora NIIMBOT B1 se desconectó inesperadamente.');
    for (const [command, list] of this.waiters) {
      list.forEach((waiter) => waiter.reject(error));
      this.waiters.delete(command);
    }
  }

  private async teardownConnection(): Promise<void> {
    this.connected = false;
    this.unsubscribeNotifications?.();
    this.unsubscribeNotifications = null;
    this.unsubscribeDisconnect?.();
    this.unsubscribeDisconnect = null;
    this.frameAssembler.reset();
    for (const [command, list] of this.waiters) {
      list.forEach((waiter) => waiter.reject(new NiimbotDisconnectedError('Conexión NIIMBOT B1 cerrada.')));
      this.waiters.delete(command);
    }
  }
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
