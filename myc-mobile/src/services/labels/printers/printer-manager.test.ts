import assert from 'node:assert/strict';
import test from 'node:test';

import { MYC_50X30 } from '../label-profile';
import { renderLabel } from '../label-renderer';
import type { LabLabelPayload } from '../label-types';
import type { BleTransport, BleTransportDevice } from './ble-transport';
import {
  BluetoothDisabledError,
  BluetoothPermissionDeniedError,
  PrinterBusyError,
  PrinterManager,
  PrinterNotReadyError,
  PrinterQaUnsupportedError,
  UnknownPrinterAdapterError,
} from './printer-manager';
import type { PreferredPrinterStore } from './printer-manager';
import type { LabelPrinterAdapter, PreferredPrinter, PrinterDevice } from './types';

const PAYLOAD: LabLabelPayload = {
  calibrationDate: '2026-09-01',
  equipmentCode: 'ID-1',
  workOrderFolio: '12345',
  certificateFolio: 'MYCA-0001',
};

const RASTER = renderLabel(PAYLOAD, MYC_50X30, 203);

class FakeAdapter implements LabelPrinterAdapter {
  connected = false;
  printCalls: unknown[] = [];
  connectCalls: PrinterDevice[] = [];
  failPrintWith: Error | null = null;
  // Opcional a propósito, igual que en LabelPrinterAdapter -- ningún test
  // existente lo asigna, así que FakeAdapter sigue modelando un adaptador
  // que NO soporta QA salvo que un test lo asigne explícitamente.
  printPacketSequenceForQa?: (packets: { command: number; data: Uint8Array }[]) => Promise<void>;

  constructor(
    readonly id: 'niimbot-b1' | 'nelko-pm220',
    readonly displayName: string,
  ) {}

  readonly transport = 'ble' as const;
  readonly capabilities = { dpi: 203, printableWidthPx: 384 };

  isConnected(): boolean {
    return this.connected;
  }

  async connect(device: PrinterDevice): Promise<void> {
    this.connectCalls.push(device);
    this.connected = true;
  }

  async disconnect(): Promise<void> {
    this.connected = false;
  }

  async print(label: unknown): Promise<void> {
    if (this.failPrintWith) throw this.failPrintWith;
    this.printCalls.push(label);
  }
}

type FakeTransportOptions = {
  devicesToDiscover?: BleTransportDevice[];
  permissionsGranted?: boolean | (() => Promise<boolean>);
  bluetoothOn?: boolean;
};

function fakeBleTransport(devicesToDiscoverOrOptions: BleTransportDevice[] | FakeTransportOptions = []): BleTransport & { startScanCalls: number } {
  const options: FakeTransportOptions = Array.isArray(devicesToDiscoverOrOptions)
    ? { devicesToDiscover: devicesToDiscoverOrOptions }
    : devicesToDiscoverOrOptions;
  const devicesToDiscover = options.devicesToDiscover ?? [];
  const permissionsGranted = options.permissionsGranted ?? true;
  const bluetoothOn = options.bluetoothOn ?? true;

  return {
    startScanCalls: 0,
    isBluetoothOn: async () => bluetoothOn,
    requestPermissions: async () => (typeof permissionsGranted === 'function' ? permissionsGranted() : permissionsGranted),
    async startScan(onFound) {
      this.startScanCalls += 1;
      devicesToDiscover.forEach((device) => onFound(device));
    },
    stopScan: async () => {},
    connect: async () => {},
    disconnect: async () => {},
    isConnected: async () => false,
    discoverServices: async () => {},
    subscribeNotifications: async () => () => undefined,
    writeWithoutResponse: async () => {},
    onDisconnected: () => () => undefined,
  };
}

function inMemoryStore(): PreferredPrinterStore & { saved: PreferredPrinter[] } {
  let current: PreferredPrinter | null = null;
  const saved: PreferredPrinter[] = [];
  return {
    saved,
    read: async () => current,
    write: async (printer) => {
      current = printer;
      saved.push(printer);
    },
    clear: async () => {
      current = null;
    },
  };
}

