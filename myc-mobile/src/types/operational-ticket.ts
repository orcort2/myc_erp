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
  type: 'reopen_work_order';
  status: TicketStatus;
  work_order_id: number;
  work_order_folio: number;
  client_name: string;
  requested_by_user_id: number;
  requested_by_name: string;
  reviewed_by_user_id: number | null;
  reason: string;
  description: string;
  requested_signature_policy: SignaturePolicy;
  final_signature_policy: SignaturePolicy | null;
  decision_comment: string | null;
  created_at: string;
  reviewed_at: string | null;
  resolved_at: string | null;
};
