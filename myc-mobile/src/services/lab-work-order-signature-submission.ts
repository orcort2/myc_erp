import type { SignaturePayload } from '@/src/components/signatures/signature-flow-state';
import type { LabClosureScope } from '@/src/services/lab-work-order-closure';
import type { LabWorkOrder } from '@/src/types/lab-work-order';

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

export function postLabCompletion({
  request,
  scope,
  workOrder,
}: {
  request: SignatureRequest;
  scope: LabClosureScope;
  workOrder: LabWorkOrder;
}): Promise<LabWorkOrder> {
  const suffix = scope === 'individual' ? '/complete/individual' : '/complete';
  return request<LabWorkOrder>(
    `/mobile/v1/technician/lab-work-orders/${workOrder.id}${suffix}`,
    { method: 'POST' },
  );
}