test('scan() clasifica cada dispositivo descubierto y nunca ofrece un desconocido como impresora', async () => {
  const devices: BleTransportDevice[] = [
    { id: '1', name: 'B1-AAAA' },
    { id: '2', name: 'PM220-BBBB' },
    { id: '3', name: 'AirPods Pro' },
  ];
  const manager = new PrinterManager(fakeBleTransport(devices), {}, inMemoryStore());
  const found: string[] = [];
  await manager.scan((classification) => {
    found.push(classification.kind === 'recognized' ? classification.family.adapterId : 'unknown');
  });
  assert.deepEqual(found, ['niimbot-b1', 'nelko-pm220', 'unknown']);
});

test('scan() nunca reporta el mismo dispositivo dos veces (deduplicación por id)', async () => {
  const devices: BleTransportDevice[] = [{ id: '1', name: 'B1-AAAA' }, { id: '1', name: 'B1-AAAA' }];
  const manager = new PrinterManager(fakeBleTransport(devices), {}, inMemoryStore());
  let count = 0;
  await manager.scan(() => {
    count += 1;
  });
  assert.equal(count, 1);
});

/**
 * AUDITORÍA 2026-09-08 (seguimiento): BleTransport ya implementaba
 * requestPermissions()/isBluetoothOn(), pero scan() nunca los llamaba --
 * el permiso de runtime de Android podía nunca pedirse antes del primer
 * escaneo. Estos tests fijan el orden exacto: permiso -> Bluetooth ->
 * recién entonces startScan() nativo.
 */

test('AUDITORÍA: con permiso concedido y Bluetooth encendido, el scan nativo arranca con normalidad', async () => {
  const transport = fakeBleTransport({ devicesToDiscover: [{ id: '1', name: 'B1-AAAA' }] });
  const manager = new PrinterManager(transport, {}, inMemoryStore());
  const found: string[] = [];
  await manager.scan((classification) => found.push(classification.device.id));
  assert.equal(transport.startScanCalls, 1);
  assert.deepEqual(found, ['1']);
});

test('AUDITORÍA: permiso de Bluetooth denegado -> startScan nativo NUNCA se llama, error tipado y accionable', async () => {
  const transport = fakeBleTransport({ permissionsGranted: false });
  const manager = new PrinterManager(transport, {}, inMemoryStore());
  await assert.rejects(manager.scan(() => {}), BluetoothPermissionDeniedError);
  assert.equal(transport.startScanCalls, 0, 'nunca debe arrancar el scan nativo sin permiso');
});

test('AUDITORÍA: Bluetooth apagado -> startScan nativo NUNCA se llama, error tipado y accionable', async () => {
  const transport = fakeBleTransport({ bluetoothOn: false });
  const manager = new PrinterManager(transport, {}, inMemoryStore());
  await assert.rejects(manager.scan(() => {}), BluetoothDisabledError);
  assert.equal(transport.startScanCalls, 0, 'nunca debe arrancar el scan nativo con Bluetooth apagado');
});

test('AUDITORÍA: un error al pedir permisos se propaga limpio -- nunca arranca el scan ni lo esconde', async () => {
  const transport = fakeBleTransport({
    permissionsGranted: async () => {
      throw new Error('fallo nativo simulado al pedir permisos');
    },
  });
  const manager = new PrinterManager(transport, {}, inMemoryStore());
  await assert.rejects(manager.scan(() => {}), /fallo nativo simulado al pedir permisos/);
  assert.equal(transport.startScanCalls, 0);
});

test('AUDITORÍA: un scan repetido vuelve a validar permiso/Bluetooth cada vez y sigue limpiando correctamente', async () => {
  const transport = fakeBleTransport({ devicesToDiscover: [{ id: '1', name: 'B1-AAAA' }] });
  const manager = new PrinterManager(transport, {}, inMemoryStore());

  await manager.scan(() => {});
  await manager.scan(() => {});

  assert.equal(transport.startScanCalls, 2, 'cada scan debe volver a pasar por el chequeo y arrancar de nuevo');
});

/**
 * AUDITORÍA 2026-09-08 (ronda 2): connectAndRemember() y connectPreferred()
 * llamaban adapter.connect() directo, sin el mismo chequeo de permiso/
 * Bluetooth que ya exige scan() -- si Android revocaba el permiso entre
 * sesiones, el fallo llegaba como error nativo genérico en vez de
 * BluetoothPermissionDeniedError/BluetoothDisabledError.
 */

