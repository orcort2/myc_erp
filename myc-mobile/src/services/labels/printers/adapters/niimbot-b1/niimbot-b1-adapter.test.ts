import assert from 'node:assert/strict';
import test from 'node:test';

import type { BleNotificationHandler, BleTransport, BleTransportDevice, Unsubscribe } from '../../ble-transport';
import { MYC_50X30 } from '../../../label-profile';
import { renderLabel } from '../../../label-renderer';
import type { LabLabelPayload } from '../../../label-types';
import {
  NiimbotB1Adapter,
  NiimbotDisconnectedError,
  NiimbotNotConnectedError,
  NiimbotPrintInProgressError,
  NiimbotTimeoutError,
} from './niimbot-b1-adapter';
import { NIIMBOT_REQUEST, decodeNiimbotPacket, encodeNiimbotPacket } from './protocol';

const PAYLOAD: LabLabelPayload = {
  calibrationDate: '2026-09-01',
  nextCalibrationDate: '2027-09-01',
  equipmentCode: 'ID-1',
  workOrderFolio: '12345',
  certificateFolio: 'MYCA-0001',
};

const DEVICE: BleTransportDevice = { id: 'device-1', name: 'B1-A1B2C3' };

/** Timeouts cortos exclusivos de este archivo -- nunca los ~8-25s reales de
 * producción (ver NiimbotB1AdapterTimeouts). Esto es lo que permite probar
 * un timeout de verdad en milisegundos, no ejercitar el valor de
 * producción. */
const TEST_TIMEOUTS = {
  connectTimeoutMs: 30,
  identifyTimeoutMs: 20,
  commandTimeoutMs: 30,
  printStatusPollIntervalMs: 5,
  printStatusTimeoutMs: 60,
  printEndTimeoutMs: 30,
};

/** Transporte de prueba: registra cada escritura y, si hay un "auto
 * responder" configurado para ese comando, entrega la respuesta simulada
 * al canal de notificaciones -- usa el protocolo REAL (encode/decode) en
 * ambos lados, así que esto ejerce exactamente el mismo camino de código
 * que ble-manager-transport.ts, sin ningún módulo nativo. */
class MockBleTransport implements BleTransport {
  writes: { command: number; data: Uint8Array }[] = [];
  connectedDevices = new Set<string>();
  disconnectHandlers = new Map<string, (() => void)[]>();
  private notificationHandler: BleNotificationHandler | null = null;
  private autoResponses = new Map<number, number>();
  connectDelayMs = 0;

  respondTo(command: number, withResponseCommand: number): void {
    this.autoResponses.set(command, withResponseCommand);
  }

  async isBluetoothOn(): Promise<boolean> {
    return true;
  }

  async requestPermissions(): Promise<boolean> {
    return true;
  }

  async startScan(): Promise<void> {}

  async stopScan(): Promise<void> {}

  async connect(deviceId: string): Promise<void> {
    if (this.connectDelayMs) await new Promise((resolve) => setTimeout(resolve, this.connectDelayMs));
    this.connectedDevices.add(deviceId);
  }

  async disconnect(deviceId: string): Promise<void> {
    this.connectedDevices.delete(deviceId);
  }

  async isConnected(deviceId: string): Promise<boolean> {
    return this.connectedDevices.has(deviceId);
  }

  async discoverServices(): Promise<void> {}

  async subscribeNotifications(
    _deviceId: string,
    _serviceUUID: string,
    _characteristicUUID: string,
    onData: BleNotificationHandler,
  ): Promise<Unsubscribe> {
    this.notificationHandler = onData;
    return () => {
      this.notificationHandler = null;
    };
  }

  async writeWithoutResponse(_deviceId: string, _serviceUUID: string, _characteristicUUID: string, data: Uint8Array): Promise<void> {
    const decoded = decodeNiimbotPacket(data);
    this.writes.push(decoded);
    const responseCommand = this.autoResponses.get(decoded.command);
    if (responseCommand !== undefined) {
      queueMicrotask(() => {
        this.notificationHandler?.(encodeNiimbotPacket({ command: responseCommand, data: Uint8Array.of(1) }));
      });
    }
  }

  onDisconnected(deviceId: string, callback: () => void): Unsubscribe {
    const list = this.disconnectHandlers.get(deviceId) ?? [];
    list.push(callback);
    this.disconnectHandlers.set(deviceId, list);
    return () => {
      this.disconnectHandlers.set(
        deviceId,
        (this.disconnectHandlers.get(deviceId) ?? []).filter((item) => item !== callback),
      );
    };
  }

  simulateDisconnect(deviceId: string): void {
    this.connectedDevices.delete(deviceId);
    (this.disconnectHandlers.get(deviceId) ?? []).forEach((handler) => handler());
  }
}

function fullyResponsiveTransport(): MockBleTransport {
  const transport = new MockBleTransport();
  transport.respondTo(NIIMBOT_REQUEST.Connect, NIIMBOT_REQUEST.ConnectResult);
  transport.respondTo(NIIMBOT_REQUEST.PrinterStatusData, NIIMBOT_REQUEST.PrinterStatusDataResult);
  transport.respondTo(NIIMBOT_REQUEST.PrintStatus, NIIMBOT_REQUEST.PrintStatusResult);
  transport.respondTo(NIIMBOT_REQUEST.PrintEnd, NIIMBOT_REQUEST.PrintEndResult);
  return transport;
}

test('connect() envía Connect y espera ConnectResult antes de darse por conectado', async () => {
  const transport = fullyResponsiveTransport();
  const adapter = new NiimbotB1Adapter(transport, TEST_TIMEOUTS);
  assert.equal(adapter.isConnected(), false);
  await adapter.connect(DEVICE);
  assert.equal(adapter.isConnected(), true);
  assert.equal(transport.writes[0]?.command, NIIMBOT_REQUEST.Connect);
});

