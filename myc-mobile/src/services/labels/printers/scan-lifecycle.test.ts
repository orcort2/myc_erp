import assert from 'node:assert/strict';
import test from 'node:test';

import type { BleTransport, BleTransportDevice } from './ble-transport';
import { PrinterManager } from './printer-manager';
import type { PreferredPrinterStore } from './printer-manager';

/**
 * AUDITORÍA 2026-09-08: BleManagerTransport.startScan() awaitaba sólo
 * BleManager.scan(...), que resuelve en cuanto el scan NATIVO arranca, no
 * cuando termina -- PrinterManager.scan() devolvía el control de inmediato
 * mientras el escaneo seguía activo, y los listeners sólo se limpiaban en
 * stopScan() (nunca en error, y potencialmente acumulándose en escaneos
 * repetidos). Corregido en ble-manager-transport.ts -- ver su docstring de
 * startScan() para el detalle exacto de la corrección (onStopScan +
 * cancelación explícita + timer de seguridad, limpieza única vía
 * cleanupScanListeners).
 *
 * ble-manager-transport.ts NO es testeable directamente en Node (importa
 * react-native-ble-manager -> react-native, que tsx/esbuild no puede
 * transformar fuera de Metro -- confirmado durante esta implementación).
 * Este archivo fija el CONTRATO async correcto que cualquier BleTransport
 * real debe cumplir (el scan permanece activo hasta completarse/cancelarse,
 * los listeners se liberan exactamente una vez, un error también limpia)
 * usando un doble de prueba que modela ese contrato explícitamente, y
 * verifica que PrinterManager.scan()/stopScan() componen correctamente
 * contra él -- la misma composición que usa la app real vía
 * label-print-service.ts.
 */

function flushMicrotasks(): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, 0));
}

class LifecycleAwareFakeTransport implements BleTransport {
  listenerCount = 0;
  stopScanCalls = 0;
  startScanCalls = 0;
  shouldFailNextScan = false;
  private onDeviceFound: ((device: BleTransportDevice) => void) | null = null;
  private pendingSettle: (() => void) | null = null;

  async isBluetoothOn(): Promise<boolean> {
    return true;
  }

  async requestPermissions(): Promise<boolean> {
    return true;
  }

  async startScan(onDeviceFound: (device: BleTransportDevice) => void, _timeoutMs: number): Promise<void> {
    this.startScanCalls += 1;
    if (this.shouldFailNextScan) {
      this.shouldFailNextScan = false;
      throw new Error('scan nativo falló');
    }
    this.listenerCount += 1; // simula suscribirse a onDiscoverPeripheral + onStopScan
    this.onDeviceFound = onDeviceFound;
    return new Promise((resolve) => {
      this.pendingSettle = () => {
        this.listenerCount -= 1; // simula el remove() de ambas suscripciones
        this.onDeviceFound = null;
        this.pendingSettle = null;
        resolve();
      };
    });
  }

  async stopScan(): Promise<void> {
    this.stopScanCalls += 1;
    this.pendingSettle?.();
  }

  emitDevice(device: BleTransportDevice): void {
    this.onDeviceFound?.(device);
  }

  async connect(): Promise<void> {}
  async disconnect(): Promise<void> {}
  async isConnected(): Promise<boolean> {
    return false;
  }
  async discoverServices(): Promise<void> {}
  async subscribeNotifications(): Promise<() => void> {
    return () => undefined;
  }
  async writeWithoutResponse(): Promise<void> {}
  onDisconnected(): () => void {
    return () => undefined;
  }
}

function inMemoryStore(): PreferredPrinterStore {
  return { read: async () => null, write: async () => undefined, clear: async () => undefined };
}

test('el scan permanece activo (la promesa no resuelve) hasta completarse -- nunca resuelve apenas arranca', async () => {
  const transport = new LifecycleAwareFakeTransport();
  const manager = new PrinterManager(transport, {}, inMemoryStore());

  let resolved = false;
  const scanPromise = manager.scan(() => {}).then(() => {
    resolved = true;
  });
  await flushMicrotasks();
  assert.equal(resolved, false, 'el scan no debe resolver antes de completarse/cancelarse');

  await manager.stopScan();
  await scanPromise;
  assert.equal(resolved, true);
});

test('los dispositivos que llegan durante la ventana de escaneo se emiten al callback', async () => {
  const transport = new LifecycleAwareFakeTransport();
  const manager = new PrinterManager(transport, {}, inMemoryStore());
  const found: string[] = [];

  const scanPromise = manager.scan((classification) => found.push(classification.device.id));
  // AUDITORÍA 2026-09-08 (ronda 2): scan() ahora espera requestPermissions()
  // + isBluetoothOn() (ver PrinterManager.scan()) antes de llegar a
  // startScan() -- sin este flush, emitDevice() se dispararía ANTES de que
  // el transporte de prueba tuviera siquiera un onDeviceFound registrado
  // (se perdería en silencio). flushMicrotasks() drena toda la cadena de
  // promesas pendientes de forma determinista (no es un delay arbitrario:
  // un macrotask sólo corre después de vaciar por completo la cola de
  // microtareas), dejando el scan nativo ya arrancado antes de emitir.
  await flushMicrotasks();
  transport.emitDevice({ id: 'device-1', name: 'B1-AAAA' });
  transport.emitDevice({ id: 'device-2', name: 'PM220-BBBB' });
  await manager.stopScan();
  await scanPromise;

  assert.deepEqual(found, ['device-1', 'device-2']);
});