test('AUDITORÍA (ronda 2): connectAndRemember() exige permiso de Bluetooth -- denegado nunca llega a adapter.connect()', async () => {
  const adapter = new FakeAdapter('niimbot-b1', 'NIIMBOT B1');
  const transport = fakeBleTransport({ permissionsGranted: false });
  const manager = new PrinterManager(transport, { 'niimbot-b1': () => adapter }, inMemoryStore());
  await assert.rejects(manager.connectAndRemember('niimbot-b1', { id: 'd', name: 'B1' }), BluetoothPermissionDeniedError);
  assert.equal(adapter.connectCalls.length, 0);
});

test('AUDITORÍA (ronda 2): connectAndRemember() exige Bluetooth encendido -- apagado nunca llega a adapter.connect()', async () => {
  const adapter = new FakeAdapter('niimbot-b1', 'NIIMBOT B1');
  const transport = fakeBleTransport({ bluetoothOn: false });
  const manager = new PrinterManager(transport, { 'niimbot-b1': () => adapter }, inMemoryStore());
  await assert.rejects(manager.connectAndRemember('niimbot-b1', { id: 'd', name: 'B1' }), BluetoothDisabledError);
  assert.equal(adapter.connectCalls.length, 0);
});

test('AUDITORÍA (ronda 2): connectPreferred() exige permiso de Bluetooth -- denegado nunca llega a adapter.connect()', async () => {
  const adapter = new FakeAdapter('niimbot-b1', 'NIIMBOT B1');
  const store = inMemoryStore();
  await store.write({ adapterId: 'niimbot-b1', deviceId: 'saved-device', deviceName: 'B1-9999', savedAt: 'x' });
  const transport = fakeBleTransport({ permissionsGranted: false });
  const manager = new PrinterManager(transport, { 'niimbot-b1': () => adapter }, store);
  await assert.rejects(manager.connectPreferred(), BluetoothPermissionDeniedError);
  assert.equal(adapter.connectCalls.length, 0);
});

test('AUDITORÍA (ronda 2): connectPreferred() exige Bluetooth encendido -- apagado nunca llega a adapter.connect()', async () => {
  const adapter = new FakeAdapter('niimbot-b1', 'NIIMBOT B1');
  const store = inMemoryStore();
  await store.write({ adapterId: 'niimbot-b1', deviceId: 'saved-device', deviceName: 'B1-9999', savedAt: 'x' });
  const transport = fakeBleTransport({ bluetoothOn: false });
  const manager = new PrinterManager(transport, { 'niimbot-b1': () => adapter }, store);
  await assert.rejects(manager.connectPreferred(), BluetoothDisabledError);
  assert.equal(adapter.connectCalls.length, 0);
});

test('AUDITORÍA (ronda 2): connectPreferred() sin impresora guardada nunca pide permiso/Bluetooth -- sigue devolviendo false sin más', async () => {
  const transport = fakeBleTransport({ permissionsGranted: false, bluetoothOn: false });
  const manager = new PrinterManager(transport, {}, inMemoryStore());
  assert.equal(await manager.connectPreferred(), false);
});

/**
 * AUDITORÍA 2026-09-08 (ronda 2): cambiar de una B1 conectada a otra no
 * tenía frontera explícita -- connectAndRemember() podía llamar
 * adapter.connect(device) aunque ya existiera un adaptador activo,
 * dejando la impresora vieja físicamente conectada mientras deviceId
 * pasaba a representar la nueva.
 */

test('AUDITORÍA (ronda 2): conectar una impresora nueva desconecta la activa antes de conectar la nueva -- nunca deja dos físicamente vivas', async () => {
  const adapterA = new FakeAdapter('niimbot-b1', 'NIIMBOT B1');
  const adapterB = new FakeAdapter('nelko-pm220', 'NELKO PM220');
  const manager = new PrinterManager(
    fakeBleTransport(),
    { 'niimbot-b1': () => adapterA, 'nelko-pm220': () => adapterB },
    inMemoryStore(),
  );

  await manager.connectAndRemember('niimbot-b1', { id: 'device-a', name: 'B1-A' });
  assert.equal(adapterA.isConnected(), true);

  await manager.connectAndRemember('nelko-pm220', { id: 'device-b', name: 'PM220-B' });

  assert.equal(adapterA.isConnected(), false, 'la impresora anterior debe quedar desconectada antes de conectar la nueva');
  assert.equal(adapterB.isConnected(), true);
});

