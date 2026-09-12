import assert from 'node:assert/strict';
import test from 'node:test';

import type {
  BleNotificationHandler,
  BleTransport,
  BleTransportDevice,
  Unsubscribe,
} from '../../ble-transport';
import { MYC_50X30 } from '../../../label-profile';
import { renderLabel } from '../../../label-renderer';
import type { LabLabelPayload } from '../../../label-types';
import {
  NiimbotB1Adapter,
  NiimbotCommandRejectedError,
  NiimbotDisconnectedError,
  NiimbotNotConnectedError,
  NiimbotPrintInProgressError,
  NiimbotTimeoutError,
} from './niimbot-b1-adapter';
import {
  NIIMBOT_REQUEST,
  decodeNiimbotPacket,
  encodeNiimbotPacket,
} from './protocol';

const PAYLOAD: LabLabelPayload = {
  calibrationDate: '2026-09-01',
  nextCalibrationDate: '2027-09-01',
  equipmentCode: 'ID-1',
  workOrderFolio: '12345',
  certificateFolio: 'MYCA-0001',
};

const DEVICE: BleTransportDevice = {
  id: 'device-1',
  name: 'B1-A1B2C3',
};

const TEST_TIMEOUTS = {
  connectTimeoutMs: 30,
  identifyTimeoutMs: 20,
  commandTimeoutMs: 30,
  printStatusPollIntervalMs: 5,
  printStatusTimeoutMs: 60,
  printEndTimeoutMs: 30,
};

class MockBleTransport
  implements BleTransport
{
  writes: {
    command: number;
    data: Uint8Array;
  }[] = [];

  connectedDevices =
    new Set<string>();

  disconnectHandlers =
    new Map<
      string,
      (() => void)[]
    >();

  disconnectCalls:
    string[] = [];

  private notificationHandler:
    BleNotificationHandler | null =
    null;

  private autoResponses =
    new Map<
      number,
      {
        command: number;
        data: Uint8Array;
      }
    >();

  connectDelayMs =
    0;

  respondTo(
    command: number,
    withResponseCommand: number,
    data:
      Uint8Array =
        Uint8Array.of(1),
  ): void {
    this.autoResponses.set(
      command,
      {
        command:
          withResponseCommand,
        data:
          Uint8Array.from(data),
      },
    );
  }

  stopRespondingTo(
    command: number,
  ): void {
    this.autoResponses.delete(
      command,
    );
  }

  emitResponse(
    command: number,
    data:
      Uint8Array =
        Uint8Array.of(1),
  ): void {
    queueMicrotask(
      () => {
        this.notificationHandler?.(
          encodeNiimbotPacket({
            command,
            data,
          }),
        );
      },
    );
  }

  async isBluetoothOn():
    Promise<boolean> {
    return true;
  }

  async requestPermissions():
    Promise<boolean> {
    return true;
  }

  async startScan():
    Promise<void> {}

  async stopScan():
    Promise<void> {}

  async connect(
    deviceId: string,
  ): Promise<void> {
    if (
      this.connectDelayMs
    ) {
      await new Promise(
        (resolve) =>
          setTimeout(
            resolve,
            this.connectDelayMs,
          ),
      );
    }

    this.connectedDevices.add(
      deviceId,
    );
  }

  async disconnect(
    deviceId: string,
  ): Promise<void> {
    this.disconnectCalls.push(
      deviceId,
    );

    this.connectedDevices.delete(
      deviceId,
    );
  }

  async isConnected(
    deviceId: string,
  ): Promise<boolean> {
    return this.connectedDevices.has(
      deviceId,
    );
  }

  failDiscoverServices =
    false;

  failSubscribeNotifications =
    false;

  subscribeNotificationsCalls =
    0;

  async discoverServices():
    Promise<void> {
    if (
      this.failDiscoverServices
    ) {
      throw new Error(
        'fallo simulado en discoverServices',
      );
    }
  }

  async subscribeNotifications(
    _deviceId: string,
    _serviceUUID: string,
    _characteristicUUID: string,
    onData: BleNotificationHandler,
  ): Promise<Unsubscribe> {
    this.subscribeNotificationsCalls +=
      1;

    if (
      this.failSubscribeNotifications
    ) {
      throw new Error(
        'fallo simulado en subscribeNotifications',
      );
    }

    this.notificationHandler =
      onData;

    return () => {
      this.notificationHandler =
        null;
    };
  }

  failWriteForCommand:
    number | null = null;

  async writeWithoutResponse(
    _deviceId: string,
    _serviceUUID: string,
    _characteristicUUID: string,
    data: Uint8Array,
  ): Promise<void> {
    const decoded =
      decodeNiimbotPacket(
        data,
      );

    if (
      this.failWriteForCommand ===
      decoded.command
    ) {
      throw new Error(
        'fallo simulado de transporte/protocolo al escribir',
      );
    }

    this.writes.push(
      decoded,
    );

    const response =
      this.autoResponses.get(
        decoded.command,
      );

    if (
      response !==
      undefined
    ) {
      this.emitResponse(
        response.command,
        response.data,
      );
    }
  }

  onDisconnected(
    deviceId: string,
    callback: () => void,
  ): Unsubscribe {
    const list =
      this.disconnectHandlers.get(
        deviceId,
      ) ?? [];

    list.push(
      callback,
    );

    this.disconnectHandlers.set(
      deviceId,
      list,
    );

    return () => {
      this.disconnectHandlers.set(
        deviceId,
        (
          this.disconnectHandlers.get(
            deviceId,
          ) ?? []
        ).filter(
          (item) =>
            item !== callback,
        ),
      );
    };
  }

  simulateDisconnect(
    deviceId: string,
  ): void {
    this.connectedDevices.delete(
      deviceId,
    );

    (
      this.disconnectHandlers.get(
        deviceId,
      ) ?? []
    ).forEach(
      (handler) =>
        handler(),
    );
  }
}

