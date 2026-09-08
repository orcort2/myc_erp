import type { RasterLabel } from '../../../label-types';
import type { LabelPrinterAdapter, PrintOptions, PrinterCapabilities, PrinterDevice } from '../../types';

/**
 * NELKO PM220 -- reconocida por nombre (ver printer-registry.ts) pero SIN
 * protocolo BLE confiable confirmado todavía (ver mission section 15: no
 * existe un SDK/protocolo público de confianza). Este adaptador existe
 * únicamente para que la arquitectura tenga un segundo miembro real de
 * PrinterAdapterId -- connect()/print() rechazan explícitamente en vez de
 * intentar hablar un protocolo inventado, reutilizar comandos NIIMBOT, o
 * escribir bytes arbitrarios al dispositivo.
 *
 * NUNCA reportar esta impresora como soportada hasta que:
 * 1. se obtenga documentación/SDK confiable del protocolo PM220, o
 * 2. se caracterice su servicio/característica BLE real vía
 *    nelko-diagnostics.ts durante QA física, Y
 * 3. pase su propia matriz de QA física (ver mission section 15/29) --
 *    igual que NIIMBOT B1, nunca antes.
 */
export class NelkoProtocolPendingError extends Error {}

export class NelkoPm220Adapter implements LabelPrinterAdapter {
  readonly id = 'nelko-pm220' as const;
  readonly displayName = 'NELKO PM220';
  readonly transport = 'ble' as const;
  // dpi/printableWidthPx son las especificaciones públicas del producto
  // (ficha técnica), NO capacidades verificadas por protocolo -- no se usan
  // para imprimir todavía, sólo declaran el hardware conocido.
  readonly capabilities: PrinterCapabilities = { dpi: 203, printableWidthPx: 384 };

  isConnected(): boolean {
    return false;
  }

  async connect(_device: PrinterDevice): Promise<void> {
    throw new NelkoProtocolPendingError(
      'NELKO PM220 aún no tiene protocolo de impresión confirmado -- usa el diagnóstico (nelko-diagnostics.ts) durante QA física, no una conexión de impresión real.',
    );
  }

  async disconnect(): Promise<void> {
    // No hay nada que desconectar: connect() nunca llega a establecer sesión.
  }

  async print(_label: RasterLabel, _options?: PrintOptions): Promise<void> {
    throw new NelkoProtocolPendingError(
      'NELKO PM220 aún no tiene protocolo de impresión confirmado; no se envía ningún byte al dispositivo.',
    );
  }
}