test('AUDITORÍA (ronda 2): no se puede cambiar de impresora mientras hay una impresión en curso -- PrinterBusyError, la activa sigue conectada', async () => {
  const adapterA = new FakeAdapter('niimbot-b1', 'NIIMBOT B1');
  let resolvePrint: () => void = () => {};
  adapterA.print = () => new Promise((resolve) => { resolvePrint = resolve; });
  const adapterB = new FakeAdapter('nelko-pm220', 'NELKO PM220');
  const manager = new PrinterManager(
    fakeBleTransport(),
    { 'niimbot-b1': () => adapterA, 'nelko-pm220': () => adapterB },
    inMemoryStore(),
  );
  await manager.connectAndRemember('niimbot-b1', { id: 'device-a', name: 'B1-A' });

  const printing = manager.print(RASTER);
  await assert.rejects(manager.connectAndRemember('nelko-pm220', { id: 'device-b', name: 'PM220-B' }), PrinterBusyError);

  assert.equal(adapterA.isConnected(), true, 'la impresora en uso nunca debe desconectarse a mitad de una impresión');
  assert.equal(adapterB.isConnected(), false);
  resolvePrint();
  await printing;
});

test('connectAndRemember conecta el adaptador correcto y persiste la impresora preferida', async () => {
  const adapter = new FakeAdapter('niimbot-b1', 'NIIMBOT B1');
  const store = inMemoryStore();
  const manager = new PrinterManager(fakeBleTransport(), { 'niimbot-b1': () => adapter }, store);
  const device: PrinterDevice = { id: 'device-1', name: 'B1-AAAA' };

  await manager.connectAndRemember('niimbot-b1', device);

  assert.equal(manager.isReady(), true);
  assert.equal(manager.activePrinterDisplayName(), 'NIIMBOT B1');
  assert.deepEqual(adapter.connectCalls, [device]);
  assert.equal(store.saved.length, 1);
  assert.equal(store.saved[0].deviceId, 'device-1');
  assert.equal(store.saved[0].adapterId, 'niimbot-b1');
});

test('connectAndRemember con un adapterId sin registrar lanza UnknownPrinterAdapterError', async () => {
  const manager = new PrinterManager(fakeBleTransport(), {}, inMemoryStore());
  await assert.rejects(
    manager.connectAndRemember('niimbot-b1', { id: 'x', name: null }),
    UnknownPrinterAdapterError,
  );
});

test('connectPreferred() reconecta la impresora guardada sin escanear', async () => {
  const adapter = new FakeAdapter('niimbot-b1', 'NIIMBOT B1');
  const store = inMemoryStore();
  await store.write({ adapterId: 'niimbot-b1', deviceId: 'saved-device', deviceName: 'B1-9999', savedAt: 'x' });
  const manager = new PrinterManager(fakeBleTransport(), { 'niimbot-b1': () => adapter }, store);

  const reconnected = await manager.connectPreferred();

  assert.equal(reconnected, true);
  assert.equal(manager.isReady(), true);
  assert.deepEqual(adapter.connectCalls, [{ id: 'saved-device', name: 'B1-9999' }]);
});

test('connectPreferred() devuelve false (sin lanzar) cuando no hay impresora guardada', async () => {
  const manager = new PrinterManager(fakeBleTransport(), {}, inMemoryStore());
  assert.equal(await manager.connectPreferred(), false);
  assert.equal(manager.isReady(), false);
});

test('print() sin impresora conectada lanza PrinterNotReadyError', async () => {
  const manager = new PrinterManager(fakeBleTransport(), {}, inMemoryStore());
  await assert.rejects(manager.print(RASTER), PrinterNotReadyError);
});

test('print() nunca deja avanzar una segunda impresión mientras la primera sigue en curso', async () => {
  const adapter = new FakeAdapter('niimbot-b1', 'NIIMBOT B1');
  let resolveFirstPrint: () => void = () => {};
  adapter.print = () => new Promise((resolve) => { resolveFirstPrint = resolve; });
  const manager = new PrinterManager(fakeBleTransport(), { 'niimbot-b1': () => adapter }, inMemoryStore());
  await manager.connectAndRemember('niimbot-b1', { id: 'd', name: 'B1' });

  const firstPrint = manager.print(RASTER);
  await assert.rejects(manager.print(RASTER), PrinterBusyError);
  resolveFirstPrint();
  await firstPrint;
});

