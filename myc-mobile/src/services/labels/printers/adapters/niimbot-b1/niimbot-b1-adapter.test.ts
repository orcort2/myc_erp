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
  disconnectCalls: string[] = [];
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
    this.disconnectCalls.push(deviceId);
    this.connectedDevices.delete(deviceId);
  }

  async isConnected(deviceId: string): Promise<boolean> {
    return this.connectedDevices.has(deviceId);
  }

  failDiscoverServices = false;
  failSubscribeNotifications = false;
  subscribeNotificationsCalls = 0;

  async discoverServices(): Promise<void> {
    if (this.failDiscoverServices) throw new Error('fallo simulado en discoverServices');
  }

  async subscribeNotifications(
    _deviceId: string,
    _serviceUUID: string,
    _characteristicUUID: string,
    onData: BleNotificationHandler,
  ): Promise<Unsubscribe> {
    this.subscribeNotificationsCalls += 1;
    if (this.failSubscribeNotifications) throw new Error('fallo simulado en subscribeNotifications');
    this.notificationHandler = onData;
    return () => {
      this.notificationHandler = null;
    };
  }

  failWriteForCommand: number | null = null;

  async writeWithoutResponse(_deviceId: string, _serviceUUID: string, _characteristicUUID: string, data: Uint8Array): Promise<void> {
    const decoded = decodeNiimbotPacket(data);
    if (this.failWriteForCommand === decoded.command) {
      throw new Error('fallo simulado de transporte/protocolo al escribir');
    }
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

// AUDITORÍA 2026-09-08: la conexión BLE ya se había establecido con éxito
// (transport.connect() nunca lanzó) antes de que el handshake fallara --
// teardownConnection() sólo limpiaba estado local del adaptador, nunca
// desconectaba físicamente. El SO podía seguir "conectado" mientras el
// adaptador se creía libre, dejando el dispositivo inalcanzable para un
// reintento inmediato. Corregido: cualquier fallo de handshake posterior a
// una conexión BLE exitosa debe desconectar físicamente.

test('AUDITORÍA: handshake expirado (timeout) desconecta físicamente el dispositivo, no sólo el estado local', async () => {
  const transport = new MockBleTransport(); // sin auto-respuesta a Connect -> expira
  const adapter = new NiimbotB1Adapter(transport, TEST_TIMEOUTS);

  await assert.rejects(adapter.connect(DEVICE), NiimbotTimeoutError);

  assert.deepEqual(transport.disconnectCalls, [DEVICE.id]);
  assert.equal(transport.connectedDevices.has(DEVICE.id), false, 'el transporte ya no debe reportar el dispositivo conectado');
});

test('AUDITORÍA: un fallo de protocolo/transporte durante el handshake (no sólo timeout) también desconecta físicamente', async () => {
  const transport = new MockBleTransport();
  transport.failWriteForCommand = NIIMBOT_REQUEST.Connect; // la escritura del propio Connect falla
  const adapter = new NiimbotB1Adapter(transport, TEST_TIMEOUTS);

  await assert.rejects(adapter.connect(DEVICE));

  assert.deepEqual(transport.disconnectCalls, [DEVICE.id]);
  assert.equal(adapter.isConnected(), false);
});

test('AUDITORÍA: la limpieza tras un handshake fallido nunca desconecta dos veces', async () => {
  const transport = new MockBleTransport();
  const adapter = new NiimbotB1Adapter(transport, TEST_TIMEOUTS);

  await assert.rejects(adapter.connect(DEVICE), NiimbotTimeoutError);
  await adapter.disconnect(); // llamar disconnect() explícitamente después no debe volver a desconectar

  assert.deepEqual(transport.disconnectCalls, [DEVICE.id], 'un solo disconnect físico, sin duplicados');
});

test('AUDITORÍA: tras un handshake fallido, un reintento inmediato conecta con estado completamente fresco', async () => {
  const transport = new MockBleTransport();
  const adapter = new NiimbotB1Adapter(transport, TEST_TIMEOUTS);

  await assert.rejects(adapter.connect(DEVICE), NiimbotTimeoutError);
  assert.equal(adapter.isConnected(), false);

  transport.respondTo(NIIMBOT_REQUEST.Connect, NIIMBOT_REQUEST.ConnectResult);
  await adapter.connect(DEVICE);

  assert.equal(adapter.isConnected(), true);
  // El reintento debe volver a conectar/suscribirse desde cero -- nunca
  // reutilizar la sesión BLE fallida anterior.
  assert.equal(transport.connectedDevices.has(DEVICE.id), true);
});

test('AUDITORÍA: una respuesta que llega después de que el handshake ya expiró no la recibe ningún waiter de la sesión siguiente', async () => {
  const transport = new MockBleTransport();
  const adapter = new NiimbotB1Adapter(transport, TEST_TIMEOUTS);

  await assert.rejects(adapter.connect(DEVICE), NiimbotTimeoutError);

  // Reconecta con éxito -- una nueva sesión con sus propios waiters.
  transport.respondTo(NIIMBOT_REQUEST.Connect, NIIMBOT_REQUEST.ConnectResult);
  await adapter.connect(DEVICE);
  assert.equal(adapter.isConnected(), true);

  // Una impresión debe poder avanzar con normalidad en la sesión nueva --
  // si algún waiter/suscripción de la sesión fallida hubiera quedado vivo,
  // esto podría resolver con datos equivocados o quedarse colgado.
  transport.respondTo(NIIMBOT_REQUEST.PrintStatus, NIIMBOT_REQUEST.PrintStatusResult);
  transport.respondTo(NIIMBOT_REQUEST.PrintEnd, NIIMBOT_REQUEST.PrintEndResult);
  const raster = renderLabel(PAYLOAD, MYC_50X30, 203);
  await assert.doesNotReject(adapter.print(raster));
});

// AUDITORÍA 2026-09-08 (seguimiento): antes, sólo el try/catch del
// handshake (Connect/ConnectResult) limpiaba y desconectaba físicamente.
// Si ble.connect() tenía éxito pero discoverServices() o
// subscribeNotifications() fallaban -- pasos que ocurrían ANTES de ese
// try/catch -- la conexión BLE física quedaba viva sin que nada la
// cerrara. Corregido: toda la configuración posterior a un ble.connect()
// exitoso vive dentro de un único try/catch.

test('AUDITORÍA: si discoverServices() falla tras un ble.connect() exitoso, desconecta físicamente exactamente una vez y permite reintentar', async () => {
  const transport = new MockBleTransport();
  transport.failDiscoverServices = true;
  const adapter = new NiimbotB1Adapter(transport, TEST_TIMEOUTS);

  await assert.rejects(adapter.connect(DEVICE), /fallo simulado en discoverServices/);

  assert.deepEqual(transport.disconnectCalls, [DEVICE.id], 'debe desconectar físicamente exactamente una vez');
  assert.equal(adapter.isConnected(), false);

  // Reintento inmediato con estado fresco.
  transport.failDiscoverServices = false;
  transport.respondTo(NIIMBOT_REQUEST.Connect, NIIMBOT_REQUEST.ConnectResult);
  await adapter.connect(DEVICE);
  assert.equal(adapter.isConnected(), true);
});

test('AUDITORÍA: si subscribeNotifications() falla tras discoverServices() exitoso, desconecta físicamente exactamente una vez, limpia suscripciones y permite reintentar', async () => {
  const transport = new MockBleTransport();
  transport.failSubscribeNotifications = true;
  const adapter = new NiimbotB1Adapter(transport, TEST_TIMEOUTS);

  await assert.rejects(adapter.connect(DEVICE), /fallo simulado en subscribeNotifications/);

  assert.deepEqual(transport.disconnectCalls, [DEVICE.id], 'debe desconectar físicamente exactamente una vez');
  assert.equal(adapter.isConnected(), false);
  assert.equal(transport.subscribeNotificationsCalls, 1, 'el intento fallido no debe reintentarse por su cuenta');

  // Reintento inmediato: nuevas suscripciones desde cero, sin arrastrar nada del intento anterior.
  transport.failSubscribeNotifications = false;
  transport.respondTo(NIIMBOT_REQUEST.Connect, NIIMBOT_REQUEST.ConnectResult);
  await adapter.connect(DEVICE);
  assert.equal(adapter.isConnected(), true);
  assert.equal(transport.subscribeNotificationsCalls, 2);
});

test('AUDITORÍA: ble.connect() que nunca tiene éxito no intenta desconectar (nada que desconectar)', async () => {
  const transport = new MockBleTransport();
  transport.connect = async () => {
    throw new Error('fallo simulado de conexión BLE');
  };
  const adapter = new NiimbotB1Adapter(transport, TEST_TIMEOUTS);

  await assert.rejects(adapter.connect(DEVICE), /fallo simulado de conexión BLE/);

  assert.deepEqual(transport.disconnectCalls, [], 'nunca hubo conexión física que cerrar');
  assert.equal(adapter.isConnected(), false);
});

test('AUDITORÍA: una conexión exitosa nunca dispara una desconexión física', async () => {
  const transport = fullyResponsiveTransport();
  const adapter = new NiimbotB1Adapter(transport, TEST_TIMEOUTS);

  await adapter.connect(DEVICE);

  assert.equal(adapter.isConnected(), true);
  assert.deepEqual(transport.disconnectCalls, [], 'una conexión exitosa nunca debe desconectar por su cuenta');
});

test('connect() no bloquea si la identificación (PrinterStatusData) no responde a tiempo -- es best-effort', async () => {
  const transport = new MockBleTransport();
  transport.respondTo(NIIMBOT_REQUEST.Connect, NIIMBOT_REQUEST.ConnectResult);
  // Deliberadamente sin respuesta a PrinterStatusData.
  const adapter = new NiimbotB1Adapter(transport, TEST_TIMEOUTS);
  await adapter.connect(DEVICE);
  assert.equal(adapter.isConnected(), true);
});

// AUDITORÍA 2026-09-08 (ronda 2): la identificación best-effort
// (PrinterStatusData) ignoraba CUALQUIER error, no sólo un timeout -- un
// fallo real de transporte o una desconexión física durante esa ventana
// dejaba connect() resolviendo "con éxito" mientras this.connected ya
// había vuelto a false por dentro. Ahora sólo un NiimbotTimeoutError se
// ignora; cualquier otro error debe limpiar y propagarse.

test('AUDITORÍA (ronda 2): un error real de transporte (no timeout) durante la identificación best-effort limpia y propaga -- nunca reporta éxito con connected en false por dentro', async () => {
  const transport = new MockBleTransport();
  transport.respondTo(NIIMBOT_REQUEST.Connect, NIIMBOT_REQUEST.ConnectResult);
  transport.failWriteForCommand = NIIMBOT_REQUEST.PrinterStatusData;
  const adapter = new NiimbotB1Adapter(transport, TEST_TIMEOUTS);

  await assert.rejects(adapter.connect(DEVICE), /fallo simulado de transporte\/protocolo al escribir/);

  assert.equal(adapter.isConnected(), false);
  assert.deepEqual(transport.disconnectCalls, [DEVICE.id], 'la conexión BLE ya se había establecido -- debe desconectarse físicamente');

  // Reintento inmediato debe funcionar con estado fresco.
  transport.failWriteForCommand = null;
  transport.respondTo(NIIMBOT_REQUEST.PrinterStatusData, NIIMBOT_REQUEST.PrinterStatusDataResult);
  await adapter.connect(DEVICE);
  assert.equal(adapter.isConnected(), true);
});

test('AUDITORÍA (ronda 2): una desconexión física real durante la identificación best-effort rechaza connect(), nunca resuelve "conectado" con el estado ya en false', async () => {
  const transport = new MockBleTransport();
  transport.respondTo(NIIMBOT_REQUEST.Connect, NIIMBOT_REQUEST.ConnectResult);
  // Deliberadamente sin auto-respuesta a PrinterStatusData: la
  // identificación se queda esperando hasta que simulemos la desconexión.
  const adapter = new NiimbotB1Adapter(transport, TEST_TIMEOUTS);

  const connectPromise = adapter.connect(DEVICE);
  connectPromise.catch(() => undefined);
  // Deja que el handshake (Connect/ConnectResult) termine y el adaptador
  // entre a la ventana de identificación antes de desconectar -- si
  // desconectamos demasiado pronto no habría todavía ningún waiter para
  // PrinterStatusDataResult que rechazar.
  await new Promise((resolve) => setTimeout(resolve, 5));
  transport.simulateDisconnect(DEVICE.id);

  await assert.rejects(connectPromise, NiimbotDisconnectedError);
  assert.equal(adapter.isConnected(), false);

  // Reintento inmediato debe funcionar con estado fresco.
  transport.respondTo(NIIMBOT_REQUEST.PrinterStatusData, NIIMBOT_REQUEST.PrinterStatusDataResult);
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

test('print() recorta el raster físico (400px) al ancho real del cabezal (384px) antes de construir SetPageSize/filas -- AUDITORÍA 2026-09-08', async () => {
  const transport = fullyResponsiveTransport();
  const adapter = new NiimbotB1Adapter(transport, TEST_TIMEOUTS);
  await adapter.connect(DEVICE);
  transport.writes = [];

  const raster = renderLabel(PAYLOAD, MYC_50X30, 203);
  assert.equal(raster.widthPx, 400, 'precondición: el raster físico completo es 400px, más ancho que el cabezal');
  await adapter.print(raster);

  const setPageSize = transport.writes.find((packet) => packet.command === NIIMBOT_REQUEST.SetPageSize);
  assert.ok(setPageSize);
  // data = [heightHi,heightLo,widthHi,widthLo,0,1] -- ver buildSetPageSizePacket.
  const sentWidthPx = (setPageSize!.data[2] << 8) | setPageSize!.data[3];
  assert.equal(sentWidthPx, adapter.capabilities.printableWidthPx, 'SetPageSize debe llevar el ancho real imprimible (384), nunca el ancho físico completo (400)');
  assert.notEqual(sentWidthPx, raster.widthPx);

  const rowPackets = transport.writes.filter((packet) => packet.command === NIIMBOT_REQUEST.PrintBitmapRow);
  const expectedStride = Math.ceil(adapter.capabilities.printableWidthPx / 8);
  for (const row of rowPackets) {
    // data = [rowHi,rowLo,0,0,0,repeat, ...bytesDeLaFila] -- header de 6 bytes, ver encodeRowPacket.
    assert.equal(row.data.length - 6, expectedStride, 'cada fila enviada debe tener exactamente el stride de 384px, nunca el de 400px');
  }
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