// AUDITORÍA 2026-09-08 (ronda 2): antes, stopScan() llamaba
// this.ble.stopScan() incondicionalmente. Si la pantalla se desmontaba (o
// el usuario cancelaba) MIENTRAS scan() todavía esperaba el readiness de
// permiso/Bluetooth -- una espera que puede tardar tiempo real, un diálogo
// nativo de Android no resuelve al instante -- no había ningún scan nativo
// corriendo todavía que detener: la cancelación se perdía y, en cuanto el
// readiness finalmente resolvía, scan() arrancaba igual el escaneo nativo
// que quien lo pidió ya había cancelado. Corregido con una sesión de scan
// que stopScan() puede marcar como cancelada antes de que exista algo que
// detener nativamente (ver PrinterManager.scan()/stopScan()).

test('AUDITORÍA (ronda 2): stopScan() durante la ventana de readiness (permiso/Bluetooth aún pendiente) cancela limpiamente -- nunca arranca el scan nativo ni deja la promesa colgada', async () => {
  const transport = new LifecycleAwareFakeTransport();
  let resolvePermission: (granted: boolean) => void = () => {};
  transport.requestPermissions = () => new Promise((resolve) => {
    resolvePermission = resolve;
  });
  const manager = new PrinterManager(transport, {}, inMemoryStore());

  const scanPromise = manager.scan(() => {});
  // requestPermissions() (el primer paso del readiness) todavía no
  // resolvió -- stopScan() llega antes de que exista siquiera un scan
  // nativo que detener.
  await manager.stopScan();
  resolvePermission(true);

  await scanPromise; // nunca debe quedar colgada
  assert.equal(transport.startScanCalls, 0, 'cancelar durante el readiness nunca debe llegar a arrancar el scan nativo');
  assert.equal(transport.listenerCount, 0, 'no debe quedar ningún listener nativo activo tras la cancelación');

  // Un scan posterior debe funcionar con total normalidad -- cancelar
  // durante el readiness no debe dejar al manager en un estado inconsistente.
  transport.requestPermissions = async () => true;
  const secondScan = manager.scan(() => {});
  await flushMicrotasks();
  assert.equal(transport.listenerCount, 1, 'el scan posterior a una cancelación durante readiness debe arrancar con normalidad');
  await manager.stopScan();
  await secondScan;
  assert.equal(transport.listenerCount, 0);
});

test('stopScan() cancela el scan nativo y limpia exactamente una vez -- sin listeners colgados', async () => {
  const transport = new LifecycleAwareFakeTransport();
  const manager = new PrinterManager(transport, {}, inMemoryStore());

  const scanPromise = manager.scan(() => {});
  await flushMicrotasks();
  assert.equal(transport.listenerCount, 1, 'debe haber exactamente un listener activo durante el scan');

  await manager.stopScan();
  await scanPromise;
  assert.equal(transport.listenerCount, 0, 'la limpieza debe liberar el listener');
  assert.equal(transport.stopScanCalls, 1);
});

test('un segundo scan nunca acumula listeners del anterior', async () => {
  const transport = new LifecycleAwareFakeTransport();
  const manager = new PrinterManager(transport, {}, inMemoryStore());

  const first = manager.scan(() => {});
  await manager.stopScan();
  await first;
  assert.equal(transport.listenerCount, 0);

  const second = manager.scan(() => {});
  await flushMicrotasks();
  assert.equal(transport.listenerCount, 1, 'el segundo scan debe partir de cero, nunca sumarse al anterior');
  await manager.stopScan();
  await second;
  assert.equal(transport.listenerCount, 0);
});

test('cancelación explícita (equivalente a desmontar la pantalla) limpia el listener sin dejar la promesa colgada', async () => {
  const transport = new LifecycleAwareFakeTransport();
  const manager = new PrinterManager(transport, {}, inMemoryStore());

  const scanPromise = manager.scan(() => {});
  await manager.stopScan(); // p.ej. la pantalla se desmonta / el usuario cancela
  await scanPromise; // no debe quedar pendiente para siempre
  assert.equal(transport.listenerCount, 0);
});

test('un error del scan nativo también limpia el listener -- nunca lo deja activo tras un fallo', async () => {
  const transport = new LifecycleAwareFakeTransport();
  transport.shouldFailNextScan = true;
  const manager = new PrinterManager(transport, {}, inMemoryStore());

  await assert.rejects(manager.scan(() => {}));
  assert.equal(transport.listenerCount, 0, 'un scan que falla no debe dejar ningún listener activo');
});