function configurePrintControlResponses(
  transport: MockBleTransport,
): void {
  transport.respondTo(
    NIIMBOT_REQUEST.SetDensity,
    0x31,
  );

  transport.respondTo(
    NIIMBOT_REQUEST.SetLabelType,
    0x33,
  );

  transport.respondTo(
    NIIMBOT_REQUEST.PrintStart,
    0x02,
  );

  transport.respondTo(
    NIIMBOT_REQUEST.PageStart,
    0x04,
  );

  transport.respondTo(
    NIIMBOT_REQUEST.SetPageSize,
    0x14,
  );

  transport.respondTo(
    NIIMBOT_REQUEST.PageEnd,
    0xe4,
  );
}

function fullyResponsiveTransport():
  MockBleTransport {
  const transport =
    new MockBleTransport();

  transport.respondTo(
    NIIMBOT_REQUEST.Connect,
    NIIMBOT_REQUEST.ConnectResult,
  );

  transport.respondTo(
    NIIMBOT_REQUEST.PrinterStatusData,
    NIIMBOT_REQUEST.PrinterStatusDataResult,
  );

  configurePrintControlResponses(
    transport,
  );

  transport.respondTo(
    NIIMBOT_REQUEST.PrintStatus,
    NIIMBOT_REQUEST.PrintStatusResult,
    Uint8Array.of(
      0x00, 0x01, 0x64, 0x64,
      0x00, 0x01, 0x00, 0x00,
    ),
  );

  transport.respondTo(
    NIIMBOT_REQUEST.PrintEnd,
    NIIMBOT_REQUEST.PrintEndResult,
  );

  return transport;
}

test('connect() envía Connect y espera ConnectResult', async () => {
  const transport =
    fullyResponsiveTransport();

  const adapter =
    new NiimbotB1Adapter(
      transport,
      TEST_TIMEOUTS,
    );

  assert.equal(
    adapter.isConnected(),
    false,
  );

  await adapter.connect(
    DEVICE,
  );

  assert.equal(
    adapter.isConnected(),
    true,
  );

  assert.equal(
    transport.writes[0]
      ?.command,
    NIIMBOT_REQUEST.Connect,
  );
});

test('connect() sin ConnectResult expira y limpia conexión', async () => {
  const transport =
    new MockBleTransport();

  const adapter =
    new NiimbotB1Adapter(
      transport,
      TEST_TIMEOUTS,
    );

  await assert.rejects(
    adapter.connect(
      DEVICE,
    ),
    NiimbotTimeoutError,
  );

  assert.equal(
    adapter.isConnected(),
    false,
  );
});

test('handshake expirado desconecta físicamente exactamente una vez', async () => {
  const transport =
    new MockBleTransport();

  const adapter =
    new NiimbotB1Adapter(
      transport,
      TEST_TIMEOUTS,
    );

  await assert.rejects(
    adapter.connect(
      DEVICE,
    ),
    NiimbotTimeoutError,
  );

  assert.deepEqual(
    transport.disconnectCalls,
    [
      DEVICE.id,
    ],
  );

  assert.equal(
    transport.connectedDevices.has(
      DEVICE.id,
    ),
    false,
  );
});

test('fallo de escritura durante Connect desconecta físicamente', async () => {
  const transport =
    new MockBleTransport();

  transport.failWriteForCommand =
    NIIMBOT_REQUEST.Connect;

  const adapter =
    new NiimbotB1Adapter(
      transport,
      TEST_TIMEOUTS,
    );

  await assert.rejects(
    adapter.connect(
      DEVICE,
    ),
  );

  assert.deepEqual(
    transport.disconnectCalls,
    [
      DEVICE.id,
    ],
  );

  assert.equal(
    adapter.isConnected(),
    false,
  );
});

test('disconnect() después de handshake fallido no desconecta dos veces', async () => {
  const transport =
    new MockBleTransport();

  const adapter =
    new NiimbotB1Adapter(
      transport,
      TEST_TIMEOUTS,
    );

  await assert.rejects(
    adapter.connect(
      DEVICE,
    ),
    NiimbotTimeoutError,
  );

  await adapter.disconnect();

  assert.deepEqual(
    transport.disconnectCalls,
    [
      DEVICE.id,
    ],
  );
});

test('tras handshake fallido puede reconectar con estado fresco', async () => {
  const transport =
    new MockBleTransport();

  const adapter =
    new NiimbotB1Adapter(
      transport,
      TEST_TIMEOUTS,
    );

  await assert.rejects(
    adapter.connect(
      DEVICE,
    ),
    NiimbotTimeoutError,
  );

  transport.respondTo(
    NIIMBOT_REQUEST.Connect,
    NIIMBOT_REQUEST.ConnectResult,
  );

  await adapter.connect(
    DEVICE,
  );

  assert.equal(
    adapter.isConnected(),
    true,
  );

  assert.equal(
    transport.connectedDevices.has(
      DEVICE.id,
    ),
    true,
  );
});

