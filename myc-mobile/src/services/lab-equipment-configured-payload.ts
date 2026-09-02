import type { LabEquipment } from '@/src/types/lab-work-order';

export type EquipmentBasicData = {
  instrument: string;
  brand: string;
  // Fase 6: identidad del equipo (mismo criterio que Equipment productivo) --
  // opcionales, igual que en el backend (no todo instrumento trae modelo o
  // alcance documentado).
  model: string | null;
  range_or_capacity: string | null;
  identification: string;
  serial_number: string;
  report_number: string | null;
  is_good_condition: boolean;
};

export type DocumentaryClientMode = 'order' | 'different';

export type DocumentaryClientSelection = {
  mode: DocumentaryClientMode;
  finalLabClientId: number | null;
  finalClientCompany: string | null;
  finalClientAddress: string | null;
  finalClientAttention: string | null;
};

export type LabServiceType = 'accredited' | 'traceable' | 'linked';

export type ServiceSelection = {
  serviceType: LabServiceType;
  linkedCompanyId: number | null;
};

/** Default documentary client: "Mismo cliente de la OT" (certificate_client_mode='order').
 * No snapshot fields are populated here -- Fase 1's invariant requires them to
 * stay null in 'order' mode, so there is nothing to copy from the OT client. */
export function defaultDocumentaryClient(): DocumentaryClientSelection {
  return {
    mode: 'order',
    finalLabClientId: null,
    finalClientCompany: null,
    finalClientAddress: null,
    finalClientAttention: null,
  };
}

/** Selecting/creating a final LabClient always freezes company/address/attention
 * as of right now -- never a bare id the backend would have to re-resolve. */
export function selectFinalClient(client: {
  id: number;
  company: string;
  address: string;
  attention: string;
}): DocumentaryClientSelection {
  return {
    mode: 'different',
    finalLabClientId: client.id,
    finalClientCompany: client.company,
    finalClientAddress: client.address || null,
    finalClientAttention: client.attention || null,
  };
}

/** Vinculado requires an explicit LinkedCompany selection; Acreditado/Trazable never take one. */
export function validateServiceSelection(service: ServiceSelection): string | null {
  if (service.serviceType === 'linked' && service.linkedCompanyId == null) {
    return 'Selecciona la empresa vinculada';
  }
  return null;
}

export type CertificateClientPayload = {
  certificate_client_mode: DocumentaryClientMode;
  final_lab_client_id: number | null;
  final_client_company_snapshot: string | null;
  final_client_address_snapshot: string | null;
  final_client_attention_snapshot: string | null;
};

/**
 * Builds the LabEquipmentCertificateClientWrite body shared by the integrated
 * create payload and the standalone PATCH .../certificate-client endpoint.
 *
 * Security hardening: when finalLabClientId is set, company/address/attention
 * are sent as null -- the backend is the ONLY authority for those values once
 * a LabClient id is known (_set_equipment_certificate_client_core always
 * re-resolves them from that LabClient and ignores whatever the payload
 * says). Mobile's local finalClientCompany/Address/Attention exist purely
 * for presentation/optimistic UI; they are never trusted as the persisted
 * snapshot when a catalog reference exists. They are only sent as-is for the
 * rare no-catalog-reference case (finalLabClientId absent).
 */
export function buildCertificateClientPayload(
  documentaryClient: DocumentaryClientSelection,
): CertificateClientPayload {
  if (documentaryClient.mode === 'order') {
    return {
      certificate_client_mode: 'order',
      final_lab_client_id: null,
      final_client_company_snapshot: null,
      final_client_address_snapshot: null,
      final_client_attention_snapshot: null,
    };
  }
  const hasCatalogReference = documentaryClient.finalLabClientId != null;
  return {
    certificate_client_mode: 'different',
    final_lab_client_id: documentaryClient.finalLabClientId,
    final_client_company_snapshot: hasCatalogReference ? null : documentaryClient.finalClientCompany,
    final_client_address_snapshot: hasCatalogReference ? null : documentaryClient.finalClientAddress,
    final_client_attention_snapshot: hasCatalogReference ? null : documentaryClient.finalClientAttention,
  };
}

export type ConfiguredEquipmentPayload = {
  equipment: EquipmentBasicData;
  certificate_client?: CertificateClientPayload;
  service: { service_type: LabServiceType; linked_company_id: number | null };
};

/** Builds the exact POST .../equipment/configured body. 'order' mode omits
 * certificate_client entirely (backend defaults to order with null snapshots,
 * matching Fase 1's invariant -- nothing is copied needlessly). */
export function buildConfiguredEquipmentPayload(
  equipment: EquipmentBasicData,
  documentaryClient: DocumentaryClientSelection,
  service: ServiceSelection,
): ConfiguredEquipmentPayload {
  const payload: ConfiguredEquipmentPayload = {
    equipment,
    service: {
      service_type: service.serviceType,
      linked_company_id: service.serviceType === 'linked' ? service.linkedCompanyId : null,
    },
  };
  if (documentaryClient.mode === 'different') {
    payload.certificate_client = buildCertificateClientPayload(documentaryClient);
  }
  return payload;
}

export type EquipmentFormValues = {
  equipment: EquipmentBasicData;
  documentaryClient: DocumentaryClientSelection;
  service: ServiceSelection;
};

