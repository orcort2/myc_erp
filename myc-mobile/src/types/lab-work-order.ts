// Fase 3: recepción firmada + máquina de estados. 'ready_for_signatures' se
// conserva como legacy (OT firmada bajo el flujo anterior a esta fase);
// el flujo nuevo nunca lo produce, pero un registro histórico puede seguir
// trayéndolo desde el backend y debe presentarse/cerrarse igual que antes.
export type LabWorkOrderStatus =
  | 'draft'
  | 'received_signed'
  | 'in_progress'
  | 'ready_for_signatures'
  | 'ready_to_close'
  | 'completed'
  | 'partially_closed'
  | 'cancelled';

export type LabEquipment = {
  id: number;
  position: number;
  instrument: string;
  brand: string;
  identification: string;
  serial_number: string;
  // Fase 6: identidad del equipo (mismo criterio que Equipment productivo).
  model: string | null;
  report_number: string | null;
  is_good_condition: boolean;
  service_type: 'accredited' | 'traceable' | 'linked' | null;
  linked_company_id: number | null;
  linked_company_name_snapshot: string | null;
  linked_company_prefix_snapshot: string | null;
  certificate_folio: string | null;
  automatic_certificate_folio: string | null;
  folio_status: 'unassigned' | 'pending' | 'reserved' | 'authorized';
  folio_ticket_id: number | null;
  field_sheet_id: number | null;
  field_sheet_status: string | null;
  certificate_client_mode: 'order' | 'different';
  final_lab_client_id: number | null;
  final_client_company_snapshot: string | null;
  final_client_address_snapshot: string | null;
  final_client_attention_snapshot: string | null;
};

export type LabRelatedWorkOrder = {
  id: number;
  folio: number;
  sequence_number: number;
  status: LabWorkOrderStatus;
  signature_session_id: number | null;
  equipment_count: number;
};

export type LabWorkOrder = {
  id: number;
  folio: number;
  root_work_order_id: number;
  previous_work_order_id: number | null;
  sequence_number: number;
  signature_session_id: number | null;
  signature_scope: 'group' | 'individual' | null;
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
  status: LabWorkOrderStatus;
  lab_client_id: number | null;
  revision_number: number;
  edit_version: number;
  reopen_ticket_id: number | null;
  signature_required: boolean;
  signature_preserved: boolean;
  partial_close_ticket_id: number | null;
  cancellation_reason: string | null;
  // Cierre UX 2026-09: cancelar ya no bloquea desde completed/partially_closed
  // -- previous_status es lo que restore usa para volver exactamente a ese
  // estado (nunca a draft/in_progress como si fuera una reapertura técnica).
  previous_status: LabWorkOrderStatus | null;
  equipment: LabEquipment[];
  related_work_orders: LabRelatedWorkOrder[];
  // Cierre UX 2026-09: autoridad real de "Calibró" en el PDF/captura -- el
  // firmante técnico ya persistido en la sesión de firma de la OT, nunca un
  // input libre (ver LabTechnicalCapture, resolveSignerName). Opcional para
  // no romper los fixtures existentes que no modelan firmas.
  signature_session?: LabSignatureSession | null;
};

export type LabSignature = {
  id: number;
  signature_type: 'technician' | 'client';
  signer_name: string;
  signed_at: string;
};

export type LabSignatureSession = {
  id: number;
  root_work_order_id: number;
  signed_at: string;
  signatures: LabSignature[];
};

export type LabListItem = {
  id: number;
  folio: number;
  client_name: string;
  reception_date: string;
  status: string;
  equipment_count: number;
  completed_equipment_count: number;
  revision_number: number;
  signature_required: boolean;
};