test('waiters de una sesión fallida no contaminan una sesión nueva', async () => {
  const transport =
    new MockBleTransport();

  const adapter =
    new NiimbotB1Adapter(
      transport,
      TEST_TIMEOUTS,
    );

  await assert.rejects(
    adapter.connect(
      DEVICE,
    ),
    NiimbotTimeoutError,
  );

  transport.respondTo(
    NIIMBOT_REQUEST.Connect,
    NIIMBOT_REQUEST.ConnectResult,
  );

  await adapter.connect(
    DEVICE,
  );

  configurePrintControlResponses(
    transport,
  );

  transport.respondTo(
    NIIMBOT_REQUEST.PrintStatus,
    NIIMBOT_REQUEST.PrintStatusResult,
    Uint8Array.of(
      0x00, 0x01, 0x64, 0x64,
      0x00, 0x01, 0x00, 0x00,
    ),
  );

  transport.respondTo(
    NIIMBOT_REQUEST.PrintEnd,
    NIIMBOT_REQUEST.PrintEndResult,
  );

  const raster =
    renderLabel(
      PAYLOAD,
      MYC_50X30,
      203,
    );

  await adapter.print(
    raster,
  );
});

test('discoverServices() fallido desconecta y permite reintento', async () => {
  const transport =
    new MockBleTransport();

  transport.failDiscoverServices =
    true;

  const adapter =
    new NiimbotB1Adapter(
      transport,
      TEST_TIMEOUTS,
    );

  await assert.rejects(
    adapter.connect(
      DEVICE,
    ),
    /fallo simulado en discoverServices/,
  );

  assert.deepEqual(
    transport.disconnectCalls,
    [
      DEVICE.id,
    ],
  );

  assert.equal(
    adapter.isConnected(),
    false,
  );

  transport.failDiscoverServices =
    false;

  transport.respondTo(
    NIIMBOT_REQUEST.Connect,
    NIIMBOT_REQUEST.ConnectResult,
  );

  await adapter.connect(
    DEVICE,
  );

  assert.equal(
    adapter.isConnected(),
    true,
  );
});

test('subscribeNotifications() fallido desconecta, limpia y permite reintento', async () => {
  const transport =
    new MockBleTransport();

  transport.failSubscribeNotifications =
    true;

  const adapter =
    new NiimbotB1Adapter(
      transport,
      TEST_TIMEOUTS,
    );

  await assert.rejects(
    adapter.connect(
      DEVICE,
    ),
    /fallo simulado en subscribeNotifications/,
  );

  assert.deepEqual(
    transport.disconnectCalls,
    [
      DEVICE.id,
    ],
  );

  assert.equal(
    adapter.isConnected(),
    false,
  );

  assert.equal(
    transport.subscribeNotificationsCalls,
    1,
  );

  transport.failSubscribeNotifications =
    false;

  transport.respondTo(
    NIIMBOT_REQUEST.Connect,
    NIIMBOT_REQUEST.ConnectResult,
  );

  await adapter.connect(
    DEVICE,
  );

  assert.equal(
    adapter.isConnected(),
    true,
  );

  assert.equal(
    transport.subscribeNotificationsCalls,
    2,
  );
});

test('ble.connect() fallido no intenta desconectar algo que nunca conectó', async () => {
  const transport =
    new MockBleTransport();

  transport.connect =
    async () => {
      throw new Error(
        'fallo simulado de conexión BLE',
      );
    };

  const adapter =
    new NiimbotB1Adapter(
      transport,
      TEST_TIMEOUTS,
    );

  await assert.rejects(
    adapter.connect(
      DEVICE,
    ),
    /fallo simulado de conexión BLE/,
  );

  assert.deepEqual(
    transport.disconnectCalls,
    [],
  );

  assert.equal(
    adapter.isConnected(),
    false,
  );
});

test('conexión exitosa no desconecta físicamente por su cuenta', async () => {
  const transport =
    fullyResponsiveTransport();

  const adapter =
    new NiimbotB1Adapter(
      transport,
      TEST_TIMEOUTS,
    );

  await adapter.connect(
    DEVICE,
  );

  assert.equal(
    adapter.isConnected(),
    true,
  );

  assert.deepEqual(
    transport.disconnectCalls,
    [],
  );
});

test('PrinterStatusData es best-effort si sólo expira por timeout', async () => {
  const transport =
    new MockBleTransport();

  transport.respondTo(
    NIIMBOT_REQUEST.Connect,
    NIIMBOT_REQUEST.ConnectResult,
  );

  const adapter =
    new NiimbotB1Adapter(
      transport,
      TEST_TIMEOUTS,
    );

  await adapter.connect(
    DEVICE,
  );

  assert.equal(
    adapter.isConnected(),
    true,
  );
});

test('error real de transporte durante identificación limpia y propaga', async () => {
  const transport =
    new MockBleTransport();

  transport.respondTo(
    NIIMBOT_REQUEST.Connect,
    NIIMBOT_REQUEST.ConnectResult,
  );

  transport.failWriteForCommand =
    NIIMBOT_REQUEST.PrinterStatusData;

  const adapter =
    new NiimbotB1Adapter(
      transport,
      TEST_TIMEOUTS,
    );

  await assert.rejects(
    adapter.connect(
      DEVICE,
    ),
    /fallo simulado de transporte\/protocolo al escribir/,
  );

  assert.equal(
    adapter.isConnected(),
    false,
  );

  assert.deepEqual(
    transport.disconnectCalls,
    [
      DEVICE.id,
    ],
  );

  transport.failWriteForCommand =
    null;

  transport.respondTo(
    NIIMBOT_REQUEST.PrinterStatusData,
    NIIMBOT_REQUEST.PrinterStatusDataResult,
  );

  await adapter.connect(
    DEVICE,
  );

  assert.equal(
    adapter.isConnected(),
    true,
  );
});

