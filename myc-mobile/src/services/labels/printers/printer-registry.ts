import type { DeviceClassification, DiscoveredDevice, PrinterFamilyDescriptor } from './types';

/**
 * Catálogo central de familias de impresora conocidas. Distingue "impresora
 * soportada" de "impresora reconocida pero sin soporte" de "dispositivo BLE
 * cualquiera (audífonos, reloj, etc.)" -- la UI nunca debe ofrecer un
 * dispositivo ajeno como si fuera una impresora de etiquetas compatible.
 *
 * La clasificación hoy es por prefijo de nombre anunciado (NIIMBOT/NELKO
 * publican su marca en el nombre BLE, ver referencias del protocolo en
 * niimbot-b1/protocol.ts) -- es deliberadamente conservadora: si no hay
 * nombre o no coincide con ningún patrón conocido, el dispositivo se
 * reporta `unknown`, nunca se asume una familia por descarte.
 */

const FAMILIES: PrinterFamilyDescriptor[] = [
  {
    adapterId: 'niimbot-b1',
    displayName: 'NIIMBOT B1',
    modelHint: 'B1',
    supportStatus: 'supported',
  },
  {
    adapterId: 'nelko-pm220',
    displayName: 'NELKO PM220',
    modelHint: 'PM220',
    supportStatus: 'protocol_pending',
  },
];

const NAME_MATCHERS: Record<string, RegExp> = {
  'niimbot-b1': /^(niimbot[_\s-]?)?b1\b/i,
  'nelko-pm220': /^(nelko[_\s-]?)?pm[_\s-]?220\b/i,
};

export function listKnownPrinterFamilies(): PrinterFamilyDescriptor[] {
  return FAMILIES;
}

export function familyFor(adapterId: string): PrinterFamilyDescriptor | undefined {
  return FAMILIES.find((family) => family.adapterId === adapterId);
}

/** Clasifica un dispositivo BLE descubierto contra el catálogo. Nunca
 * clasifica por descarte ("no es NIIMBOT, debe ser NELKO"): cada familia
 * exige su propio patrón positivo. */
export function classifyDevice(device: DiscoveredDevice): DeviceClassification {
  const name = (device.name ?? '').trim();
  if (name) {
    for (const family of FAMILIES) {
      const matcher = NAME_MATCHERS[family.adapterId];
      if (matcher?.test(name)) return { kind: 'recognized', family, device };
    }
  }
  return { kind: 'unknown', device };
}
