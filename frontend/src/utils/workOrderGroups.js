function activeWorkOrders(order) {
  const workOrders = Array.isArray(order?.work_orders)
    ? order.work_orders.filter((item) => item.is_active !== false)
    : [];
  if (workOrders.length) {
    return [...workOrders].sort((left, right) => Number(left.sequence || 0) - Number(right.sequence || 0));
  }
  return [{ id: `legacy-${order.id}`, work_order_number: order.work_order_number, status: order.status, isLegacy: true }];
}

export function itemBelongsToWorkOrder(item, workOrder, equipmentById, getItemEquipmentId = (candidate) => candidate.equipment_id) {
  const equipment = equipmentById.get(getItemEquipmentId(item));
  if (!equipment) return false;
  if (!workOrder.isLegacy && equipment.work_order_id != null) {
    return Number(equipment.work_order_id) === Number(workOrder.id);
  }
  return String(equipment.work_order_number ?? '') === String(workOrder.work_order_number ?? '');
}

export function buildWorkOrderGroups({ items, orders, equipmentById, getItemEquipmentId = (item) => item.equipment_id }) {
  return orders.map((order) => {
    const orderItems = items.filter((item) => Number(item.service_order_id) === Number(order.id));
    if (!orderItems.length) return null;
    const workOrders = activeWorkOrders(order)
      .map((workOrder) => ({ workOrder, items: orderItems.filter((item) => itemBelongsToWorkOrder(item, workOrder, equipmentById, getItemEquipmentId)) }))
      .filter((group) => group.items.length);
    const assignedIds = new Set(workOrders.flatMap((group) => group.items.map((item) => item.id)));
    const unassigned = orderItems.filter((item) => !assignedIds.has(item.id));
    if (unassigned.length) {
      workOrders.push({ workOrder: { id: `unassigned-${order.id}`, work_order_number: order.work_order_number, status: order.status }, items: unassigned });
    }
    return { order, workOrders };
  }).filter(Boolean);
}
