import type { RasterLabel } from '../../../label-types';
import type { BleTransport, Unsubscribe } from '../../ble-transport';
import { cropRasterToPrintableWidth } from '../../raster-adapt';
import type {
  LabelPrinterAdapter,
  PrintOptions,
  PrinterCapabilities,
  PrinterDevice,
} from '../../types';
import {
  NIIMBOT_BLE_CHARACTERISTIC_UUID,
  NIIMBOT_BLE_SERVICE_UUID,
  NIIMBOT_REQUEST,
  NiimbotFrameAssembler,
  NiimbotPageStatusError,
  buildConnectPacket,
  buildPrintEndPacket,
  buildPrintJobPackets,
  buildPrintStatusQueryPacket,
  buildPrinterStatusDataPacket,
  encodeNiimbotPacket,
  parsePrintStatusResult,
  type DecodedNiimbotPacket,
  type NiimbotPageStatus,
} from './protocol';

/**
 * Adaptador NIIMBOT B1 / protocolo V3.
 *
 * El B1 utiliza WRITE_NO_RESPONSE a nivel GATT, pero los comandos de
 * control del protocolo NIIMBOT sí tienen respuesta protocolaria.
 *
 * Flujo V3 auditado:
 *
 *   SetDensity   0x21 -> 0x31
 *   SetLabelType 0x23 -> 0x33
 *   PrintStart   0x01 -> 0x02
 *   PageStart    0x03 -> 0x04
 *   SetPageSize  0x13 -> 0x14
 *   PageEnd      0xE3 -> 0xE4
 *   PrintEnd     0xF3 -> 0xF4
 *
 * PrintBitmapRow 0x85 se transmite como stream y no espera un ACK
 * individual por fila.
 *
 * AUDITORÍA SDK OFICIAL 2026-09-09
 * =================================
 *
 * La inspección de cPrinterV3 del SDK oficial confirmó que varias
 * respuestas de control no se consideran exitosas únicamente por recibir
 * el opcode esperado.
 *
 * Para las transiciones V3 confirmadas:
 *
 *   PrintStartResult   0x02
 *   PageStartResult    0x04
 *   SetPageSizeResult  0x14
 *   PageEndResult      0xE4
 *   PrintEndResult     0xF4
 *
 * el SDK inspecciona DATA[0] y considera 0x01 como aceptación.
 *
 * Por ello este adapter diferencia:
 *
 *   - "recibí la respuesta esperada"
 *   - "la impresora aceptó la operación"
 *
 * PrintStatusResult 0xB3 se trata aparte: no es un ACK simple. El SDK
 * oficial exige LEN >= 8 y construye un PageStatus con esos bytes.
 *
 * Durante el bring-up físico se registra ese estado sin inventar todavía
 * una condición de completado no demostrada.
 */

const DEFAULT_TIMEOUTS = {
  connectTimeoutMs: 8_000,
  identifyTimeoutMs: 3_000,
  commandTimeoutMs: 5_000,
  printStatusPollIntervalMs: 300,
  printStatusTimeoutMs: 25_000,
  printEndTimeoutMs: 5_000,
};

export type NiimbotB1AdapterTimeouts =
  typeof DEFAULT_TIMEOUTS;

export class NiimbotTimeoutError extends Error {}

export class NiimbotDisconnectedError extends Error {}

export class NiimbotPrintInProgressError extends Error {}

export class NiimbotNotConnectedError extends Error {}

/**
 * La impresora respondió al comando, pero indicó que la transición no fue
 * aceptada.
 *
 * Es distinto de timeout:
 *
 * - Timeout: no llegó la respuesta esperada.
 * - Rejected: sí llegó, pero DATA[0] != 0x01.
 */
export class NiimbotCommandRejectedError extends Error {
  readonly requestCommand: number;
  readonly responseCommand: number;
  readonly responseData: Uint8Array;

