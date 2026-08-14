export type LabEquipment = {
  id: number;
  position: number;
  instrument: string;
  brand: string;
  identification: string;
  serial_number: string;
  report_number: string | null;
  is_good_condition: boolean;
};

export type LabRelatedWorkOrder = {
  id: number;
  folio: number;
  sequence_number: number;
  status: 'draft' | 'ready_for_signatures' | 'completed';
  equipment_count: number;
};

export type LabWorkOrder = {
  id: number;
  folio: number;
  root_work_order_id: number;
  previous_work_order_id: number | null;
  sequence_number: number;
  signature_session_id: number | null;
  reception_date: string;
  departure_date: string;
  client_name: string;
  address: string;
  contact_name: string | null;
  contact_phone: string | null;
  contact_email: string | null;
  postal_code: string | null;
  city: string | null;
  state_name: string | null;
  purchase_order: string | null;
  notes: string | null;
  status: 'draft' | 'ready_for_signatures' | 'completed';
  revision_number: number;
  edit_version: number;
  reopen_ticket_id: number | null;
  signature_required: boolean;
  signature_preserved: boolean;
  equipment: LabEquipment[];
  related_work_orders: LabRelatedWorkOrder[];
};

export type LabListItem = {
  id: number;
  folio: number;
  client_name: string;
  reception_date: string;
  status: string;
  equipment_count: number;
  revision_number: number;
  signature_required: boolean;
};

export type GeneralData = {
  reception_date: string;
  departure_date: string;
  client_name: string;
  address: string;
  contact_name: string;
  contact_phone: string;
  contact_email: string;
  postal_code: string;
  city: string;
  state_name: string;
  purchase_order: string;
  notes: string;
};

export type EquipmentData = Omit<LabEquipment, 'id' | 'position'>;
