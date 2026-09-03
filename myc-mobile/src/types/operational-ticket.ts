export type TicketStatus =
  | 'pending'
  | 'approved'
  | 'rejected'
  | 'in_progress'
  | 'resolved'
  | 'cancelled';

export type SignaturePolicy = 'preserve' | 'invalidate';

export type OperationalTicket = {
  id: number;
  type:
    | 'reopen_work_order'
    | 'manual_myc_folio'
    | 'linked_folio'
    | 'partial_close'
    | 'certificate_folio_block'
    | 'field_sheet_template_request'
    | 'field_sheet_reopen'
    | 'reception_date_change'
    | 'partial_delivery';
  status: TicketStatus;
  work_order_id: number | null;
  equipment_id: number | null;
  equipment_position: number | null;
  equipment_instrument: string | null;
  equipment_brand: string | null;
  equipment_model: string | null;
  equipment_identification: string | null;
  equipment_serial_number: string | null;
  equipment_service_type: string | null;
  equipment_folio_status: string | null;
  operator_client_id: number | null;
  work_order_folio: number | null;
  client_name: string | null;
  requested_by_user_id: number;
  requested_by_name: string;
  reviewed_by_user_id: number | null;
  reason: string;
  description: string;
  requested_signature_policy: SignaturePolicy | null;
  final_signature_policy: SignaturePolicy | null;
  linked_company_id: number | null;
  conversation_id: number | null;
  automatic_folio: string | null;
  requested_folio: string | null;
  authorized_folio: string | null;
  accredited_quantity: number | null;
  traceable_quantity: number | null;
  resolution_snapshot: Record<string, unknown> | null;
  decision_comment: string | null;
  created_at: string;
  reviewed_at: string | null;
  resolved_at: string | null;
};
