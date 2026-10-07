/* Fixtures de OT/equipo LAB para pruebas de lifecycle (forma = LabWorkOrder real). */

export function equipmentFixture(overrides: Record<string, unknown> = {}) {
  return {
    id: 289, position: 1, instrument: 'Manómetro', brand: 'B', identification: 'ID', serial_number: 'S1', model: null,
    report_number: null, observations: null, is_good_condition: true, service_type: 'accredited', linked_company_id: null,
    linked_company_name_snapshot: null, linked_company_prefix_snapshot: null, certificate_folio: 'MYCA-10-26-0001',
    automatic_certificate_folio: null, folio_status: 'reserved', folio_ticket_id: null, field_sheet_id: null,
    field_sheet_status: null, technical_report_id: null, technical_report_type: null, technical_report_folio: null,
    technical_report_status: null, technical_report_revision_count: 0, certificate_client_mode: 'order',
    final_lab_client_id: null, final_client_company_snapshot: null, final_client_address_snapshot: null,
    final_client_attention_snapshot: null,
    ...overrides,
  };
}

/** Equipo de Servicio General: sin modalidad, folio ni hoja metrológicos. */
export function generalServiceEquipmentFixture(overrides: Record<string, unknown> = {}) {
  return equipmentFixture({
    instrument: 'Báscula', service_type: null, certificate_folio: null, folio_status: 'unassigned', ...overrides,
  });
}

export function installationProjection(overrides: Record<string, unknown> = {}) {
  return {
    technical_report_id: 5, technical_report_type: 'installation', technical_report_folio: 'MYC-IN10-26-0001',
    technical_report_status: 'draft', technical_report_revision_count: 1, ...overrides,
  };
}

export function workOrderFixture(overrides: Record<string, unknown> = {}) {
  const id = (overrides.id as number | undefined) ?? 72;
  const status = (overrides.status as string | undefined) ?? 'draft';
  const category = (overrides.operational_category as string | undefined) ?? 'calibration';
  return {
    id, folio: 6000 + id, root_work_order_id: id, previous_work_order_id: null, sequence_number: 1,
    signature_session_id: null, signature_scope: null, reception_date: '2026-10-07', departure_date: null,
    client_name: 'Cliente SG', address: 'A', contact_name: 'N', contact_phone: null, contact_email: null,
    postal_code: null, city: null, state_name: null, purchase_order: null, notes: null, status,
    workflow_mode: 'group', operational_category: category, lab_client_id: 1, revision_number: 1, edit_version: 1,
    reopen_ticket_id: null, signature_required: true, signature_preserved: false, partial_close_ticket_id: null,
    cancellation_reason: null, previous_status: null,
    equipment: [category === 'general_service' ? generalServiceEquipmentFixture() : equipmentFixture()],
    related_work_orders: [{ id, folio: 6000 + id, sequence_number: 1, status, workflow_mode: 'group', signature_session_id: null, equipment_count: 1 }],
    pending_signature_review: { sensitive_fields: [], requires_new_signature: false },
    ...overrides,
  };
}

export const installationReport = {
  id: 5, lab_equipment_id: 289, report_type: 'installation', folio: 'MYC-IN10-26-0001', status: 'draft',
  capture_values: {}, document_snapshot: {
    work_order: { id: 72, folio: 6072 },
    client: { name: 'Cliente SG' },
    equipment: { instrument: 'Báscula', brand: 'MYC', model: 'B-1', serial_number: 'SER-1', identification: 'ID-1' },
  },
  report_schema_version: 1, revision_number: 1, is_current: true, evidence: [] as Record<string, unknown>[],
};

export function freshInstallationReport(overrides: Record<string, unknown> = {}) {
  return structuredClone({ ...installationReport, ...overrides });
}

export function evidenceFixture(id: number, evidenceType: string, position: number) {
  return {
    id, technical_report_id: 5, evidence_type: evidenceType, mime_type: 'image/jpeg', sha256: 'b'.repeat(64),
    size_bytes: 120_000, position, caption: null, created_at: '2026-10-08T00:00:00Z',
  };
}
