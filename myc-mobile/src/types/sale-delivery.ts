export type SaleDelivery = {
  id: number;
  service_order_id: number;
  mode: 'myc_technician';
  status: 'technician_requested' | 'scheduled';
  delivery_address?: Record<string, unknown> | null;
  scheduled_for?: string | null;
  lines: { id: number; quantity: number; sale_unit_state_id?: number | null }[];
};
