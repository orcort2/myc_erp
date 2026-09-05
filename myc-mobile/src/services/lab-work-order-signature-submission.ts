import type { SignaturePayload } from '@/src/components/signatures/signature-flow-state';
import type { EquipmentByEquipmentPrevalidation } from '@/src/services/lab-equipment-by-equipment-flow';
import type { LabClosureScope } from '@/src/services/lab-work-order-closure';
import type { LabWorkOrder, LabWorkOrderWorkflowMode } from '@/src/types/lab-work-order';

type SignatureRequest = <T>(path: string, init?: RequestInit) => Promise<T>;

export function postLabSignatures({
  payload,
  request,
  scope,
  signedAt,
  workOrder,
}: {
  payload: SignaturePayload;
  request: SignatureRequest;
  scope: LabClosureScope;
  signedAt: string;
  workOrder: LabWorkOrder;
}): Promise<LabWorkOrder> {
  const suffix = scope === 'individual' ? '/signatures/individual' : '/signatures';
  return request<LabWorkOrder>(
    `/mobile/v1/technician/lab-work-orders/${workOrder.id}${suffix}`,
    {
      method: 'POST',
      body: JSON.stringify({
        technician: { ...payload.technician, signed_at: signedAt, version: 1 },
        client: { ...payload.client, signed_at: signedAt, version: 1 },
      }),
    },
  );
}

export function postLabGroupSignatures(
  options: Omit<Parameters<typeof postLabSignatures>[0], 'scope'>,
): Promise<LabWorkOrder> {
  return postLabSignatures({ ...options, scope: 'group' });
}

/** Sección 14 del encargo equipo-por-equipo: sólo lectura, nunca muta nada.
 * Se llama ANTES de abrir la pantalla de firma de "Finalizar registro de
 * equipos". */
export function getLabEquipmentByEquipmentPrevalidation({
  request,
  workOrder,
}: {
  request: SignatureRequest;
  workOrder: LabWorkOrder;
}): Promise<EquipmentByEquipmentPrevalidation> {
  return request<EquipmentByEquipmentPrevalidation>(
    `/mobile/v1/technician/lab-work-orders/${workOrder.id}/equipment-by-equipment/prevalidate`,
  );
}

/** Misma firma que postLabSignatures, pero apunta a la operación atómica
 * única (firma + completar hojas + cerrar OT + entrega FULL) -- nunca al
 * endpoint de recepción group/individual. */
export function postLabEquipmentByEquipmentFinalize({
  payload,
  request,
  signedAt,
  workOrder,
}: {
  payload: SignaturePayload;
  request: SignatureRequest;
  signedAt: string;
  workOrder: LabWorkOrder;
}): Promise<LabWorkOrder> {
  return request<LabWorkOrder>(
    `/mobile/v1/technician/lab-work-orders/${workOrder.id}/equipment-by-equipment/finalize`,
    {
      method: 'POST',
      body: JSON.stringify({
        technician: { ...payload.technician, signed_at: signedAt, version: 1 },
        client: { ...payload.client, signed_at: signedAt, version: 1 },
        expected_edit_version: workOrder.edit_version,
      }),
    },
  );
}

/** Cierre "grupos mixtos": prevalida el scope grupal completo -- puede
 * mezclar miembros 'group'/'equipment_by_equipment', cada uno validado según
 * su propia modalidad. Sólo lectura, se llama ANTES de abrir la firma. */
export function getLabSignatureGroupPrevalidation({
  request,
  workOrder,
}: {
  request: SignatureRequest;
  workOrder: LabWorkOrder;
}): Promise<EquipmentByEquipmentPrevalidation> {
  return request<EquipmentByEquipmentPrevalidation>(
    `/mobile/v1/technician/lab-work-orders/${workOrder.id}/signature-group/prevalidate`,
  );
}

/** Firma grupal única que puede mezclar miembros 'group' y
 * 'equipment_by_equipment' -- cada uno avanza según su propia modalidad
 * (backend decide el efecto real por OT, nunca Mobile). Se firma UNA sola
 * vez -- nunca abrir MobileSignatureFlow ni enviar firmas por segunda vez. */
export function postLabSignatureGroupFinalize({
  payload,
  request,
  signedAt,
  workOrder,
}: {
  payload: SignaturePayload;
  request: SignatureRequest;
  signedAt: string;
  workOrder: LabWorkOrder;
}): Promise<LabWorkOrder> {
  return request<LabWorkOrder>(
    `/mobile/v1/technician/lab-work-orders/${workOrder.id}/signature-group/finalize`,
    {
      method: 'POST',
      body: JSON.stringify({
        technician: { ...payload.technician, signed_at: signedAt, version: 1 },
        client: { ...payload.client, signed_at: signedAt, version: 1 },
        expected_edit_version: workOrder.edit_version,
      }),
    },
  );
}

/** Acción administrativa "Cambiar modalidad de trabajo" -- nunca confundir
 * con service_type. Backend es la única autoridad (permiso interno +
 * motivo obligatorio + guard de pre-firma); este wrapper no valida nada por
 * su cuenta. */
export function postLabWorkOrderWorkflowModeChange({
  newWorkflowMode,
  reason,
  request,
  workOrder,
}: {
  newWorkflowMode: LabWorkOrderWorkflowMode;
  reason: string;
  request: SignatureRequest;
  workOrder: LabWorkOrder;
}): Promise<LabWorkOrder> {
  return request<LabWorkOrder>(
    `/mobile/v1/technician/lab-work-orders/${workOrder.id}/workflow-mode`,
    {
      method: 'POST',
      body: JSON.stringify({ new_workflow_mode: newWorkflowMode, reason }),
    },
  );
}

export function postLabCompletion({
  confirmDraftCompletion,
  request,
  scope,
  workOrder,
}: {
  confirmDraftCompletion?: boolean;
  request: SignatureRequest;
  scope: LabClosureScope;
  workOrder: LabWorkOrder;
}): Promise<LabWorkOrder> {
  const suffix = scope === 'individual' ? '/complete/individual' : '/complete';
  const query = confirmDraftCompletion ? '?confirm_draft_completion=true' : '';
  return request<LabWorkOrder>(
    `/mobile/v1/technician/lab-work-orders/${workOrder.id}${suffix}${query}`,
    { method: 'POST' },
  );
}