export type GeneralData = {
  lab_client_id: number | null;
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

export type EquipmentData = Pick<LabEquipment,
  'instrument' | 'brand' | 'model' | 'identification' | 'serial_number'
  | 'report_number' | 'is_good_condition'
>;

export type LabClient = {
  id: number;
  operator_client_id: number | null;
  company: string;
  address: string;
  attention: string;
  // Cierre UX 2026-09: domicilio estructurado -- LabWorkOrder ya modelaba
  // postal_code/city/state_name por separado; el cliente ahora también, sin
  // desglosar calle/número/colonia (el dominio tampoco los modela ahí).
  postal_code: string | null;
  city: string | null;
  state: string | null;
  is_active: boolean;
};

export type LinkedCompany = {
  id: number;
  name: string;
  default_certificate_prefix: string;
};

// Fase 6: contrato de campo declarativo completo (mismo shape que
// backend/app/schemas/field_sheet_template.py::FieldSheetFieldRead) -- la
// autoridad principal para label/placeholder/orden/tipo/requerido debe venir
// de aquí cuando el backend lo puebla; FIELD_LABELS en Mobile queda sólo
// como fallback legacy para cuando un bloque no trae field_type/label
// propios (ver src/services/field-sheet-contract.ts).
export type FieldSheetFieldContract = {
  key: string;
  label: string;
  field_type?: string;
  required?: boolean;
  visible?: boolean;
  order?: number;
  placeholder?: string | null;
  help_text?: string | null;
  options?: string[];
  metadata?: Record<string, unknown>;
};

export type FieldSheetResultColumn = {
  key: string;
  label: string;
  source?: string | null;
  width?: string | null;
  unit?: string | null;
  editable?: boolean;
  required?: boolean;
  data_type?: string;
  suggested_unit?: string | null;
  metadata?: Record<string, unknown>;
};

export type FieldSheetResultSection = {
  key: string;
  title: string;
  rows: number;
  columns: FieldSheetResultColumn[];
  allow_add_rows?: boolean;
  allow_remove_rows?: boolean;
  min_rows?: number | null;
  max_rows?: number | null;
  metadata?: Record<string, unknown>;
};

export type FieldSheetTemplateBlock = {
  key: string;
  block_key?: string | null;
  title: string;
  block_type: string;
  order?: number | null;
  visible?: boolean;
  capture_visible?: boolean;
  print_visible?: boolean;
  pdf_visible?: boolean;
  visible_fields?: string[];
  fields?: FieldSheetFieldContract[];
  sections?: { key: string }[];
  required?: boolean;
  metadata?: Record<string, unknown>;
};

/**
 * Fase 2 del catalogo LAB (2026-09): metadata de organizacion/magnitud del
 * template -- puramente de presentacion y búsqueda en el selector Mobile
 * (ver field-sheet-template-selector.ts). No es autoridad de captura (eso
 * sigue siendo field-sheet-canonical-contract.ts) ni de layout/PDF. Todas
 * las claves son opcionales porque las plantillas historicas/fallback
 * (termometro/cronometro/temperatura, o cualquier definicion sin esta
 * metadata) no la tienen -- el selector debe usar un fallback seguro a
 * `name` cuando falta, nunca asumir su presencia.
 */
export type FieldSheetTemplateMetadata = {
  organization_key?: string;
  organization_label?: string;
  magnitude_key?: string;
  magnitude_label?: string;
  supported_equipment?: string[];
  search_aliases?: string[];
  source_document?: string;
};

export type FieldSheetTemplate = {
  template_key: string;
  name: string;
  version: number;
  table_family?: string;
  blocks: FieldSheetTemplateBlock[];
  result_sections: FieldSheetResultSection[];
  metadata?: FieldSheetTemplateMetadata;
};

export type FieldSheetResultRow = {
  id?: number;
  section_key: string;
  row_number: number;
  pattern_value?: string | null;
  ibc_value_1?: string | null;
  ibc_value_2?: string | null;
  ibc_value_3?: string | null;
  unit?: string | null;
  notes?: string | null;
  row_data: Record<string, string>;
};

export type LabFieldSheet = {
  id: number;
  status: string;
  // Fase 6: modelo de revisión -- current es siempre la única is_current=true
  // por equipo; supersedes_field_sheet_id encadena hacia la anterior sin
  // borrarla. Mobile nunca decide esto, sólo lo muestra si aplica.
  revision_number: number;
  is_current: boolean;
  supersedes_field_sheet_id: number | null;
  template_key: string;
  template_definition: FieldSheetTemplate;
  capture_values: Record<string, unknown>;
  work_order_number: number | null;
  reserved_certificate_folio: string | null;
  attention: string | null;
  company: string | null;
  address: string | null;
  reception_date: string | null;
  calibration_date: string | null;
  next_calibration_date: string | null;
  calibration_place: string | null;
  minimum_division: string | null;
  location: string | null;
  units: string | null;
  method: string | null;
  environment_humidity_start: string | null;
  environment_humidity_end: string | null;
  environment_temperature_start: string | null;
  environment_temperature_end: string | null;
  equipment_general_condition: boolean | null;
  consider_equipment_deviations: boolean;
  calibrated_by: string | null;
  reviewed_by: string | null;
  report_made_by: string | null;
  purchase_order_or_quotation: string | null;
  initial_condition: string | null;
  final_condition: string | null;
  observations: string | null;
  evidence_notes: string | null;
  results_rows: FieldSheetResultRow[];
};

export type LabWorkOrderGroupRequest = {
  id: number;
  operator_client_id: number;
  requested_by_user_id: number;
  quantity: number;
  status: 'pending' | 'in_review' | 'approved' | 'rejected';
  root_work_order_id: number | null;
  decision_reason: string | null;
  conversation_id: number | null;
  client_name: string;
  operator_client_name: string;
  requested_by_name: string;
  handled_by_name: string | null;
  handled_by_user_id: number | null;
  claimed_at: string | null;
  decided_at: string | null;
  folios: number[];
  created_at: string;
};
