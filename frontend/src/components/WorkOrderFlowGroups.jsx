import React from 'react';
import { buildWorkOrderGroups } from '../utils/workOrderGroups.js';

export default function WorkOrderFlowGroups({
  emptyMessage,
  equipmentById,
  getGroupState,
  getItemEquipmentId = (item) => item.equipment_id,
  items,
  orders,
  renderItem
}) {
  const groups = buildWorkOrderGroups({ items, orders, equipmentById, getItemEquipmentId });

  if (!groups.length) return <div className="clients-empty">{emptyMessage}</div>;

  return (
    <div className="flow-ets-groups">
      {groups.map(({ order, workOrders }) => (
        <section className="flow-ets-group" key={order.id}>
          <header className="flow-ets-group__header">
            <div><span>ETS</span><h3>{order.folio}</h3></div>
            <small>{workOrders.length} {workOrders.length === 1 ? 'Orden de Trabajo' : 'Órdenes de Trabajo'}</small>
          </header>
          <div className="flow-work-order-groups">
            {workOrders.map(({ workOrder, items: workOrderItems }) => {
              const groupState = getGroupState?.(workOrderItems, order, workOrder);
              return (
                <details className="flow-work-order-group" key={workOrder.id} open>
                  <summary>
                    <div><span>Orden de Trabajo</span><strong>OT-{workOrder.work_order_number ?? '-'}</strong></div>
                    <div className="flow-work-order-group__summary">
                      <small>{workOrderItems.length} {workOrderItems.length === 1 ? 'certificado' : 'certificados'}</small>
                      {groupState ? <mark className={`quotation-status status-${groupState.tone || 'pending'}`}>{groupState.label}</mark> : null}
                    </div>
                  </summary>
                  <div className="flow-work-order-group__content">
                    {workOrderItems.map((item) => renderItem(item, { order, workOrder }))}
                  </div>
                </details>
              );
            })}
          </div>
        </section>
      ))}
    </div>
  );
}
