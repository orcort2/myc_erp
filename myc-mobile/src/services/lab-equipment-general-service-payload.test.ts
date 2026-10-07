import assert from 'node:assert/strict';
import test from 'node:test';

import type { LabEquipment } from '@/src/types/lab-work-order';
import {
  buildConfiguredEquipmentPayload,
  buildEquipmentCreateBody,
  buildEquipmentEditRequestBody,
  defaultDocumentaryClient,
  diffEquipmentEdit,
  hasEquipmentEditChanges,
  hydrateEquipmentFormValues,
  type EquipmentBasicData,
} from './lab-equipment-configured-payload';

const basic: EquipmentBasicData = {
  instrument: 'Báscula', brand: 'MYC', model: 'B-1', identification: 'ID-1', serial_number: 'SER-1',
  report_number: null, observations: 'Obs', is_good_condition: true,
};

function saved(overrides: Partial<LabEquipment> = {}): LabEquipment {
  return {
    id: 1, position: 1, instrument: 'Báscula', brand: 'MYC', model: 'B-1', identification: 'ID-1', serial_number: 'SER-1',
    report_number: null, observations: 'Obs', is_good_condition: true, service_type: null, linked_company_id: null,
    linked_company_name_snapshot: null, linked_company_prefix_snapshot: null, certificate_folio: null,
    automatic_certificate_folio: null, folio_status: 'unassigned', folio_ticket_id: null, field_sheet_id: null,
    field_sheet_status: null, technical_report_id: null, technical_report_type: null, technical_report_folio: null,
    technical_report_status: null, technical_report_revision_count: 0, certificate_client_mode: 'order',
    final_lab_client_id: null, final_client_company_snapshot: null, final_client_address_snapshot: null,
    final_client_attention_snapshot: null,
    ...overrides,
  };
}

test('Servicio General: el alta sólo envía el equipo -- sin service, service_type ni certificate_client', () => {
  const body = buildEquipmentCreateBody({ equipment: basic, operationalCategory: 'general_service' }, 3);
  assert.deepEqual(Object.keys(body), ['equipment']);
  const { report_number: _systemAssigned, ...expected } = basic;
  assert.deepEqual(body.equipment, { ...expected, expected_edit_version: 3 });
  assert.doesNotMatch(JSON.stringify(body), /service|certificate|linked|accredited|traceable|installation/);
  assert.ok(!('report_number' in body.equipment), 'el folio del reporte lo asigna el sistema');
});

test('Servicio General: la edición conserva la misma forma (sólo equipment + versión)', () => {
  const body = buildEquipmentEditRequestBody({ equipment: basic, operationalCategory: 'general_service' }, 7);
  assert.deepEqual(Object.keys(body), ['equipment']);
  assert.equal(body.equipment.expected_edit_version, 7);
});

test('calibración: el cuerpo de alta es EXACTAMENTE el de buildConfiguredEquipmentPayload (sin regresión)', () => {
  const values = {
    equipment: basic,
    documentaryClient: { ...defaultDocumentaryClient(), mode: 'different' as const, finalLabClientId: 4 },
    service: { serviceType: 'traceable' as const, linkedCompanyId: null },
  };
  assert.deepEqual(
    buildEquipmentCreateBody(values, 2),
    buildConfiguredEquipmentPayload(values.equipment, values.documentaryClient, values.service, 2),
  );
  const body = buildEquipmentCreateBody(values, 2);
  assert.equal(body.service.service_type, 'traceable');
  assert.ok(body.certificate_client);
});

test('hidratar Servicio General: sólo datos base; calibración sigue hidratando cliente documental y servicio', () => {
  const general = hydrateEquipmentFormValues(saved(), 'general_service');
  assert.deepEqual(Object.keys(general).sort(), ['equipment', 'operationalCategory']);
  const calibration = hydrateEquipmentFormValues(saved({ service_type: 'linked' }));
  assert.equal(calibration.service.serviceType, 'linked');
  assert.equal(calibration.documentaryClient.mode, 'order');
});

test('el diff de Servicio General sólo considera el equipo (no hay cliente documental ni servicio)', () => {
  const initial = hydrateEquipmentFormValues(saved(), 'general_service');
  const same = hydrateEquipmentFormValues(saved(), 'general_service');
  assert.equal(hasEquipmentEditChanges(diffEquipmentEdit(initial, same)), false);
  const edited = { ...same, equipment: { ...same.equipment, brand: 'Otra' } };
  const changes = diffEquipmentEdit(initial, edited);
  assert.deepEqual(changes, { equipmentChanged: true, certificateClientChanged: false, serviceChanged: false });
});
