import assert from 'node:assert/strict';
import test from 'node:test';

import { MYC_50X30 } from '../label-profile';
import { renderLabel } from '../label-renderer';
import type { LabLabelPayload } from '../label-types';
import type { BleTransport, BleTransportDevice } from './ble-transport';
import { PrinterBusyError, PrinterManager, PrinterNotReadyError, UnknownPrinterAdapterError } from './printer-manager';
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

function fakeBleTransport(devicesToDiscover: BleTransportDevice[] = []): BleTransport {
  return {
    isBluetoothOn: async () => true,
    requestPermissions: async () => true,
    startScan: async (onFound) => {
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
