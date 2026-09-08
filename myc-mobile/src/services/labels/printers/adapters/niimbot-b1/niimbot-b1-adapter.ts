import type { RasterLabel } from '../../../label-types';
import type { BleTransport, Unsubscribe } from '../../ble-transport';
import { cropRasterToPrintableWidth } from '../../raster-adapt';
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
 *
 * REVISADO 2026-09-08 (gate de QA física, sin cambios de comportamiento):
 * waitForPrintComplete() acepta CUALQUIER PrintStatusResult válido como
 * señal de "página lista", sin parsear ningún byte de conteo de páginas.
 * Se revisaron de nuevo las fuentes auditadas en protocol.ts buscando el
 * layout exacto de esa respuesta: niim.blue documenta un poll de
 * PrintStatus "hasta page >= 1" pero NUNCA especifica en qué byte/offset
 * del payload de 0xB3 vive ese "page"; niimprint (la única librería
 * confirmada contra hardware B1 real) ni siquiera hace ese poll -- su
 * end_print() reintenta PrintEnd(0xF3) directamente. Ninguna de las 3
 * fuentes da un layout de bytes verificable para PrintStatusResult. Parsear
 * un offset inventado sería fabricar certeza que no existe -- se mantiene
 * deliberadamente la interpretación conservadora (cualquier respuesta
 * válida al comando correcto == avanzar) y esto sigue siendo un punto de
 * control obligatorio de QA física, no algo que este archivo pueda resolver
 * por sí solo.
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

  /**
   * AUDITORÍA 2026-09-08 (seguimiento): antes, sólo el handshake
   * (Connect/ConnectResult) estaba protegido por un try/catch con
   * limpieza. Si ble.connect() tenía éxito pero discoverServices() o
   * subscribeNotifications() fallaban -- ANTES de llegar a ese try/catch --
   * la conexión BLE física quedaba viva mientras el adaptador nunca
   * terminaba de inicializarse, sin ningún camino de limpieza. Ahora TODA
   * la configuración posterior a un ble.connect() exitoso (discover,
   * suscripciones, handshake) vive dentro de un único try/catch: cualquier
   * fallo en cualquiera de esos pasos limpia todo lo que ya se haya creado
   * y desconecta físicamente -- invariante: después de un ble.connect()
   * exitoso, ningún camino de error de connect() puede dejar el periférico
   * físicamente conectado sin que el adaptador lo sepa.
   *
   * physicalConnectionEstablished distingue "ble.connect() nunca llegó a
   * tener éxito" (nada que desconectar) de "sí tuvo éxito, algo después
   * falló" (desconectar de verdad) -- teardownConnection ya tolera estado
   * parcial (suscripciones ausentes, deviceId nulo, etc.), así que es
   * seguro llamarla sin importar en qué paso exacto falló.
   */
  async connect(device: PrinterDevice): Promise<void> {
    let physicalConnectionEstablished = false;
    try {
      await this.ble.connect(device.id);
      physicalConnectionEstablished = true;
      // Se fija deviceId de inmediato (antes de discoverServices) -- si
      // algo falla más abajo, teardownConnection necesita saber a qué
      // dispositivo desconectar.
      this.deviceId = device.id;
      this.frameAssembler.reset();

      await this.ble.discoverServices(device.id);

      this.unsubscribeNotifications = await this.ble.subscribeNotifications(
        device.id,
        NIIMBOT_BLE_SERVICE_UUID,
        NIIMBOT_BLE_CHARACTERISTIC_UUID,
        (chunk) => this.handleIncoming(chunk),
      );
      this.unsubscribeDisconnect = this.ble.onDisconnected(device.id, () => this.handleUnexpectedDisconnect());
      this.connected = true;

      await this.sendAndWait(buildConnectPacket(), NIIMBOT_REQUEST.ConnectResult, this.timeouts.connectTimeoutMs);
    } catch (error) {
      await this.teardownConnection({ physicallyDisconnect: physicalConnectionEstablished });
      throw error;
    }

    // Identificación best-effort: informativa (ver docstring de la clase),
    // nunca bloquea la conexión si la impresora simplemente no responde a
    // tiempo. AUDITORÍA 2026-09-08 (ronda 2): antes este catch{} tragaba
    // CUALQUIER error, incluida una desconexión física real ocurrida justo
    // después del handshake (p.ej. NiimbotDisconnectedError vía
    // handleUnexpectedDisconnect, o un fallo real de escritura/transporte)
    // -- eso hacía que connect() resolviera "con éxito" mientras
    // this.connected ya había vuelto a false por dentro, y el caller
    // (PrinterManager) terminaba marcando la impresora como conectada sin
    // estarlo. Ahora sólo se ignora NiimbotTimeoutError; cualquier otro
    // error limpia (teardownConnection ya es idempotente: tolera un
    // teardown previo disparado por handleUnexpectedDisconnect) y se
    // propaga, para que connect() nunca reporte un éxito falso.
    try {
      await this.sendAndWait(buildPrinterStatusDataPacket(), NIIMBOT_REQUEST.PrinterStatusDataResult, this.timeouts.identifyTimeoutMs);
    } catch (error) {
      if (error instanceof NiimbotTimeoutError) return;
      await this.teardownConnection({ physicallyDisconnect: true });
      throw error;
    }
  }

  async disconnect(): Promise<void> {
    await this.teardownConnection({ physicallyDisconnect: true });
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
      // El raster llega a las dimensiones físicas completas del perfil
      // (p.ej. 400px de ancho para MYC_50X30 a 203dpi) -- el cabezal del B1
      // sólo puede imprimir capabilities.printableWidthPx (384) puntos por
      // fila. Recorta el margen físico ya vacío antes de construir los
      // paquetes: SetPageSize y cada PrintBitmapRow deben usar dimensiones
      // realmente válidas para el cabezal, ver raster-adapt.ts.
      const printable = cropRasterToPrintableWidth(label, this.capabilities.printableWidthPx);
      const packets = buildPrintJobPackets(printable, { density: options?.density });
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
    // Todo caller de write() (connect()/print()) ya validó this.deviceId
    // antes de empezar -- si desapareció aquí, fue una desconexión a mitad
    // de una operación en curso (ver teardownConnection/
    // handleUnexpectedDisconnect), nunca "nunca se conectó". Ese caso ya lo
    // cubre el guard explícito al inicio de print().
    if (!this.deviceId) throw new NiimbotDisconnectedError('La impresora NIIMBOT B1 se desconectó durante la operación en curso.');
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
    // Si write() falla (protocolo/transporte, ver AUDITORÍA 2026-09-08),
    // responsePromise queda huérfana: nadie más la espera, pero
    // teardownConnection() igual la rechazará más tarde al limpiar
    // this.waiters. Sin este catch mudo, eso dispara un unhandledRejection
    // -- el resultado real (el error de write()) se sigue propagando abajo
    // con el throw normal, esto sólo evita que la promesa huérfana quede
    // sin ningún handler.
    responsePromise.catch(() => undefined);
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
    // El SO ya desconectó físicamente el dispositivo (por eso este callback
    // se disparó) -- physicallyDisconnect: false, para no reintentar un
    // ble.disconnect() redundante/potencialmente fallido sobre algo que ya
    // no está conectado. Fire-and-forget: es un callback síncrono del
    // transporte (onDisconnected), no hay nada que awaitar aquí.
    void this.teardownConnection({ physicallyDisconnect: false });
  }

  /**
   * Único primitivo de limpieza, idempotente -- AUDITORÍA 2026-09-08: antes
   * había DOS caminos de limpieza que podían divergir (teardownConnection()
   * sólo limpiaba estado local; disconnect() además desconectaba
   * físicamente por su cuenta). Ahora normal disconnect() y un handshake
   * fallido usan exactamente esta misma función, con physicallyDisconnect
   * indicando si hace falta cerrar la conexión BLE real (true) o si ya se
   * cerró sola y sólo queda limpiar estado (false, ver
   * handleUnexpectedDisconnect). Deja deviceId/estado local listos para un
   * reintento inmediato: waiters/suscripciones de la sesión anterior nunca
   * reciben datos de la sesión siguiente.
   */
  private async teardownConnection(options: { physicallyDisconnect: boolean }): Promise<void> {
    const deviceId = this.deviceId;
    this.connected = false;
    this.deviceId = null;
    this.unsubscribeNotifications?.();
    this.unsubscribeNotifications = null;
    this.unsubscribeDisconnect?.();
    this.unsubscribeDisconnect = null;
    this.frameAssembler.reset();
    for (const [command, list] of this.waiters) {
      list.forEach((waiter) => waiter.reject(new NiimbotDisconnectedError('Conexión NIIMBOT B1 cerrada.')));
      this.waiters.delete(command);
    }
    if (options.physicallyDisconnect && deviceId) {
      await this.ble.disconnect(deviceId).catch(() => undefined);
    }
  }
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