test('connect() sin respuesta ConnectResult expira con NiimbotTimeoutError y no queda conectado', async () => {
  const transport = new MockBleTransport(); // sin auto-respuestas configuradas
  const adapter = new NiimbotB1Adapter(transport, TEST_TIMEOUTS);
  await assert.rejects(adapter.connect(DEVICE), NiimbotTimeoutError);
  assert.equal(adapter.isConnected(), false);
});

test('connect() no bloquea si la identificación (PrinterStatusData) no responde a tiempo -- es best-effort', async () => {
  const transport = new MockBleTransport();
  transport.respondTo(NIIMBOT_REQUEST.Connect, NIIMBOT_REQUEST.ConnectResult);
  // Deliberadamente sin respuesta a PrinterStatusData.
  const adapter = new NiimbotB1Adapter(transport, TEST_TIMEOUTS);
  await adapter.connect(DEVICE);
  assert.equal(adapter.isConnected(), true);
});

test('print() sin conexión previa lanza NiimbotNotConnectedError y no escribe nada', async () => {
  const transport = fullyResponsiveTransport();
  const adapter = new NiimbotB1Adapter(transport, TEST_TIMEOUTS);
  const raster = renderLabel(PAYLOAD, MYC_50X30, 203);
  await assert.rejects(adapter.print(raster), NiimbotNotConnectedError);
  assert.equal(transport.writes.length, 0);
});

test('print() envía densidad->tipo->inicio->página->tamaño->filas->fin de página, sondea estado y cierra con PrintEnd', async () => {
  const transport = fullyResponsiveTransport();
  const adapter = new NiimbotB1Adapter(transport, TEST_TIMEOUTS);
  await adapter.connect(DEVICE);
  transport.writes = []; // descarta el Connect/identify previos para esta aserción

  const raster = renderLabel(PAYLOAD, MYC_50X30, 203);
  await adapter.print(raster);

  const commands = transport.writes.map((packet) => packet.command);
  assert.equal(commands[0], NIIMBOT_REQUEST.SetDensity);
  assert.equal(commands[1], NIIMBOT_REQUEST.SetLabelType);
  assert.equal(commands[2], NIIMBOT_REQUEST.PrintStart);
  assert.equal(commands[3], NIIMBOT_REQUEST.PageStart);
  assert.equal(commands[4], NIIMBOT_REQUEST.SetPageSize);
  const rowCount = commands.filter((command) => command === NIIMBOT_REQUEST.PrintBitmapRow).length;
  assert.equal(rowCount, raster.bitmap.rows.length);
  assert.ok(commands.includes(NIIMBOT_REQUEST.PageEnd));
  assert.ok(commands.includes(NIIMBOT_REQUEST.PrintStatus), 'debe sondear el estado antes de terminar');
  assert.equal(commands[commands.length - 1], NIIMBOT_REQUEST.PrintEnd, 'PrintEnd debe ser el último comando enviado');
});

test('print() nunca deja avanzar una segunda impresión mientras la primera sigue en curso (doble tap)', async () => {
  const transport = fullyResponsiveTransport();
  const adapter = new NiimbotB1Adapter(transport, TEST_TIMEOUTS);
  await adapter.connect(DEVICE);
  const raster = renderLabel(PAYLOAD, MYC_50X30, 203);

  const firstPrint = adapter.print(raster);
  await assert.rejects(adapter.print(raster), NiimbotPrintInProgressError);
  await firstPrint; // deja terminar la primera para no filtrar el timer/handles
});

test('una desconexión a mitad de impresión rechaza la impresión en curso, nunca la deja colgada', async () => {
  const transport = new MockBleTransport();
  transport.respondTo(NIIMBOT_REQUEST.Connect, NIIMBOT_REQUEST.ConnectResult);
  transport.respondTo(NIIMBOT_REQUEST.PrinterStatusData, NIIMBOT_REQUEST.PrinterStatusDataResult);
  // Deliberadamente SIN auto-respuesta a PrintStatus: la impresión se queda
  // esperando el sondeo hasta que simulemos la desconexión.
  const adapter = new NiimbotB1Adapter(transport, TEST_TIMEOUTS);
  await adapter.connect(DEVICE);
  const raster = renderLabel(PAYLOAD, MYC_50X30, 203);

  const printPromise = adapter.print(raster);
  queueMicrotask(() => transport.simulateDisconnect(DEVICE.id));
  await assert.rejects(printPromise, NiimbotDisconnectedError);
  assert.equal(adapter.isConnected(), false);
});

test('disconnect() limpia el estado -- una impresora reconectada puede volver a imprimir', async () => {
  const transport = fullyResponsiveTransport();
  const adapter = new NiimbotB1Adapter(transport, TEST_TIMEOUTS);
  await adapter.connect(DEVICE);
  await adapter.disconnect();
  assert.equal(adapter.isConnected(), false);

  await adapter.connect(DEVICE);
  assert.equal(adapter.isConnected(), true);
  const raster = renderLabel(PAYLOAD, MYC_50X30, 203);
  await adapter.print(raster);
});

test('capabilities declara 203 dpi y 384px de ancho imprimible -- valores públicos conocidos del B1, ver mission section 12', () => {
  const adapter = new NiimbotB1Adapter(new MockBleTransport(), TEST_TIMEOUTS);
  assert.equal(adapter.capabilities.dpi, 203);
  assert.equal(adapter.capabilities.printableWidthPx, 384);
});
