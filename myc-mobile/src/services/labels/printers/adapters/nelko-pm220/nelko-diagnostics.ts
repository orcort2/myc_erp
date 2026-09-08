import type { BleTransport, DeviceInspectionReport } from '../../ble-transport';
import type { PrinterDevice } from '../../types';

/**
 * Herramienta de diagnóstico -- exclusivamente para caracterizar un NELKO
 * PM220 real durante QA física (ver mission section 16). NUNCA envía un
 * comando propio del protocolo NIIMBOT ni ningún byte inventado: sólo
 * conecta, lee lo que el dispositivo ya anuncia/expone (nombre, datos de
 * fabricante, servicios, características y sus propiedades) y se
 * desconecta. Uso exclusivo de desarrollo -- no está pensado para
 * aparecer en la UX operativa normal (ver mission section 16).
 */
export type NelkoDiagnosticReport = DeviceInspectionReport;

export class NelkoDiagnosticsUnavailableError extends Error {}

export async function runNelkoDiagnostics(
  ble: BleTransport,
  device: PrinterDevice,
): Promise<NelkoDiagnosticReport> {
  if (!ble.inspect) {
    throw new NelkoDiagnosticsUnavailableError('Este transporte BLE no implementa inspect().');
  }
  await ble.connect(device.id);
  try {
    await ble.discoverServices(device.id);
    return await ble.inspect(device.id);
  } finally {
    await ble.disconnect(device.id).catch(() => undefined);
  }
}