/** Fase 2 hardening: hidrata el formulario desde un equipo ya guardado (modo
 * edición). Los snapshots que se muestran vienen de lo ya persistido -- son
 * lectura, no una nueva autoridad; cualquier cambio real vuelve a pasar por
 * buildCertificateClientPayload/el backend. */
export function hydrateEquipmentFormValues(equipment: LabEquipment): EquipmentFormValues {
  return {
    equipment: {
      instrument: equipment.instrument,
      brand: equipment.brand,
      model: equipment.model,
      range_or_capacity: equipment.range_or_capacity,
      identification: equipment.identification,
      serial_number: equipment.serial_number,
      report_number: equipment.report_number,
      is_good_condition: equipment.is_good_condition,
    },
    documentaryClient: equipment.certificate_client_mode === 'different'
      ? {
        mode: 'different',
        finalLabClientId: equipment.final_lab_client_id,
        finalClientCompany: equipment.final_client_company_snapshot,
        finalClientAddress: equipment.final_client_address_snapshot,
        finalClientAttention: equipment.final_client_attention_snapshot,
      }
      : defaultDocumentaryClient(),
    service: {
      serviceType: equipment.service_type ?? 'accredited',
      linkedCompanyId: equipment.linked_company_id,
    },
  };
}

export type EquipmentEditChanges = {
  equipmentChanged: boolean;
  certificateClientChanged: boolean;
  serviceChanged: boolean;
};

/** Fase 2 hardening (endurecimiento de consistencia): el diff ya NO decide a
 * qué endpoint(s) llamar -- la edición es una sola transacción backend (PATCH
 * .../equipment/{id}/configured), igual que el alta (Fase 2E). El diff sólo
 * sirve para decidir si vale la pena hacer la llamada (ver
 * hasEquipmentEditChanges): si algo cambió, se manda la configuración
 * completa y el backend aplica o revierte todo junto. */
export function diffEquipmentEdit(
  initial: EquipmentFormValues,
  current: EquipmentFormValues,
): EquipmentEditChanges {
  return {
    equipmentChanged: JSON.stringify(initial.equipment) !== JSON.stringify(current.equipment),
    certificateClientChanged: initial.documentaryClient.mode !== current.documentaryClient.mode
      || initial.documentaryClient.finalLabClientId !== current.documentaryClient.finalLabClientId
      || (current.documentaryClient.mode === 'different'
        && initial.documentaryClient.finalLabClientId == null
        && initial.documentaryClient.finalClientCompany !== current.documentaryClient.finalClientCompany),
    serviceChanged: initial.service.serviceType !== current.service.serviceType
      || initial.service.linkedCompanyId !== current.service.linkedCompanyId,
  };
}

/** True when at least one of the three sections actually changed -- the only
 * case where the single integrated edit call is worth making. A no-op edit
 * (nothing changed) must never reach the network. */
export function hasEquipmentEditChanges(changes: EquipmentEditChanges): boolean {
  return changes.equipmentChanged || changes.certificateClientChanged || changes.serviceChanged;
}

/** Builds the exact PATCH .../equipment/{id}/configured body for editing an
 * existing equipment: the same full configuration payload as the create flow
 * (buildConfiguredEquipmentPayload), plus expected_edit_version for optimistic
 * concurrency. There is deliberately only one shape here -- edition sends the
 * full configuration in a single call, never partial per-field patches. */
export function buildEquipmentEditRequestBody(
  values: EquipmentFormValues,
  expectedEditVersion: number,
): ConfiguredEquipmentPayload & { equipment: EquipmentBasicData & { expected_edit_version: number } } {
  const payload = buildConfiguredEquipmentPayload(values.equipment, values.documentaryClient, values.service);
  return { ...payload, equipment: { ...payload.equipment, expected_edit_version: expectedEditVersion } };
}

const SERVICE_LABELS: Record<LabServiceType, string> = {
  accredited: 'ACREDITADO',
  traceable: 'TRAZABLE',
  linked: 'VINCULADO',
};

export type EquipmentSummary = {
  client: string;
  service: string;
  linkedCompany: string | null;
  folio: string;
};

/** Compact, ID-free summary for an already-saved equipment row (Fase 2I). */
export function describeEquipmentSummary(
  equipment: Pick<
    LabEquipment,
    | 'certificate_client_mode'
    | 'final_client_company_snapshot'
    | 'service_type'
    | 'linked_company_name_snapshot'
    | 'certificate_folio'
    | 'folio_status'
  >,
  workOrderClientName: string,
): EquipmentSummary {
  const client = equipment.certificate_client_mode === 'different'
    ? (equipment.final_client_company_snapshot || '-')
    : workOrderClientName;
  const service = equipment.service_type ? SERVICE_LABELS[equipment.service_type] : 'Sin asignar';
  const linkedCompany = equipment.service_type === 'linked'
    ? (equipment.linked_company_name_snapshot || 'Pendiente')
    : null;
  const folio = equipment.certificate_folio
    ?? (equipment.folio_status === 'pending' || equipment.folio_status === 'unassigned' ? 'Pendiente' : '-');
  return { client, service, linkedCompany, folio };
}
