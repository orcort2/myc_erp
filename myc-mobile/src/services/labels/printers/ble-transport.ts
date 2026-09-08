/**
 * Abstracción de transporte BLE genérica -- ningún adaptador de impresora
 * (NIIMBOT, NELKO, el que siga) importa react-native-ble-manager
 * directamente. Programan exclusivamente contra esta interfaz, inyectada
 * por quien los construye (ver printer-manager.ts). Esto es lo que permite
 * probar el protocolo/orquestación de cada adaptador con un transporte de
 * prueba en Node, sin ningún módulo nativo -- ver
 * niimbot-b1-adapter.test.ts.
 *
 * Sólo tipos puros en este archivo (sin `import ... from 'react-native'` ni
 * de 'react-native-ble-manager'): la implementación real vive en
 * ble-manager-transport.ts, deliberadamente separada para que ésta pueda
 * importarse desde un test de Node sin arrastrar módulos nativos, mismo
 * patrón que push-notification-policy.ts/push-notifications.ts en este
 * mismo proyecto.
 */

export type BleTransportDevice = {
  id: string;
  name: string | null;
  rssi?: number;
  advertisedServiceUUIDs?: string[];
  manufacturerData?: string | null;
};

export type BleNotificationHandler = (data: Uint8Array) => void;
export type Unsubscribe = () => void;

export type InspectedCharacteristic = {
  uuid: string;
  properties: string[];
};

export type InspectedService = {
  uuid: string;
  characteristics: InspectedCharacteristic[];
};

/** Snapshot crudo de lo que anuncia/expone un periférico BLE -- usado
 * exclusivamente por el diagnóstico NELKO (ver
 * adapters/nelko-pm220/nelko-diagnostics.ts), nunca por un adaptador de
 * impresora real. Nunca envía comandos: sólo lee lo que el propio
 * dispositivo ya expone. */
export type DeviceInspectionReport = {
  deviceId: string;
  advertisedName: string | null;
  manufacturerData: string | null;
  advertisedServiceUUIDs: string[];
  services: InspectedService[];
};

export interface BleTransport {
  isBluetoothOn(): Promise<boolean>;
  /** Pide los permisos de runtime necesarios (Android 12+ BLUETOOTH_SCAN/
   * BLUETOOTH_CONNECT, o ubicación en versiones anteriores) -- true si
   * quedaron concedidos. */
  requestPermissions(): Promise<boolean>;
  startScan(onDeviceFound: (device: BleTransportDevice) => void, timeoutMs: number): Promise<void>;
  stopScan(): Promise<void>;
  connect(deviceId: string): Promise<void>;
  disconnect(deviceId: string): Promise<void>;
  isConnected(deviceId: string): Promise<boolean>;
  /** Descubre servicios/características del periférico -- debe llamarse
   * antes de notify/write en la mayoría de las plataformas. */
  discoverServices(deviceId: string): Promise<void>;
  subscribeNotifications(
    deviceId: string,
    serviceUUID: string,
    characteristicUUID: string,
    onData: BleNotificationHandler,
  ): Promise<Unsubscribe>;
  writeWithoutResponse(
    deviceId: string,
    serviceUUID: string,
    characteristicUUID: string,
    data: Uint8Array,
  ): Promise<void>;
  onDisconnected(deviceId: string, callback: () => void): Unsubscribe;
  /** Opcional: no todo transporte de prueba necesita implementarlo -- sólo
   * lo usa el diagnóstico NELKO. La implementación real
   * (ble-manager-transport.ts) sí lo provee vía retrieveServices(). */
  inspect?(deviceId: string): Promise<DeviceInspectionReport>;
}