  constructor(
    requestCommand: number,
    response: DecodedNiimbotPacket,
  ) {
    const status =
      response.data.length > 0
        ? `0x${response.data[0].toString(16).padStart(2, '0')}`
        : 'sin DATA[0]';

    super(
      `La impresora NIIMBOT rechazó el comando 0x${requestCommand
        .toString(16)
        .padStart(2, '0')} ` +
        `(respuesta 0x${response.command
          .toString(16)
          .padStart(2, '0')}, estado ${status}).`,
    );

    this.name =
      'NiimbotCommandRejectedError';

    this.requestCommand =
      requestCommand;

    this.responseCommand =
      response.command;

    this.responseData =
      Uint8Array.from(
        response.data,
      );
  }
}

type PendingWaiter = {
  resolve(
    packet: DecodedNiimbotPacket,
  ): void;

  reject(
    error: Error,
  ): void;
};

export class NiimbotB1Adapter
  implements LabelPrinterAdapter
{
  readonly id =
    'niimbot-b1' as const;

  readonly displayName =
    'NIIMBOT B1';

  readonly transport =
    'ble' as const;

  readonly capabilities:
    PrinterCapabilities = {
      dpi: 203,
      printableWidthPx: 384,
    };

  private readonly ble:
    BleTransport;

  private readonly timeouts:
    NiimbotB1AdapterTimeouts;

  private deviceId:
    string | null = null;

  private connected =
    false;

  private printing =
    false;

  private frameAssembler =
    new NiimbotFrameAssembler();

  private waiters =
    new Map<
      number,
      PendingWaiter[]
    >();

  private unsubscribeNotifications:
    Unsubscribe | null = null;

  private unsubscribeDisconnect:
    Unsubscribe | null = null;

  constructor(
    ble: BleTransport,
    timeouts:
      Partial<NiimbotB1AdapterTimeouts> = {},
  ) {
    this.ble =
      ble;

    this.timeouts = {
      ...DEFAULT_TIMEOUTS,
      ...timeouts,
    };
  }

  isConnected(): boolean {
    return this.connected;
  }

  async connect(
    device: PrinterDevice,
  ): Promise<void> {
    let physicalConnectionEstablished =
      false;

    try {
      await this.ble.connect(
        device.id,
      );

      physicalConnectionEstablished =
        true;

      this.deviceId =
        device.id;

      this.frameAssembler.reset();

      await this.ble.discoverServices(
        device.id,
      );

      this.unsubscribeNotifications =
        await this.ble.subscribeNotifications(
          device.id,
          NIIMBOT_BLE_SERVICE_UUID,
          NIIMBOT_BLE_CHARACTERISTIC_UUID,
          (chunk) =>
            this.handleIncoming(
              chunk,
            ),
        );

      this.unsubscribeDisconnect =
        this.ble.onDisconnected(
          device.id,
          () =>
            this.handleUnexpectedDisconnect(),
        );

      this.connected =
        true;

      /**
       * ConnectResult no se mete todavía en la validación DATA[0] de los
       * comandos de impresión. Conservamos su comportamiento existente.
       */
      await this.sendAndWait(
        buildConnectPacket(),
        NIIMBOT_REQUEST.ConnectResult,
        this.timeouts.connectTimeoutMs,
      );
    } catch (error) {
      await this.teardownConnection({
        physicallyDisconnect:
          physicalConnectionEstablished,
      });

      throw error;
    }

    /**
     * Identificación best-effort.
     *
     * Un timeout no bloquea una conexión B1 ya confirmada. Cualquier otro
     * error sí se propaga porque puede representar una desconexión real.
     */
    try {
      await this.sendAndWait(
        buildPrinterStatusDataPacket(),
        NIIMBOT_REQUEST.PrinterStatusDataResult,
        this.timeouts.identifyTimeoutMs,
      );
    } catch (error) {
      if (
        error instanceof
        NiimbotTimeoutError
      ) {
        return;
      }

      await this.teardownConnection({
        physicallyDisconnect:
          true,
      });

      throw error;
    }
  }

  async disconnect(): Promise<void> {
    await this.teardownConnection({
      physicallyDisconnect:
        true,
    });
  }

  async print(
    label: RasterLabel,
    options?: PrintOptions,
  ): Promise<void> {
    this.assertCanStartPrint();

    this.printing =
      true;

    try {
      const copies =
        Math.max(
          1,
          options?.copies ?? 1,
        );

      const printable =
        cropRasterToPrintableWidth(
          label,
          this.capabilities
            .printableWidthPx,
        );

      const packets =
        buildPrintJobPackets(
          printable,
          {
            density:
              options?.density,
          },
        );

      for (
        let copy = 0;
        copy < copies;
        copy += 1
      ) {
        await this.sendPrintJobPackets(
          packets,
        );

        await this.waitForPrintComplete();

        /**
         * cPrinterV3::jcSetPrintTerminal():
         *
         *   F3 01 00 -> F4
         *
         * El SDK oficial exige DATA[0] == 0x01.
         */
        await this.sendAndWaitAccepted(
          buildPrintEndPacket(),
          NIIMBOT_REQUEST.PrintEndResult,
          this.timeouts.printEndTimeoutMs,
        );
      }
    } finally {
      this.printing =
        false;
    }
  }

  /**
   * SOLO QA/desarrollo.
   *
   * Usa exactamente la misma máquina de estados que print(). La única
   * diferencia es que los paquetes son construidos por la herramienta QA.
   */
  async printPacketSequenceForQa(
    packets: {
      command: number;
      data: Uint8Array;
    }[],
  ): Promise<void> {
    this.assertCanStartPrint();

    this.printing =
      true;

    try {
      await this.sendPrintJobPackets(
        packets,
      );

      await this.waitForPrintComplete();

      await this.sendAndWaitAccepted(
        buildPrintEndPacket(),
        NIIMBOT_REQUEST.PrintEndResult,
        this.timeouts.printEndTimeoutMs,
      );
    } finally {
      this.printing =
        false;
    }
  }

  /**
   * Envía una página respetando la máquina de estados V3.
   *
   * Los comandos de control esperan una respuesta y, cuando su semántica
   * fue confirmada contra el SDK oficial, exigen DATA[0] == 0x01.
   *
   * PrintBitmapRow 0x85 sigue siendo streaming sin ACK individual.
   */
  private async sendPrintJobPackets(
    packets: {
      command: number;
      data: Uint8Array;
    }[],
  ): Promise<void> {
    for (
      const packet
      of packets
    ) {
      const expectedResponse =
        this.expectedPrintControlResponse(
          packet.command,
        );

      if (
        expectedResponse !==
        null
      ) {
        if (
          this.requiresAcceptedStatus(
            packet.command,
          )
        ) {
          await this.sendAndWaitAccepted(
            packet,
            expectedResponse,
            this.timeouts.commandTimeoutMs,
          );
        } else {
          await this.sendAndWait(
            packet,
            expectedResponse,
            this.timeouts.commandTimeoutMs,
          );
        }

        continue;
      }

      await this.write(
        packet,
      );
    }
  }

  /**
   * ACK correspondiente a cada comando de control del trabajo.
   */
  private expectedPrintControlResponse(
    command: number,
  ): number | null {
    switch (command) {
      case NIIMBOT_REQUEST.SetDensity:
        return NIIMBOT_REQUEST.SetDensityResult;

      case NIIMBOT_REQUEST.SetLabelType:
        return NIIMBOT_REQUEST.SetLabelTypeResult;

      case NIIMBOT_REQUEST.PrintStart:
        return NIIMBOT_REQUEST.PrintStartResult;

      case NIIMBOT_REQUEST.PageStart:
        return NIIMBOT_REQUEST.PageStartResult;

      case NIIMBOT_REQUEST.SetPageSize:
        return NIIMBOT_REQUEST.SetPageSizeResult;

      case NIIMBOT_REQUEST.PageEnd:
        return NIIMBOT_REQUEST.PageEndResult;

      case NIIMBOT_REQUEST.PrintBitmapRow:
        return null;

      default:
        /**
         * QA puede contener comandos experimentales. No inventamos una
         * respuesta para comandos cuyo contrato no conocemos.
         */
        return null;
    }
  }

  /**
   * Comandos para los que hemos confirmado en el SDK oficial V3 que
   * recibir el opcode de respuesta NO basta: DATA[0] debe ser 0x01.
   *
   * SetDensity/SetLabelType se mantienen por ahora como ACK por opcode.
   * No extendemos una semántica que todavía no hemos demostrado.
   */
  private requiresAcceptedStatus(
    requestCommand: number,
  ): boolean {
    switch (requestCommand) {
      case NIIMBOT_REQUEST.PrintStart:
      case NIIMBOT_REQUEST.PageStart:
      case NIIMBOT_REQUEST.SetPageSize:
      case NIIMBOT_REQUEST.PageEnd:
      case NIIMBOT_REQUEST.PrintEnd:
        return true;

      default:
        return false;
    }
  }

  private assertCanStartPrint(): void {
    if (
      !this.connected ||
      !this.deviceId
    ) {
      throw new NiimbotNotConnectedError(
        'No hay conexión activa con la impresora NIIMBOT B1.',
      );
    }

    if (
      this.printing
    ) {
      throw new NiimbotPrintInProgressError(
        'Ya hay una impresión en curso; espera a que termine.',
      );
    }
  }

  private async waitForPrintComplete(): Promise<void> {
    const deadline =
      Date.now() +
      this.timeouts
        .printStatusTimeoutMs;

    let previousStatus:
      NiimbotPageStatus | null =
        null;

    for (;;) {
      if (
        !this.connected
      ) {
        throw new NiimbotDisconnectedError(
          'La impresora se desconectó durante la impresión.',
        );
      }

      try {
        const response =
          await this.sendAndWait(
            buildPrintStatusQueryPacket(),
            NIIMBOT_REQUEST.PrintStatusResult,
            this.timeouts.commandTimeoutMs,
          );

        const status =
          parsePrintStatusResult(
            response,
          );

        this.logPrintStatus(
          status,
          response,
          previousStatus,
        );

        const printCompleted =
          status.field0 === 1 &&
          status.field1 === 100 &&
          status.field2 === 100 &&
          status.field4 === 0 &&
          status.field5 === 0;

        if (
          printCompleted
        ) {
          return;
        }

        previousStatus =
          status;
      } catch (error) {
        if (
          error instanceof
          NiimbotDisconnectedError
        ) {
          throw error;
        }

        if (
          error instanceof
          NiimbotPageStatusError
        ) {
          throw error;
        }
      }

      if (
        Date.now() >=
        deadline
      ) {
        throw new NiimbotTimeoutError(
          'La impresora no alcanzó un estado de impresión confirmado a tiempo.',
        );
      }

      await delay(
        this.timeouts
          .printStatusPollIntervalMs,
      );
    }
  }

  /**
   * Diagnóstico temporal de bring-up físico.
   *
   * No asigna nombres semánticos todavía a los campos del PageStatus:
   * sólo muestra exactamente lo que devuelve el B1 para poder comparar
   * estados sucesivos con el comportamiento del SDK oficial.
   */
  private logPrintStatus(
    status: NiimbotPageStatus,
    response: DecodedNiimbotPacket,
    previousStatus:
      NiimbotPageStatus | null,
  ): void {
    const rawData =
      Array.from(
        response.data,
      )
        .map(
          (byte) =>
            byte
              .toString(16)
              .padStart(2, '0'),
        )
        .join(' ');

    const changed =
      previousStatus === null ||
      status.field0 !==
        previousStatus.field0 ||
      status.field1 !==
        previousStatus.field1 ||
      status.field2 !==
        previousStatus.field2 ||
      status.field3 !==
        previousStatus.field3 ||
      status.field4 !==
        previousStatus.field4 ||
      status.field5 !==
        previousStatus.field5;

    console.log(
      '[NIIMBOT B1] PrintStatus B3',
      {
        rawData,
        field0:
          status.field0,
        field1:
          status.field1,
        field2:
          status.field2,
        field3:
          status.field3,
        field4:
          status.field4,
        field5:
          status.field5,
        extraLength:
          status.extraLength,
        extraData:
          Array.from(
            status.extraData,
          )
            .map(
              (byte) =>
                byte
                  .toString(16)
                  .padStart(2, '0'),
            )
            .join(' '),
        changed,
      },
    );
  }

  private async write(
    packet: {
      command: number;
      data: Uint8Array;
    },
  ): Promise<void> {
    if (
      !this.deviceId
    ) {
      throw new NiimbotDisconnectedError(
        'La impresora NIIMBOT B1 se desconectó durante la operación en curso.',
      );
    }

    await this.ble.writeWithoutResponse(
      this.deviceId,
      NIIMBOT_BLE_SERVICE_UUID,
      NIIMBOT_BLE_CHARACTERISTIC_UUID,
      encodeNiimbotPacket(
        packet,
      ),
    );
  }

  /**
   * Envía un comando y espera únicamente el opcode de respuesta.
   *
   * Se conserva para comandos cuyo payload de respuesta todavía no tiene
   * una semántica de aceptación confirmada.
   */
  private async sendAndWait(
    packet: {
      command: number;
      data: Uint8Array;
    },
    expectedResponse: number,
    timeoutMs: number,
  ): Promise<DecodedNiimbotPacket> {
    const responsePromise =
      this.waitForResponse(
        expectedResponse,
        timeoutMs,
      );

    /**
     * Si write() falla, el waiter queda registrado hasta timeout/teardown.
     * El catch evita un unhandledRejection sin ocultar el error de write().
     */
    responsePromise.catch(
      () => undefined,
    );

    await this.write(
      packet,
    );

    return responsePromise;
  }

  /**
   * Variante para las transiciones V3 cuya aceptación ya fue confirmada
   * contra el SDK oficial.
   *
   * Contrato:
   *
   *   1. Debe llegar expectedResponse.
   *   2. La respuesta debe contener DATA[0].
   *   3. DATA[0] debe ser exactamente 0x01.
   *
   * Una respuesta explícita con otro valor NO se convierte en timeout:
   * se reporta inmediatamente como rechazo de protocolo.
   */
  private async sendAndWaitAccepted(
    packet: {
      command: number;
      data: Uint8Array;
    },
    expectedResponse: number,
    timeoutMs: number,
  ): Promise<DecodedNiimbotPacket> {
    const response =
      await this.sendAndWait(
        packet,
        expectedResponse,
        timeoutMs,
      );

    if (
      response.data.length < 1 ||
      response.data[0] !== 0x01
    ) {
      throw new NiimbotCommandRejectedError(
        packet.command,
        response,
      );
    }

    return response;
  }

  private waitForResponse(
    command: number,
    timeoutMs: number,
  ): Promise<DecodedNiimbotPacket> {
    return new Promise(
      (
        resolve,
        reject,
      ) => {
        const waiter:
          PendingWaiter = {
            resolve:
              (packet) => {
                clearTimeout(
                  timer,
                );

                resolve(
                  packet,
                );
              },

            reject:
              (error) => {
                clearTimeout(
                  timer,
                );

                reject(
                  error,
                );
              },
          };

        const timer =
          setTimeout(
            () => {
              this.removeWaiter(
                command,
                waiter,
              );

              reject(
                new NiimbotTimeoutError(
                  `La impresora no respondió a tiempo (comando 0x${command
                    .toString(16)
                    .padStart(2, '0')}).`,
                ),
              );
            },
            timeoutMs,
          );

        const list =
          this.waiters.get(
            command,
          ) ?? [];

        list.push(
          waiter,
        );

        this.waiters.set(
          command,
          list,
        );
      },
    );
  }

  private removeWaiter(
    command: number,
    waiter: PendingWaiter,
  ): void {
    const list =
      this.waiters.get(
        command,
      );

    if (
      !list
    ) {
      return;
    }

    const next =
      list.filter(
        (item) =>
          item !== waiter,
      );

    if (
      next.length
    ) {
      this.waiters.set(
        command,
        next,
      );
    } else {
      this.waiters.delete(
        command,
      );
    }
  }

  private handleIncoming(
    chunk: Uint8Array,
  ): void {
    for (
      const packet
      of this.frameAssembler.push(
        chunk,
      )
    ) {
      const list =
        this.waiters.get(
          packet.command,
        );

      if (
        !list?.length
      ) {
        this.logUnsolicitedPacket(
          packet,
        );

        continue;
      }

      this.waiters.delete(
        packet.command,
      );

      list.forEach(
        (waiter) =>
          waiter.resolve(
            packet,
          ),
      );
    }
  }

  /**
   * Diagnóstico temporal de bring-up físico.
   *
   * El SDK oficial V3 procesa paquetes espontáneos durante commitJob(),
   * especialmente 0xD3 y 0xDB. Antes, cualquier paquete recibido sin waiter
   * activo se descartaba silenciosamente; eso nos hacía perder justamente
   * la información que necesitamos observar en la B1 real.
   *
   * Esta función NO responde, NO crea nuevos waiters y NO altera la máquina
   * de estados. Sólo registra paquetes válidos que llegaron sin una espera
   * explícita asociada.
   */
  private logUnsolicitedPacket(
    packet: DecodedNiimbotPacket,
  ): void {
    const commandHex =
      packet.command
        .toString(16)
        .padStart(2, '0');

    const rawData =
      Array.from(
        packet.data,
      )
        .map(
          (byte) =>
            byte
              .toString(16)
              .padStart(2, '0'),
        )
        .join(' ');

    const isKnownCommitJobEvent =
      packet.command === 0xd3 ||
      packet.command === 0xdb;

    console.log(
      isKnownCommitJobEvent
        ? '[NIIMBOT B1] Evento espontáneo V3'
        : '[NIIMBOT B1] Paquete espontáneo',
      {
        command:
          `0x${commandHex}`,
        dataLength:
          packet.data.length,
        rawData,
      },
    );
  }

  private handleUnexpectedDisconnect(): void {
    void this.teardownConnection({
      physicallyDisconnect:
        false,
    });
  }

  private async teardownConnection(
    options: {
      physicallyDisconnect:
        boolean;
    },
  ): Promise<void> {
    const deviceId =
      this.deviceId;

    this.connected =
      false;

    this.deviceId =
      null;

    this.unsubscribeNotifications?.();

    this.unsubscribeNotifications =
      null;

    this.unsubscribeDisconnect?.();

    this.unsubscribeDisconnect =
      null;

    this.frameAssembler.reset();

    for (
      const [
        command,
        list,
      ]
      of this.waiters
    ) {
      list.forEach(
        (waiter) =>
          waiter.reject(
            new NiimbotDisconnectedError(
              'Conexión NIIMBOT B1 cerrada.',
            ),
          ),
      );

      this.waiters.delete(
        command,
      );
    }

    if (
      options.physicallyDisconnect &&
      deviceId
    ) {
      await this.ble
        .disconnect(
          deviceId,
        )
        .catch(
          () => undefined,
        );
    }
  }
}

function delay(
  ms: number,
): Promise<void> {
  return new Promise(
    (resolve) =>
      setTimeout(
        resolve,
        ms,
      ),
  );
}