// AUDITORÍA 2026-09-08 (herramienta de QA para la divergencia documentada del
// header de PrintBitmapRow del B1): printQaPacketSequence() es SOLO para
// QA/desarrollo -- nunca la usa print()/printLabel().

test('printQaPacketSequence() sin impresora conectada lanza PrinterNotReadyError', async () => {
  const manager = new PrinterManager(fakeBleTransport(), {}, inMemoryStore());
  await assert.rejects(manager.printQaPacketSequence([]), PrinterNotReadyError);
});

test('printQaPacketSequence() con un adaptador que no implementa printPacketSequenceForQa lanza PrinterQaUnsupportedError', async () => {
  const adapter = new FakeAdapter('nelko-pm220', 'NELKO PM220'); // FakeAdapter nunca implementa el método opcional
  const manager = new PrinterManager(fakeBleTransport(), { 'nelko-pm220': () => adapter }, inMemoryStore());
  await manager.connectAndRemember('nelko-pm220', { id: 'd', name: 'PM220' });
  await assert.rejects(manager.printQaPacketSequence([]), PrinterQaUnsupportedError);
});

test('printQaPacketSequence() delega en el adaptador activo cuando SÍ implementa printPacketSequenceForQa', async () => {
  const adapter = new FakeAdapter('niimbot-b1', 'NIIMBOT B1');
  const qaCalls: unknown[] = [];
  adapter.printPacketSequenceForQa = async (packets) => { qaCalls.push(packets); };
  const manager = new PrinterManager(fakeBleTransport(), { 'niimbot-b1': () => adapter }, inMemoryStore());
  await manager.connectAndRemember('niimbot-b1', { id: 'd', name: 'B1' });

  const packets = [{ command: 0x85, data: new Uint8Array(6) }];
  await manager.printQaPacketSequence(packets);

  assert.deepEqual(qaCalls, [packets]);
});

test('printQaPacketSequence() nunca se intercala con una impresión de producción en curso', async () => {
  const adapter = new FakeAdapter('niimbot-b1', 'NIIMBOT B1');
  let resolveFirstPrint: () => void = () => {};
  adapter.print = () => new Promise((resolve) => { resolveFirstPrint = resolve; });
  adapter.printPacketSequenceForQa = async () => undefined;
  const manager = new PrinterManager(fakeBleTransport(), { 'niimbot-b1': () => adapter }, inMemoryStore());
  await manager.connectAndRemember('niimbot-b1', { id: 'd', name: 'B1' });

  const firstPrint = manager.print(RASTER);
  await assert.rejects(manager.printQaPacketSequence([]), PrinterBusyError);
  resolveFirstPrint();
  await firstPrint;
});

test('activeCapabilities() refleja al adaptador realmente conectado, nunca una suposición fija de 203dpi', async () => {
  const manager = new PrinterManager(fakeBleTransport(), {}, inMemoryStore());
  assert.equal(manager.activeCapabilities(), null);
  const adapter = new FakeAdapter('niimbot-b1', 'NIIMBOT B1');
  const managerWithAdapter = new PrinterManager(fakeBleTransport(), { 'niimbot-b1': () => adapter }, inMemoryStore());
  await managerWithAdapter.connectAndRemember('niimbot-b1', { id: 'd', name: 'B1' });
  assert.deepEqual(managerWithAdapter.activeCapabilities(), { dpi: 203, printableWidthPx: 384 });
});

test('forget() desconecta y borra la impresora preferida -- connectPreferred() ya no encuentra nada', async () => {
  const adapter = new FakeAdapter('niimbot-b1', 'NIIMBOT B1');
  const store = inMemoryStore();
  const manager = new PrinterManager(fakeBleTransport(), { 'niimbot-b1': () => adapter }, store);
  await manager.connectAndRemember('niimbot-b1', { id: 'd', name: 'B1' });

  await manager.forget();

  assert.equal(manager.isReady(), false);
  assert.equal(adapter.isConnected(), false);
  assert.equal(await manager.connectPreferred(), false);
});
