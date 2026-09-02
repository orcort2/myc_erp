import assert from 'node:assert/strict';
import test from 'node:test';

import {
  buildFieldSheetTrayEntries,
  enrichTrayEntryWithFieldSheet,
  groupTrayEntriesByBucket,
} from './field-sheets-tray';
import type { LabEquipment, LabWorkOrder } from '@/src/types/lab-work-order';

function equipment(overrides: Partial<LabEquipment> = {}): LabEquipment {
  return {
    id: 1, position: 1, instrument: 'Manómetro', brand: 'MYC', model: null, range_or_capacity: null,
    identification: 'ID-1', serial_number: 'SER-1', report_number: null, is_good_condition: true,
    service_type: 'accredited', linked_company_id: null, linked_company_name_snapshot: null,
    linked_company_prefix_snapshot: null, certificate_folio: 'MYCA-09-26-4700',
    automatic_certificate_folio: 'MYCA-09-26-4700', folio_status: 'reserved', folio_ticket_id: null,
    field_sheet_id: null, field_sheet_status: null, certificate_client_mode: 'order',
    final_lab_client_id: null, final_client_company_snapshot: null, final_client_address_snapshot: null,
    final_client_attention_snapshot: null,
    ...overrides,
  };
}

function order(overrides: Partial<LabWorkOrder> = {}): LabWorkOrder {
  return {
    id: 10, folio: 6400, root_work_order_id: 10, previous_work_order_id: null, sequence_number: 1,
    signature_session_id: 1, signature_scope: 'individual', reception_date: '2026-08-13',
    departure_date: '2026-08-15', client_name: 'Cliente LAB', address: 'Av. Prueba 123',
    contact_name: 'Persona', contact_phone: null, contact_email: null, postal_code: null, city: null,
    state_name: null, purchase_order: null, notes: null, status: 'received_signed', lab_client_id: null,
    revision_number: 1, edit_version: 1, reopen_ticket_id: null, signature_required: false,
    signature_preserved: false, partial_close_ticket_id: null, cancellation_reason: null,
    equipment: [], related_work_orders: [],
    ...overrides,
  };
}

test('equipo sin hoja en una OT que ya admite captura cae en "pending"', () => {
  const entries = buildFieldSheetTrayEntries([order({ status: 'received_signed', equipment: [equipment()] })]);
  assert.equal(entries.length, 1);
  assert.equal(entries[0].bucket, 'pending');
});

test('equipo sin hoja en una OT todavía draft NO aparece en la bandeja (no es "pendiente de hoja" todavía)', () => {
  const entries = buildFieldSheetTrayEntries([order({ status: 'draft', equipment: [equipment()] })]);
  assert.equal(entries.length, 0);
});

test('hoja draft/in_progress cae en "in_progress"', () => {
  const draft = buildFieldSheetTrayEntries([order({
    equipment: [equipment({ field_sheet_id: 5, field_sheet_status: 'draft' })],
  })]);
  assert.equal(draft[0].bucket, 'in_progress');
  const inProgress = buildFieldSheetTrayEntries([order({
    equipment: [equipment({ field_sheet_id: 5, field_sheet_status: 'in_progress' })],
  })]);
  assert.equal(inProgress[0].bucket, 'in_progress');
});

test('hoja completed cae en "completed"', () => {
  const entries = buildFieldSheetTrayEntries([order({
    equipment: [equipment({ field_sheet_id: 5, field_sheet_status: 'completed' })],
  })]);
  assert.equal(entries[0].bucket, 'completed');
});

test('cliente documental por equipo se resuelve igual que en Mesa Técnica (Fase 4), no el receptor por default', () => {
  const entries = buildFieldSheetTrayEntries([order({
    client_name: 'Cliente Receptor A',
    equipment: [equipment({
      certificate_client_mode: 'different', final_client_company_snapshot: 'Cliente Documental B',
    })],
  })]);
  assert.equal(entries[0].documentaryClient, 'Cliente Documental B');
});

test('groupTrayEntriesByBucket separa las tres bandejas sin mezclar', () => {
  const entries = buildFieldSheetTrayEntries([order({
    equipment: [
      equipment({ id: 1 }), // pending
      equipment({ id: 2, field_sheet_id: 5, field_sheet_status: 'draft' }), // in_progress
      equipment({ id: 3, field_sheet_id: 6, field_sheet_status: 'completed' }), // completed
    ],
  })]);
  const buckets = groupTrayEntriesByBucket(entries);
  assert.equal(buckets.pending.length, 1);
  assert.equal(buckets.in_progress.length, 1);
  assert.equal(buckets.completed.length, 1);
});

test('múltiples OTs se aplanan en una sola lista de entradas', () => {
  const entries = buildFieldSheetTrayEntries([
    order({ id: 10, folio: 6400, equipment: [equipment({ id: 1 })] }),
    order({ id: 11, folio: 6401, equipment: [equipment({ id: 2 })] }),
  ]);
  assert.equal(entries.length, 2);
  assert.deepEqual(entries.map((entry) => entry.workOrderFolio), [6400, 6401]);
});

test('enrichTrayEntryWithFieldSheet fusiona plantilla y progreso reales sin tocar el resto de la entrada', () => {
  const [entry] = buildFieldSheetTrayEntries([order({
    equipment: [equipment({ id: 1, field_sheet_id: 5, field_sheet_status: 'draft' })],
  })]);
  const enriched = enrichTrayEntryWithFieldSheet(
    entry,
    { template_key: 'calibradores', results_rows: [] },
    'Calibradores',
    { completed: 3, total: 10 },
  );
  assert.equal(enriched.templateKey, 'calibradores');
  assert.equal(enriched.templateName, 'Calibradores');
  assert.deepEqual(enriched.progress, { completed: 3, total: 10 });
  assert.equal(enriched.equipmentId, entry.equipmentId);
});