test('desconexión física durante identificación rechaza connect()', async () => {
  const transport =
    new MockBleTransport();

  transport.respondTo(
    NIIMBOT_REQUEST.Connect,
    NIIMBOT_REQUEST.ConnectResult,
  );

  const adapter =
    new NiimbotB1Adapter(
      transport,
      TEST_TIMEOUTS,
    );

  const connectPromise =
    adapter.connect(
      DEVICE,
    );

  connectPromise.catch(
    () => undefined,
  );

  await new Promise(
    (resolve) =>
      setTimeout(
        resolve,
        5,
      ),
  );

  transport.simulateDisconnect(
    DEVICE.id,
  );

  await assert.rejects(
    connectPromise,
    NiimbotDisconnectedError,
  );

  assert.equal(
    adapter.isConnected(),
    false,
  );

  transport.respondTo(
    NIIMBOT_REQUEST.PrinterStatusData,
    NIIMBOT_REQUEST.PrinterStatusDataResult,
  );

  await adapter.connect(
    DEVICE,
  );

  assert.equal(
    adapter.isConnected(),
    true,
  );
});

test('print() sin conexión lanza NiimbotNotConnectedError', async () => {
  const transport =
    fullyResponsiveTransport();

  const adapter =
    new NiimbotB1Adapter(
      transport,
      TEST_TIMEOUTS,
    );

  const raster =
    renderLabel(
      PAYLOAD,
      MYC_50X30,
      203,
    );

  await assert.rejects(
    adapter.print(
      raster,
    ),
    NiimbotNotConnectedError,
  );

  assert.equal(
    transport.writes.length,
    0,
  );
});

test('print() respeta control ACK por ACK y termina con status + PrintEnd', async () => {
  const transport =
    fullyResponsiveTransport();

  const adapter =
    new NiimbotB1Adapter(
      transport,
      TEST_TIMEOUTS,
    );

  await adapter.connect(
    DEVICE,
  );

  transport.writes =
    [];

  const raster =
    renderLabel(
      PAYLOAD,
      MYC_50X30,
      203,
    );

  await adapter.print(
    raster,
  );

  const commands =
    transport.writes.map(
      (packet) =>
        packet.command,
    );

  assert.equal(
    commands[0],
    NIIMBOT_REQUEST.SetDensity,
  );

  assert.equal(
    commands[1],
    NIIMBOT_REQUEST.SetLabelType,
  );

  assert.equal(
    commands[2],
    NIIMBOT_REQUEST.PrintStart,
  );

  assert.equal(
    commands[3],
    NIIMBOT_REQUEST.PageStart,
  );

  assert.equal(
    commands[4],
    NIIMBOT_REQUEST.SetPageSize,
  );

  const rowCount =
    commands.filter(
      (command) =>
        command ===
        NIIMBOT_REQUEST.PrintBitmapRow,
    ).length;

  assert.equal(
    rowCount,
    raster.bitmap.rows.length,
  );

  assert.ok(
    commands.includes(
      NIIMBOT_REQUEST.PageEnd,
    ),
  );

  assert.ok(
    commands.includes(
      NIIMBOT_REQUEST.PrintStatus,
    ),
  );

  assert.equal(
    commands.includes(
      NIIMBOT_REQUEST.PrintEnd,
    ),
    true,
  );
});

test('CRÍTICO: ninguna fila 0x85 sale antes del ACK 0x14 de SetPageSize', async () => {
  const transport =
    fullyResponsiveTransport();

  /**
   * Desactivamos únicamente la respuesta automática a SetPageSize.
   * Todo lo anterior puede avanzar normalmente.
   */
  transport.stopRespondingTo(
    NIIMBOT_REQUEST.SetPageSize,
  );

  const adapter =
    new NiimbotB1Adapter(
      transport,
      {
        ...TEST_TIMEOUTS,
        commandTimeoutMs:
          100,
      },
    );

  await adapter.connect(
    DEVICE,
  );

  transport.writes =
    [];

  const raster =
    renderLabel(
      PAYLOAD,
      MYC_50X30,
      203,
    );

  const printPromise =
    adapter.print(
      raster,
    );

  printPromise.catch(
    () => undefined,
  );

  /**
   * Esperamos a que SetPageSize haya sido escrito.
   */
  for (
    let attempt = 0;
    attempt < 20;
    attempt += 1
  ) {
    if (
      transport.writes.some(
        (packet) =>
          packet.command ===
          NIIMBOT_REQUEST.SetPageSize,
      )
    ) {
      break;
    }

    await new Promise(
      (resolve) =>
        setTimeout(
          resolve,
          1,
        ),
    );
  }

  assert.ok(
    transport.writes.some(
      (packet) =>
        packet.command ===
        NIIMBOT_REQUEST.SetPageSize,
    ),
    'SetPageSize debe haberse enviado',
  );

  assert.equal(
    transport.writes.some(
      (packet) =>
        packet.command ===
        NIIMBOT_REQUEST.PrintBitmapRow,
    ),
    false,
    'no puede salir ninguna fila 0x85 mientras falta ACK 0x14',
  );

  /**
   * Liberamos manualmente el ACK 0x14.
   */
  transport.emitResponse(
    0x14,
  );

  await printPromise;

  assert.equal(
    transport.writes.some(
      (packet) =>
        packet.command ===
        NIIMBOT_REQUEST.PrintBitmapRow,
    ),
    true,
    'las filas deben comenzar después de recibir ACK 0x14',
  );
});

