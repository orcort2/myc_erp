import { hasPermission } from '@/src/permissions/permissions';

export type LabWorkOrderDeletionResult =
  | { kind: 'success' }
  | { kind: 'forbidden' }
  | { kind: 'not_found' }
  | { kind: 'conflict'; message: string }
  | { kind: 'error'; message: string };

export function canDeleteLabWorkOrder(permissions: string[]): boolean {
  return hasPermission(permissions, 'lab_work_orders.delete');
}

async function responseMessage(response: Response): Promise<string> {
  try {
    const body = await response.json() as { detail?: string | { message?: string } };
    if (typeof body.detail === 'string') return body.detail;
    if (body.detail && typeof body.detail.message === 'string') return body.detail.message;
  } catch {
    // El backend puede responder sin JSON.
  }
  return `Error del servidor (${response.status})`;
}

export async function deleteLabWorkOrder(
  authorizedFetch: (url: string, init?: RequestInit) => Promise<Response>,
  endpoint: string,
): Promise<LabWorkOrderDeletionResult> {
  try {
    const response = await authorizedFetch(endpoint, { method: 'DELETE' });
    if (response.status === 204) return { kind: 'success' };
    if (response.status === 403) return { kind: 'forbidden' };
    if (response.status === 404) return { kind: 'not_found' };
    if (response.status === 409) return { kind: 'conflict', message: await responseMessage(response) };
    return { kind: 'error', message: await responseMessage(response) };
  } catch {
    return { kind: 'error', message: 'No fue posible conectar con el servidor. Intenta nuevamente.' };
  }
}

export class LabWorkOrderDeletionCoordinator {
  private active = false;

  get isDeleting(): boolean {
    return this.active;
  }

  async run(
    confirmed: boolean,
    request: () => Promise<LabWorkOrderDeletionResult>,
  ): Promise<LabWorkOrderDeletionResult | { kind: 'cancelled' } | { kind: 'ignored' }> {
    if (!confirmed) return { kind: 'cancelled' };
    if (this.active) return { kind: 'ignored' };
    this.active = true;
    try {
      return await request();
    } finally {
      this.active = false;
    }
  }
}
