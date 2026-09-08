import assert from 'node:assert/strict';
import test from 'node:test';

import type { BleTransport, DeviceInspectionReport } from '../../ble-transport';
import { NelkoDiagnosticsUnavailableError, runNelkoDiagnostics } from './nelko-diagnostics';

const DEVICE = { id: 'device-1', name: 'PM220-0042' };

const SAMPLE_REPORT: DeviceInspectionReport = {
  deviceId: DEVICE.id,
  advertisedName: 'PM220-0042',
  manufacturerData: 'aabbcc',
  advertisedServiceUUIDs: ['0000ff00-0000-1000-8000-00805f9b34fb'],
  services: [
    {
      uuid: '0000ff00-0000-1000-8000-00805f9b34fb',
      characteristics: [{ uuid: '0000ff01-0000-1000-8000-00805f9b34fb', properties: ['Write', 'Notify'] }],
    },
  ],
};

function mockTransport(overrides: Partial<BleTransport> = {}): BleTransport {
  const calls: string[] = [];
  return {
    calls,
    isBluetoothOn: async () => true,
    requestPermissions: async () => true,
    startScan: async () => {},
    stopScan: async () => {},
    connect: async () => {
      calls.push('connect');
    },
    disconnect: async () => {
      calls.push('disconnect');
    },
    isConnected: async () => true,
    discoverServices: async () => {
      calls.push('discoverServices');
    },
    subscribeNotifications: async () => () => undefined,
    writeWithoutResponse: async () => {
      calls.push('writeWithoutResponse');
    },
    onDisconnected: () => () => undefined,
    inspect: async () => SAMPLE_REPORT,
    ...overrides,
  } as BleTransport & { calls: string[] };
}

test('runNelkoDiagnostics conecta, inspecciona y siempre desconecta -- nunca escribe ningún byte', async () => {
  const transport = mockTransport() as BleTransport & { calls: string[] };
  const report = await runNelkoDiagnostics(transport, DEVICE);
  assert.deepEqual(report, SAMPLE_REPORT);
  assert.deepEqual(transport.calls, ['connect', 'discoverServices', 'disconnect']);
});

test('runNelkoDiagnostics desconecta incluso si inspect() falla -- nunca deja la conexión colgada', async () => {
  const transport = mockTransport({
    inspect: async () => {
      throw new Error('boom');
    },
  }) as BleTransport & { calls: string[] };
  await assert.rejects(runNelkoDiagnostics(transport, DEVICE), /boom/);
  assert.deepEqual(transport.calls, ['connect', 'discoverServices', 'disconnect']);
});

test('un transporte sin inspect() rechaza explícitamente en vez de fallar de forma confusa', async () => {
  const transport = mockTransport();
  delete (transport as { inspect?: unknown }).inspect;
  await assert.rejects(runNelkoDiagnostics(transport, DEVICE), NelkoDiagnosticsUnavailableError);
});
