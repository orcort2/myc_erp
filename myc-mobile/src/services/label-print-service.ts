import { todayCivilDate } from '@/src/services/civil-date';
import { BleManagerTransport } from './labels/printers/ble-manager-transport';
import { NelkoPm220Adapter } from './labels/printers/adapters/nelko-pm220/nelko-pm220-adapter';
import { NiimbotB1Adapter } from './labels/printers/adapters/niimbot-b1/niimbot-b1-adapter';
import { clearPreferredPrinter, readPreferredPrinter, writePreferredPrinter } from './labels/printers/preferred-printer-storage';
import { PrinterManager, PrinterNotReadyError } from './labels/printers/printer-manager';
import { MYC_50X30 } from './labels/label-profile';
import { buildLabelLines, renderLabel } from './labels/label-renderer';
import type { LabLabelPayload } from './labels/label-types';

/**
 * Punto único de composición de la impresión de etiquetas LAB -- reemplaza
 * al DisabledLabelPrintService original (ver comentario histórico "Punto
 * único de sustitución futura por el adaptador BLE de NIIMBOT B1", ahora
 * cumplido). Éste es el único archivo del proyecto que conecta las 3
 * capas reales entre sí (BleManagerTransport nativo, los adaptadores
 * concretos, y la persistencia real de impresora preferida) -- por eso
 * mismo es deliberadamente el único sin pruebas unitarias directas (ver
 * docs/architecture/lab-label-printing.md): cada pieza que compone ya está
 * probada por separado con dobles de prueba.
 */

export type { LabLabelPayload, RasterLabel } from './labels/label-types';
export { LabelRenderError } from './labels/label-renderer';
export type { LabelRenderErrorCode } from './labels/label-renderer';
export { MYC_50X30 } from './labels/label-profile';
export {
  BluetoothDisabledError,
  BluetoothPermissionDeniedError,
  PrinterBusyError,
  PrinterNotReadyError,
  PrinterQaUnsupportedError,
  UnknownPrinterAdapterError,
} from './labels/printers/printer-manager';
export { classifyDevice, listKnownPrinterFamilies } from './labels/printers/printer-registry';
export type {
  DeviceClassification,
  PreferredPrinter,
  PrinterAdapterId,
  PrinterDevice,
} from './labels/printers/types';
export { runNelkoDiagnostics } from './labels/printers/adapters/nelko-pm220/nelko-diagnostics';
// SOLO QA/desarrollo -- ver qa-row-header-variant.ts. Herramienta para la
// próxima sesión de QA física del B1, nunca usada por printLabel().
export {
  buildQaBlackBarRaster,
  buildQaPrintJobPackets,
  countBlackPixels,
  type RowHeaderVariant,
} from './labels/printers/adapters/niimbot-b1/qa-row-header-variant';

const bleTransport = new BleManagerTransport();

/** Instancia única del orquestador de impresoras para toda la app -- la
 * pantalla de configuración y el flujo operativo de impresión comparten
 * exactamente este mismo PrinterManager (mismo radio BLE, mismo estado de
 * conexión). */
export const printerManager = new PrinterManager(
  bleTransport,
  {
    'niimbot-b1': (ble) => new NiimbotB1Adapter(ble),
    'nelko-pm220': () => new NelkoPm220Adapter(),
  },
  { read: readPreferredPrinter, write: writePreferredPrinter, clear: clearPreferredPrinter },
);

/** Único punto de impresión operativa real (fuera de la pantalla de
 * configuración): si no hay impresora lista, intenta reconectar la
 * preferida guardada antes de rendirse -- así una reapertura de la app no
 * exige reconfigurar en cada impresión (ver mission section 19). Si sigue
 * sin haber impresora, lanza PrinterNotReadyError -- la UI debe enrutar a
 * la pantalla de configuración, nunca reintentar en silencio ni fallar de
 * forma genérica. */
export async function printLabel(payload: LabLabelPayload, options?: { copies?: number }): Promise<void> {
  // Validar el payload ANTES de tocar BLE -- una impresión que de todas
  // formas va a fallar por datos faltantes (p.ej. sin certificateFolio)
  // nunca debe intentar reconectar la impresora primero. buildLabelLines
  // lanza LabelRenderError aquí mismo si algo requerido falta; el resultado
  // se descarta a propósito, sólo importa que no haya lanzado.
  buildLabelLines(payload);
  if (!printerManager.isReady()) {
    await printerManager.connectPreferred().catch(() => false);
  }
  const capabilities = printerManager.activeCapabilities();
  if (!capabilities) {
    throw new PrinterNotReadyError('No hay una impresora de etiquetas configurada.');
  }
  const raster = renderLabel(payload, MYC_50X30, capabilities.dpi);
  await printerManager.print(raster, options);
}

/** Etiqueta de prueba para la pantalla de configuración (ver mission
 * section 25) -- "PRUEBA MYC" en cada campo dinámico, inconfundible con un
 * folio de certificado real (nunca con formato MYCA-/MYCT-), mientras
 * ejercita exactamente el mismo camino de renderizado/impresión que una
 * etiqueta real. */
export function buildTestPrintPayload(): LabLabelPayload {
  return {
    calibrationDate: todayCivilDate(),
    nextCalibrationDate: null,
    equipmentCode: 'PRUEBA MYC',
    workOrderFolio: 'PRUEBA MYC',
    certificateFolio: 'PRUEBA MYC',
  };
}
