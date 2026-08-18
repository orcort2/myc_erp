import { hasPermission } from './accessControl.js';

export const WORK_ORDER_DELETE_PERMISSION = 'service_orders.delete';

export function canDeleteWorkOrder(user) {
  return hasPermission(user, WORK_ORDER_DELETE_PERMISSION);
}