test('CRÍTICO: SetPageSize 0x14 con DATA[0]=0 rechaza inmediatamente y ninguna fila 0x85 sale', async () => {
  const transport =
    fullyResponsiveTransport();

  transport.respondTo(
    NIIMBOT_REQUEST.SetPageSize,
    NIIMBOT_REQUEST.SetPageSizeResult,
    Uint8Array.of(0),
  );

  const adapter =
    new NiimbotB1Adapter(
      transport,
      TEST_TIMEOUTS,
    );

  await adapter.connect(
    DEVICE,
  );

  transport.writes = [];

  const raster =
    renderLabel(
      PAYLOAD,
      MYC_50X30,
      203,
    );

  await assert.rejects(
    adapter.print(
      raster,
    ),
    NiimbotCommandRejectedError,
  );

  const commands =
    transport.writes.map(
      (packet) =>
        packet.command,
    );

  assert.ok(
    commands.includes(
      NIIMBOT_REQUEST.SetPageSize,
    ),
  );

  assert.equal(
    commands.includes(
      NIIMBOT_REQUEST.PrintBitmapRow,
    ),
    false,
    'un PageInfo rechazado no puede permitir ninguna fila 0x85',
  );

  assert.equal(
    commands.includes(
      NIIMBOT_REQUEST.PageEnd,
    ),
    false,
  );

  assert.equal(
    commands.includes(
      NIIMBOT_REQUEST.PrintStatus,
    ),
    false,
  );

  assert.equal(
    commands.includes(
      NIIMBOT_REQUEST.PrintEnd,
    ),
    false,
  );
});

test('PrintStart 0x02 con DATA[0]=0 detiene el trabajo antes de PageStart', async () => {
  const transport =
    fullyResponsiveTransport();

  transport.respondTo(
    NIIMBOT_REQUEST.PrintStart,
    NIIMBOT_REQUEST.PrintStartResult,
    Uint8Array.of(0),
  );

  const adapter =
    new NiimbotB1Adapter(
      transport,
      TEST_TIMEOUTS,
    );

  await adapter.connect(
    DEVICE,
  );

  transport.writes = [];

  const raster =
    renderLabel(
      PAYLOAD,
      MYC_50X30,
      203,
    );

  await assert.rejects(
    adapter.print(
      raster,
    ),
    NiimbotCommandRejectedError,
  );

  const commands =
    transport.writes.map(
      (packet) =>
        packet.command,
    );

  assert.deepEqual(
    commands,
    [
      NIIMBOT_REQUEST.SetDensity,
      NIIMBOT_REQUEST.SetLabelType,
      NIIMBOT_REQUEST.PrintStart,
    ],
  );
});

test('PageStart 0x04 con DATA[0]=0 detiene el trabajo antes de SetPageSize', async () => {
  const transport =
    fullyResponsiveTransport();

  transport.respondTo(
    NIIMBOT_REQUEST.PageStart,
    NIIMBOT_REQUEST.PageStartResult,
    Uint8Array.of(0),
  );

  const adapter =
    new NiimbotB1Adapter(
      transport,
      TEST_TIMEOUTS,
    );

  await adapter.connect(
    DEVICE,
  );

  transport.writes = [];

  const raster =
    renderLabel(
      PAYLOAD,
      MYC_50X30,
      203,
    );

  await assert.rejects(
    adapter.print(
      raster,
    ),
    NiimbotCommandRejectedError,
  );

  const commands =
    transport.writes.map(
      (packet) =>
        packet.command,
    );

  assert.deepEqual(
    commands,
    [
      NIIMBOT_REQUEST.SetDensity,
      NIIMBOT_REQUEST.SetLabelType,
      NIIMBOT_REQUEST.PrintStart,
      NIIMBOT_REQUEST.PageStart,
    ],
  );
});

test('respuesta V3 de control sin DATA[0] también se considera rechazo', async () => {
  const transport =
    fullyResponsiveTransport();

  transport.respondTo(
    NIIMBOT_REQUEST.SetPageSize,
    NIIMBOT_REQUEST.SetPageSizeResult,
    new Uint8Array(),
  );

  const adapter =
    new NiimbotB1Adapter(
      transport,
      TEST_TIMEOUTS,
    );

  await adapter.connect(
    DEVICE,
  );

  transport.writes = [];

  const raster =
    renderLabel(
      PAYLOAD,
      MYC_50X30,
      203,
    );

  await assert.rejects(
    adapter.print(
      raster,
    ),
    NiimbotCommandRejectedError,
  );

  assert.equal(
    transport.writes.some(
      (packet) =>
        packet.command ===
        NIIMBOT_REQUEST.PrintBitmapRow,
    ),
    false,
  );
});

