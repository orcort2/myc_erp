import type { GeneralData, LabClient } from '@/src/types/lab-work-order';

/**
 * Única autoridad del mapeo cliente → Datos generales de la OT LAB.
 *
 * Los campos derivados del cliente representan exclusivamente al cliente
 * elegido: si el nuevo cliente no trae un dato, queda vacío -- nunca se
 * conserva el del cliente anterior (evita OT híbridas A/B). `address` y
 * `attention` son `str` no nulos en el contrato (default ""); `postal_code`,
 * `city` y `state` son opcionales (`null` → ""). El resto de GeneralData
 * (fecha, teléfono, correo, OC, notas) no deriva del cliente y se conserva.
 */
export function generalWithLabClient(current: GeneralData, client: LabClient): GeneralData {
  return {
    ...current,
    lab_client_id: client.id,
    client_name: client.company,
    address: client.address,
    contact_name: client.attention,
    postal_code: client.postal_code ?? '',
    city: client.city ?? '',
    state_name: client.state ?? '',
  };
}
