import * as SecureStore from 'expo-secure-store';

import type { PreferredPrinter } from './types';

/**
 * Persistencia de la impresora de etiquetas preferida del dispositivo --
 * mismo patrón/convención ya establecido por src/storage/secure-storage.ts
 * (expo-secure-store, clave "myc.internal.<dominio>.v1", JSON.stringify).
 * No se introduce AsyncStorage ni ninguna otra librería de persistencia: no
 * existe otra en el proyecto (ver auditoría previa a este cambio).
 *
 * Esto es configuración LOCAL DEL DISPOSITIVO (qué impresora física está
 * emparejada en este teléfono/tablet), no un recurso de negocio del backend
 * -- no requiere permiso LAB ni sincroniza entre dispositivos, igual que
 * ninguna otra preferencia puramente local de la app hoy.
 */

const PREFERRED_PRINTER_KEY = 'myc.internal.label-printer.v1';

export async function readPreferredPrinter(): Promise<PreferredPrinter | null> {
  const stored = await SecureStore.getItemAsync(PREFERRED_PRINTER_KEY);
  if (!stored) return null;
  try {
    return JSON.parse(stored) as PreferredPrinter;
  } catch {
    await SecureStore.deleteItemAsync(PREFERRED_PRINTER_KEY);
    return null;
  }
}

export async function writePreferredPrinter(printer: PreferredPrinter): Promise<void> {
  await SecureStore.setItemAsync(PREFERRED_PRINTER_KEY, JSON.stringify(printer));
}

export async function clearPreferredPrinter(): Promise<void> {
  await SecureStore.deleteItemAsync(PREFERRED_PRINTER_KEY);
}
