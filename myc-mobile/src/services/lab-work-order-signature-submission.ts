import type { SignaturePayload } from '@/src/components/signatures/signature-flow-state';
import type { LabWorkOrder } from '@/src/types/lab-work-order';

type SignatureRequest = <T>(path: string, init?: RequestInit) => Promise<T>;

export function postLabGroupSignatures({
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
    `/mobile/v1/technician/lab-work-orders/${workOrder.id}/signatures`,
    {
      method: 'POST',
      body: JSON.stringify({
        technician: { ...payload.technician, signed_at: signedAt, version: 1 },
        client: { ...payload.client, signed_at: signedAt, version: 1 },
      }),
    },
  );
}