test('PageEnd 0xE4 con DATA[0]=0 impide PrintStatus y PrintEnd', async () => {
  const transport =
    fullyResponsiveTransport();

  transport.respondTo(
    NIIMBOT_REQUEST.PageEnd,
    NIIMBOT_REQUEST.PageEndResult,
    Uint8Array.of(0),
  );

  const adapter =
    new NiimbotB1Adapter(
      transport,
      TEST_TIMEOUTS,
    );

  await adapter.connect(
    DEVICE,
  );

  transport.writes = [];

  const raster =
    renderLabel(
      PAYLOAD,
      MYC_50X30,
      203,
    );

  await assert.rejects(
    adapter.print(
      raster,
    ),
    NiimbotCommandRejectedError,
  );

  const commands =
    transport.writes.map(
      (packet) =>
        packet.command,
    );

  assert.ok(
    commands.includes(
      NIIMBOT_REQUEST.PageEnd,
    ),
  );

  assert.equal(
    commands.includes(
      NIIMBOT_REQUEST.PrintStatus,
    ),
    false,
  );

  assert.equal(
    commands.includes(
      NIIMBOT_REQUEST.PrintEnd,
    ),
    false,
  );
});

test('PrintStatus B3 mal formado se rechaza explícitamente', async () => {
  const transport =
    fullyResponsiveTransport();

  transport.respondTo(
    NIIMBOT_REQUEST.PrintStatus,
    NIIMBOT_REQUEST.PrintStatusResult,
    Uint8Array.of(1),
  );

  const adapter =
    new NiimbotB1Adapter(
      transport,
      TEST_TIMEOUTS,
    );

  await adapter.connect(
    DEVICE,
  );

  transport.writes = [];

  const raster =
    renderLabel(
      PAYLOAD,
      MYC_50X30,
      203,
    );

  await assert.rejects(
    adapter.print(
      raster,
    ),
    /PrintStatusResult B3 demasiado corto/,
  );

  assert.equal(
    transport.writes.some(
      (packet) =>
        packet.command ===
        NIIMBOT_REQUEST.PrintEnd,
    ),
    false,
  );
});

test('NiimbotCommandRejectedError conserva request, response y DATA recibidos', async () => {

  const transport =
    fullyResponsiveTransport();

  transport.respondTo(
    NIIMBOT_REQUEST.SetPageSize,
    NIIMBOT_REQUEST.SetPageSizeResult,
    Uint8Array.of(
      0,
      0xaa,
    ),
  );

  const adapter =
    new NiimbotB1Adapter(
      transport,
      TEST_TIMEOUTS,
    );

  await adapter.connect(
    DEVICE,
  );

  const raster =
    renderLabel(
      PAYLOAD,
      MYC_50X30,
      203,
    );

  let captured:
    unknown = null;

  try {
    await adapter.print(
      raster,
    );
  } catch (error) {
    captured =
      error;
  }

  assert.ok(
    captured instanceof
      NiimbotCommandRejectedError,
  );

  assert.equal(
    captured.requestCommand,
    NIIMBOT_REQUEST.SetPageSize,
  );

  assert.equal(
    captured.responseCommand,
    NIIMBOT_REQUEST.SetPageSizeResult,
  );

  assert.deepEqual(
    Array.from(
      captured.responseData,
    ),
    [
      0,
      0xaa,
    ],
  );

});

test('si falta ACK de SetDensity, PrintStart nunca puede comenzar', async () => {
  const transport =
    fullyResponsiveTransport();

  transport.stopRespondingTo(
    NIIMBOT_REQUEST.SetDensity,
  );

  const adapter =
    new NiimbotB1Adapter(
      transport,
      TEST_TIMEOUTS,
    );

  await adapter.connect(
    DEVICE,
  );

  transport.writes = [];

  const raster =
    renderLabel(
      PAYLOAD,
      MYC_50X30,
      203,
    );

  await assert.rejects(
    adapter.print(
      raster,
    ),
    NiimbotTimeoutError,
  );

  const commands =
    transport.writes.map(
      (packet) =>
        packet.command,
    );

  assert.deepEqual(
    commands,
    [
      NIIMBOT_REQUEST.SetDensity,
    ],
  );
});

test('si falta ACK de PageEnd no se consulta PrintStatus ni se envía PrintEnd', async () => {
  const transport =
    fullyResponsiveTransport();

  transport.stopRespondingTo(
    NIIMBOT_REQUEST.PageEnd,
  );

  const adapter =
    new NiimbotB1Adapter(
      transport,
      TEST_TIMEOUTS,
    );

  await adapter.connect(
    DEVICE,
  );

  transport.writes = [];

  const raster =
    renderLabel(
      PAYLOAD,
      MYC_50X30,
      203,
    );

  await assert.rejects(
    adapter.print(
      raster,
    ),
    NiimbotTimeoutError,
  );

  const commands =
    transport.writes.map(
      (packet) =>
        packet.command,
    );

  assert.ok(
    commands.includes(
      NIIMBOT_REQUEST.PageEnd,
    ),
  );

  assert.equal(
    commands.includes(
      NIIMBOT_REQUEST.PrintStatus,
    ),
    false,
  );

  assert.equal(
    commands.includes(
      NIIMBOT_REQUEST.PrintEnd,
    ),
    false,
  );
});

