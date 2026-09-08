import { Platform } from 'react-native';
import BleManager from 'react-native-ble-manager';

import type {
  BleNotificationHandler,
  BleTransport,
  BleTransportDevice,
  DeviceInspectionReport,
  Unsubscribe,
} from './ble-transport';

/**
 * Implementación real de BleTransport sobre react-native-ble-manager v12.x
 * (Apache-2.0, soporte explícito de New Architecture para RN 0.76+ -- ver
 * docs/architecture/lab-label-printing.md, sección "Decisión de librería
 * BLE", para por qué se descartó react-native-ble-plx). Deliberadamente
 * SIN pruebas unitarias directas (importa el módulo nativo real): la
 * cobertura de este archivo es la QA física de la Fase 29 de la misión, no
 * un test de Node. Toda la orquestación de protocolo que SÍ es testeable
 * vive en niimbot-b1-adapter.ts, que sólo depende de la interfaz
 * BleTransport, nunca de este archivo.
 *
 * maxByteSize=20/queueSleepTime=10 en writeWithoutResponse: 20 bytes es el
 * payload ATT seguro sin negociar MTU (23 bytes de MTU por defecto - 3 de
 * cabecera ATT); 10ms es el espaciado que la propia librería ya trae por
 * defecto y que coincide con el "~10ms" que documentan las referencias
 * NIIMBOT auditadas (ver protocol.ts) para no perder filas por escribir
 * demasiado rápido. Un solo paquete NIIMBOT más largo que 20 bytes (p.ej.
 * una fila de raster) se parte automáticamente en varias escrituras BLE
 * consecutivas -- el firmware NIIMBOT reensambla por stream de bytes, no
 * por escritura, así que esto es equivalente a concatenar frames, no un
 * riesgo nuevo.
 */
const WRITE_CHUNK_BYTES = 20;
const WRITE_PACING_MS = 10;
let started = false;

/** React Native/Hermes no trae `Buffer` global (no hay polyfill instalado
 * en este proyecto) -- helper propio en vez de depender de la API de Node. */
function bytesToHex(bytes: number[]): string {
  return bytes.map((byte) => byte.toString(16).padStart(2, '0')).join('');
}

async function ensureStarted(): Promise<void> {
  if (started) return;
  await BleManager.start({ showAlert: false });
  started = true;
}

export class BleManagerTransport implements BleTransport {
  async isBluetoothOn(): Promise<boolean> {
    await ensureStarted();
    const state = await BleManager.checkState();
    return state === 'on';
  }

  async requestPermissions(): Promise<boolean> {
    // Android 12+ pide BLUETOOTH_SCAN/BLUETOOTH_CONNECT como permisos de
    // runtime; react-native-ble-manager no los solicita por sí solo (a
    // diferencia del manifest, que su plugin de Expo sí declara -- ver
    // app.json). En versiones más viejas de Android, BLE de por sí exige
    // ubicación; iOS resuelve el permiso Bluetooth vía el propio diálogo de
    // sistema al primer uso, sin una llamada explícita equivalente.
    if (Platform.OS !== 'android') return true;
    const { PermissionsAndroid } = await import('react-native');
    if (Platform.Version >= 31) {
      const results = await PermissionsAndroid.requestMultiple([
        PermissionsAndroid.PERMISSIONS.BLUETOOTH_SCAN,
        PermissionsAndroid.PERMISSIONS.BLUETOOTH_CONNECT,
      ]);
      return Object.values(results).every((result) => result === PermissionsAndroid.RESULTS.GRANTED);
    }
    const granted = await PermissionsAndroid.request(PermissionsAndroid.PERMISSIONS.ACCESS_FINE_LOCATION);
    return granted === PermissionsAndroid.RESULTS.GRANTED;
  }

  async startScan(onDeviceFound: (device: BleTransportDevice) => void, timeoutMs: number): Promise<void> {
    await ensureStarted();
    const subscription = BleManager.onDiscoverPeripheral((peripheral) => {
      onDeviceFound({
        id: peripheral.id,
        name: peripheral.name ?? peripheral.advertising?.localName ?? null,
        rssi: peripheral.rssi,
        advertisedServiceUUIDs: peripheral.advertising?.serviceUUIDs,
      });
    });
    this.scanSubscription = subscription;
    await BleManager.scan({ seconds: Math.max(1, Math.round(timeoutMs / 1000)) });
  }

  private scanSubscription: { remove(): void } | null = null;

  async stopScan(): Promise<void> {
    await BleManager.stopScan();
    this.scanSubscription?.remove();
    this.scanSubscription = null;
  }

  async connect(deviceId: string): Promise<void> {
    await ensureStarted();
    await BleManager.connect(deviceId);
  }

  async disconnect(deviceId: string): Promise<void> {
    await BleManager.disconnect(deviceId);
  }

  async isConnected(deviceId: string): Promise<boolean> {
    return BleManager.isPeripheralConnected(deviceId);
  }

  async discoverServices(deviceId: string): Promise<void> {
    await BleManager.retrieveServices(deviceId);
  }

  async subscribeNotifications(
    deviceId: string,
    serviceUUID: string,
    characteristicUUID: string,
    onData: BleNotificationHandler,
  ): Promise<Unsubscribe> {
    await BleManager.startNotification(deviceId, serviceUUID, characteristicUUID);
    const subscription = BleManager.onDidUpdateValueForCharacteristic((event) => {
      if (event.peripheral !== deviceId || event.characteristic.toLowerCase() !== characteristicUUID.toLowerCase()) {
        return;
      }
      onData(Uint8Array.from(event.value));
    });
    return () => {
      subscription.remove();
      BleManager.stopNotification(deviceId, serviceUUID, characteristicUUID).catch(() => undefined);
    };
  }

  async writeWithoutResponse(
    deviceId: string,
    serviceUUID: string,
    characteristicUUID: string,
    data: Uint8Array,
  ): Promise<void> {
    await BleManager.writeWithoutResponse(
      deviceId,
      serviceUUID,
      characteristicUUID,
      Array.from(data),
      WRITE_CHUNK_BYTES,
      WRITE_PACING_MS,
    );
  }

  onDisconnected(deviceId: string, callback: () => void): Unsubscribe {
    const subscription = BleManager.onDisconnectPeripheral((event) => {
      if (event.peripheral === deviceId) callback();
    });
    return () => subscription.remove();
  }

  /** Diagnóstico NELKO (ver adapters/nelko-pm220/nelko-diagnostics.ts) --
   * sólo lee lo que el periférico ya expone (servicios, características,
   * propiedades soportadas), nunca envía un comando propio del protocolo. */
  async inspect(deviceId: string): Promise<DeviceInspectionReport> {
    const info = await BleManager.retrieveServices(deviceId);
    const byService = new Map<string, { uuid: string; properties: string[] }[]>();
    for (const characteristic of info.characteristics ?? []) {
      const list = byService.get(characteristic.service) ?? [];
      list.push({ uuid: characteristic.characteristic, properties: Object.keys(characteristic.properties) });
      byService.set(characteristic.service, list);
    }
    const services = (info.services ?? []).map((service) => ({
      uuid: service.uuid,
      characteristics: byService.get(service.uuid) ?? [],
    }));
    return {
      deviceId,
      advertisedName: info.name ?? info.advertising?.localName ?? null,
      manufacturerData: info.advertising?.manufacturerRawData?.bytes
        ? bytesToHex(info.advertising.manufacturerRawData.bytes)
        : null,
      advertisedServiceUUIDs: info.advertising?.serviceUUIDs ?? [],
      services,
    };
  }
}