test('PrintStatus usa A3 [00], valida B3 y continúa a PrintEnd', async () => {
  const transport =
    fullyResponsiveTransport();

  const adapter =
    new NiimbotB1Adapter(
      transport,
      TEST_TIMEOUTS,
    );

  await adapter.connect(
    DEVICE,
  );

  transport.writes = [];

  const raster =
    renderLabel(
      PAYLOAD,
      MYC_50X30,
      203,
    );

  await adapter.print(
    raster,
  );

  const statusPackets =
    transport.writes.filter(
      (packet) =>
        packet.command ===
        NIIMBOT_REQUEST.PrintStatus,
    );

  assert.equal(
    statusPackets.length,
    1,
  );

  assert.deepEqual(
    Array.from(
      statusPackets[0].data,
    ),
    [0x00],
  );

  assert.equal(
    transport.writes.some(
      (packet) =>
        packet.command ===
        NIIMBOT_REQUEST.PrintEnd,
    ),
    true,
  );
});

test('print() recorta 400px a 384px antes de SetPageSize y filas', async () => {

  const transport =
    fullyResponsiveTransport();

  const adapter =
    new NiimbotB1Adapter(
      transport,
      TEST_TIMEOUTS,
    );

  await adapter.connect(
    DEVICE,
  );

  transport.writes =
    [];

  const raster =
    renderLabel(
      PAYLOAD,
      MYC_50X30,
      203,
    );

  assert.equal(
    raster.widthPx,
    400,
  );

  await adapter.print(
    raster,
  );

  const setPageSize =
    transport.writes.find(
      (packet) =>
        packet.command ===
        NIIMBOT_REQUEST.SetPageSize,
    );

  assert.ok(
    setPageSize,
  );

  const sentWidthPx =
    (
      setPageSize.data[2] <<
      8
    ) |
    setPageSize.data[3];

  assert.equal(
    sentWidthPx,
    adapter.capabilities
      .printableWidthPx,
  );

  assert.notEqual(
    sentWidthPx,
    raster.widthPx,
  );

  const rowPackets =
    transport.writes.filter(
      (packet) =>
        packet.command ===
        NIIMBOT_REQUEST.PrintBitmapRow,
    );

  const expectedStride =
    Math.ceil(
      adapter.capabilities
        .printableWidthPx /
        8,
    );

  for (
    const row
    of rowPackets
  ) {
    assert.equal(
      row.data.length - 6,
      expectedStride,
    );
  }

});

test('print() bloquea doble impresión', async () => {
  const transport =
    fullyResponsiveTransport();

  /**
   * Dejamos la primera impresión detenida exactamente en SetPageSize.
   * Así podemos demostrar simultáneamente que:
   *
   * 1. printing=true bloquea una segunda impresión.
   * 2. el ACK 0x14 sólo se libera después de que SetPageSize realmente
   *    fue transmitido y su waiter ya existe.
   */
  transport.stopRespondingTo(
    NIIMBOT_REQUEST.SetPageSize,
  );

  const adapter =
    new NiimbotB1Adapter(
      transport,
      {
        ...TEST_TIMEOUTS,
        commandTimeoutMs: 100,
      },
    );

  await adapter.connect(
    DEVICE,
  );

  transport.writes = [];

  const raster =
    renderLabel(
      PAYLOAD,
      MYC_50X30,
      203,
    );

  const firstPrint =
    adapter.print(
      raster,
    );

  firstPrint.catch(
    () => undefined,
  );

  /**
   * Esperamos explícitamente hasta que la primera impresión haya escrito
   * SetPageSize. En ese momento sendAndWait() ya registró el waiter 0x14
   * antes de llamar write(), por lo que emitir el ACK ya no tiene carrera.
   */
  for (
    let attempt = 0;
    attempt < 50;
    attempt += 1
  ) {
    if (
      transport.writes.some(
        (packet) =>
          packet.command ===
          NIIMBOT_REQUEST.SetPageSize,
      )
    ) {
      break;
    }

    await new Promise(
      (resolve) =>
        setTimeout(
          resolve,
          1,
        ),
    );
  }

  assert.ok(
    transport.writes.some(
      (packet) =>
        packet.command ===
        NIIMBOT_REQUEST.SetPageSize,
    ),
    'la primera impresión debe estar esperando el ACK 0x14 de SetPageSize',
  );

  await assert.rejects(
    adapter.print(
      raster,
    ),
    NiimbotPrintInProgressError,
  );

  transport.emitResponse(
    0x14,
  );

  await firstPrint;
});

test('desconexión durante un ACK de impresión rechaza la operación', async () => {
  const transport =
    fullyResponsiveTransport();

  transport.stopRespondingTo(
    NIIMBOT_REQUEST.SetPageSize,
  );

  const adapter =
    new NiimbotB1Adapter(
      transport,
      TEST_TIMEOUTS,
    );

  await adapter.connect(
    DEVICE,
  );

  const raster =
    renderLabel(
      PAYLOAD,
      MYC_50X30,
      203,
    );

  const printPromise =
    adapter.print(
      raster,
    );

  printPromise.catch(
    () => undefined,
  );

  for (
    let attempt = 0;
    attempt < 20;
    attempt += 1
  ) {
    if (
      transport.writes.some(
        (packet) =>
          packet.command ===
          NIIMBOT_REQUEST.SetPageSize,
      )
    ) {
      break;
    }

    await new Promise(
      (resolve) =>
        setTimeout(
          resolve,
          1,
        ),
    );
  }

  transport.simulateDisconnect(
    DEVICE.id,
  );

  await assert.rejects(
    printPromise,
    NiimbotDisconnectedError,
  );

  assert.equal(
    adapter.isConnected(),
    false,
  );
});

test('disconnect() limpia estado y permite reconectar/imprimir', async () => {
  const transport =
    fullyResponsiveTransport();

  const adapter =
    new NiimbotB1Adapter(
      transport,
      TEST_TIMEOUTS,
    );

  await adapter.connect(
    DEVICE,
  );

  await adapter.disconnect();

  assert.equal(
    adapter.isConnected(),
    false,
  );

  await adapter.connect(
    DEVICE,
  );

  assert.equal(
    adapter.isConnected(),
    true,
  );

  const raster =
    renderLabel(
      PAYLOAD,
      MYC_50X30,
      203,
    );

  await adapter.print(
    raster,
  );
});

test('capabilities declara 203 dpi y 384px para B1', () => {
  const adapter =
    new NiimbotB1Adapter(
      new MockBleTransport(),
      TEST_TIMEOUTS,
    );

  assert.equal(
    adapter.capabilities.dpi,
    203,
  );

  assert.equal(
    adapter.capabilities
      .printableWidthPx,
    384,
  );
});

test('printPacketSequenceForQa() sin conexión lanza NiimbotNotConnectedError', async () => {
  const transport =
    fullyResponsiveTransport();

  const adapter =
    new NiimbotB1Adapter(
      transport,
      TEST_TIMEOUTS,
    );

  await assert.rejects(
    adapter.printPacketSequenceForQa(
      [
        {
          command:
            NIIMBOT_REQUEST.PrintBitmapRow,

          data:
            new Uint8Array(
              6,
            ),
        },
      ],
    ),
    NiimbotNotConnectedError,
  );

  assert.equal(
    transport.writes.length,
    0,
  );
});

test('printPacketSequenceForQa() bloquea una segunda llamada concurrente', async () => {
  const transport =
    fullyResponsiveTransport();

  /**
   * Una secuencia QA formada sólo por 0x85 llega inmediatamente a
   * PrintStatus. Quitamos su respuesta para mantener la primera llamada
   * viva mientras hacemos la segunda.
   */
  transport.stopRespondingTo(
    NIIMBOT_REQUEST.PrintStatus,
  );

  const adapter =
    new NiimbotB1Adapter(
      transport,
      {
        ...TEST_TIMEOUTS,
        commandTimeoutMs:
          100,
        printStatusTimeoutMs:
          100,
      },
    );

  await adapter.connect(
    DEVICE,
  );

  const packets = [
    {
      command:
        NIIMBOT_REQUEST.PrintBitmapRow,

      data:
        new Uint8Array(
          6,
        ),
    },
  ];

  const first =
    adapter.printPacketSequenceForQa(
      packets,
    );

  first.catch(
    () => undefined,
  );

  await assert.rejects(
    adapter.printPacketSequenceForQa(
      packets,
    ),
    NiimbotPrintInProgressError,
  );

  const validPageStatus =
    Uint8Array.of(
      0x00,
      0x01,
      0x64,
      0x64,
      0x00,
      0x01,
      0x00,
      0x00,
    );

  transport.respondTo(
    NIIMBOT_REQUEST.PrintStatus,
    NIIMBOT_REQUEST.PrintStatusResult,
    validPageStatus,
  );

  transport.emitResponse(
    NIIMBOT_REQUEST.PrintStatusResult,
    validPageStatus,
  );

  await first;
});

test('printPacketSequenceForQa() respeta ACK de comandos de control y conserva la secuencia recibida', async () => {
  const transport =
    fullyResponsiveTransport();

  const adapter =
    new NiimbotB1Adapter(
      transport,
      TEST_TIMEOUTS,
    );

  await adapter.connect(
    DEVICE,
  );

  transport.writes =
    [];

  const custom = [
    {
      command:
        NIIMBOT_REQUEST.PageStart,

      data:
        Uint8Array.of(
          1,
        ),
    },
    {
      command:
        NIIMBOT_REQUEST.PrintBitmapRow,

      data:
        new Uint8Array(
          6,
        ),
    },
  ];

  await adapter.printPacketSequenceForQa(
    custom,
  );

  const commands =
    transport.writes.map(
      (packet) =>
        packet.command,
    );

  assert.deepEqual(
    commands.slice(
      0,
      2,
    ),
    [
      NIIMBOT_REQUEST.PageStart,
      NIIMBOT_REQUEST.PrintBitmapRow,
    ],
  );

  assert.ok(
    commands.includes(
      NIIMBOT_REQUEST.PrintStatus,
    ),
  );

  assert.equal(
    commands.includes(
      NIIMBOT_REQUEST.PrintEnd,
    ),
    true,
  );
});

test('desconexión durante printPacketSequenceForQa() rechaza la llamada', async () => {
  const transport =
    fullyResponsiveTransport();

  transport.stopRespondingTo(
    NIIMBOT_REQUEST.PageStart,
  );

  const adapter =
    new NiimbotB1Adapter(
      transport,
      TEST_TIMEOUTS,
    );

  await adapter.connect(
    DEVICE,
  );

  const call =
    adapter
      .printPacketSequenceForQa(
        [
          {
            command:
              NIIMBOT_REQUEST.PageStart,

            data:
              Uint8Array.of(
                1,
              ),
          },
          {
            command:
              NIIMBOT_REQUEST.PrintBitmapRow,

            data:
              new Uint8Array(
                6,
              ),
          },
        ],
      );

  call.catch(
    () => undefined,
  );

  queueMicrotask(
    () =>
      transport.simulateDisconnect(
        DEVICE.id,
      ),
  );

  await assert.rejects(
    call,
    NiimbotDisconnectedError,
  );

  assert.equal(
    adapter.isConnected(),
    false,
  );
});