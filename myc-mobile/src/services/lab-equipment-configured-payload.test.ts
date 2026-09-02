import assert from 'node:assert/strict';
import test from 'node:test';

import {
  buildCertificateClientPayload,
  buildConfiguredEquipmentPayload,
  buildEquipmentEditRequestBody,
  defaultDocumentaryClient,
  describeEquipmentSummary,
  diffEquipmentEdit,
  hasEquipmentEditChanges,
  hydrateEquipmentFormValues,
  selectFinalClient,
  validateServiceSelection,
} from './lab-equipment-configured-payload';
import { shouldResetFormAfterSubmit } from './lab-client-selector';
import type { LabEquipment } from '@/src/types/lab-work-order';

const equipment = {
  instrument: 'Manómetro', brand: 'MYC', model: null, range_or_capacity: null,
  identification: 'ID-1', serial_number: 'SER-1',
  report_number: null, is_good_condition: true,
};

test('4. el cliente documental por default es "Mismo cliente de la OT" (order) sin snapshots', () => {
  const documentaryClient = defaultDocumentaryClient();
  assert.equal(documentaryClient.mode, 'order');
  assert.equal(documentaryClient.finalLabClientId, null);
  assert.equal(documentaryClient.finalClientCompany, null);
});

test('5. cambiar a "Otro cliente" selecciona un LabClient y congela sus datos actuales', () => {
  const documentaryClient = selectFinalClient({
    id: 7, company: 'Cliente Final', address: 'Calle 1', attention: 'Ing. A',
  });
  assert.equal(documentaryClient.mode, 'different');
  assert.equal(documentaryClient.finalLabClientId, 7);
  assert.equal(documentaryClient.finalClientCompany, 'Cliente Final');
});

test('6. crear/seleccionar cliente final produce el mismo shape congelado que seleccionar uno existente', () => {
  const created = { id: 99, company: 'Recién Creado', address: '', attention: '' };
  const documentaryClient = selectFinalClient(created);
  assert.equal(documentaryClient.finalLabClientId, 99);
  assert.equal(documentaryClient.finalClientAddress, null); // '' -> null, no snapshot vacío ambiguo
  assert.equal(documentaryClient.finalClientAttention, null);
});

test('el payload en modo order omite certificate_client por completo (nada que copiar)', () => {
  const payload = buildConfiguredEquipmentPayload(
    equipment, defaultDocumentaryClient(), { serviceType: 'accredited', linkedCompanyId: null },
  );
  assert.equal('certificate_client' in payload, false);
});

test('endurecimiento: con final_lab_client_id conocido, el payload NUNCA manda company/address/attention -- el backend es la única autoridad', () => {
  const documentaryClient = selectFinalClient({ id: 3, company: 'Cliente B', address: 'Calle X', attention: 'Ing. X' });
  const payload = buildConfiguredEquipmentPayload(
    equipment, documentaryClient, { serviceType: 'traceable', linkedCompanyId: null },
  );
  assert.deepEqual(payload.certificate_client, {
    certificate_client_mode: 'different',
    final_lab_client_id: 3,
    final_client_company_snapshot: null,
    final_client_address_snapshot: null,
    final_client_attention_snapshot: null,
  });
});

test('buildCertificateClientPayload: mode=order siempre viaja completamente null', () => {
  assert.deepEqual(buildCertificateClientPayload(defaultDocumentaryClient()), {
    certificate_client_mode: 'order',
    final_lab_client_id: null,
    final_client_company_snapshot: null,
    final_client_address_snapshot: null,
    final_client_attention_snapshot: null,
  });
});

test('buildCertificateClientPayload: sin referencia de catálogo (finalLabClientId null) sí manda el snapshot local, único caso donde Mobile es la autoridad', () => {
  const documentaryClient = {
    mode: 'different' as const, finalLabClientId: null,
    finalClientCompany: 'Cliente Sin Catálogo', finalClientAddress: null, finalClientAttention: null,
  };
  assert.deepEqual(buildCertificateClientPayload(documentaryClient), {
    certificate_client_mode: 'different',
    final_lab_client_id: null,
    final_client_company_snapshot: 'Cliente Sin Catálogo',
    final_client_address_snapshot: null,
    final_client_attention_snapshot: null,
  });
});

test('7. Acreditado produce service_type=accredited sin empresa vinculada', () => {
  const payload = buildConfiguredEquipmentPayload(
    equipment, defaultDocumentaryClient(), { serviceType: 'accredited', linkedCompanyId: null },
  );
  assert.deepEqual(payload.service, { service_type: 'accredited', linked_company_id: null });
});

test('8. Trazable produce service_type=traceable sin empresa vinculada', () => {
  const payload = buildConfiguredEquipmentPayload(
    equipment, defaultDocumentaryClient(), { serviceType: 'traceable', linkedCompanyId: null },
  );
  assert.deepEqual(payload.service, { service_type: 'traceable', linked_company_id: null });
});

test('9. Vinculado con empresa seleccionada produce service_type=linked + linked_company_id', () => {
  const payload = buildConfiguredEquipmentPayload(
    equipment, defaultDocumentaryClient(), { serviceType: 'linked', linkedCompanyId: 12 },
  );
  assert.deepEqual(payload.service, { service_type: 'linked', linked_company_id: 12 });
});

test('10. Vinculado sin empresa seleccionada es inválido', () => {
  const error = validateServiceSelection({ serviceType: 'linked', linkedCompanyId: null });
  assert.equal(typeof error, 'string');
  assert.equal(validateServiceSelection({ serviceType: 'linked', linkedCompanyId: 5 }), null);
  assert.equal(validateServiceSelection({ serviceType: 'accredited', linkedCompanyId: null }), null);
});

test('11. el resumen del equipo guardado muestra cliente/servicio/folio sin IDs', () => {
  const orderModeSummary = describeEquipmentSummary(
    {
      certificate_client_mode: 'order', final_client_company_snapshot: null,
      service_type: 'accredited', linked_company_name_snapshot: null,
      certificate_folio: 'MYCA-09-26-4700', folio_status: 'reserved',
    },
    'SAVERGLASS DE MÉXICO',
  );
  assert.deepEqual(orderModeSummary, {
    client: 'SAVERGLASS DE MÉXICO', service: 'ACREDITADO', linkedCompany: null, folio: 'MYCA-09-26-4700',
  });

  const differentModeSummary = describeEquipmentSummary(
    {
      certificate_client_mode: 'different', final_client_company_snapshot: 'CLIENTE FINAL XYZ',
      service_type: 'linked', linked_company_name_snapshot: 'Laboratorio Vinculado',
      certificate_folio: null, folio_status: 'pending',
    },
    'SAVERGLASS DE MÉXICO',
  );
  assert.deepEqual(differentModeSummary, {
    client: 'CLIENTE FINAL XYZ', service: 'VINCULADO', linkedCompany: 'Laboratorio Vinculado', folio: 'Pendiente',
  });
});

function savedEquipment(overrides: Partial<LabEquipment> = {}): LabEquipment {
  return {
    id: 1, position: 1, instrument: 'Manómetro', brand: 'MYC', model: null, range_or_capacity: null,
    identification: 'ID-1', serial_number: 'SER-1',
    report_number: null, is_good_condition: true, service_type: 'accredited', linked_company_id: null,
    linked_company_name_snapshot: null, linked_company_prefix_snapshot: null, certificate_folio: 'MYCA-09-26-4700',
    automatic_certificate_folio: 'MYCA-09-26-4700', folio_status: 'reserved', folio_ticket_id: null,
    field_sheet_id: null, field_sheet_status: null, certificate_client_mode: 'order', final_lab_client_id: null,
    final_client_company_snapshot: null, final_client_address_snapshot: null, final_client_attention_snapshot: null,
    ...overrides,
  };
}

test('hidratar formulario: un equipo mode=order existente produce documentaryClient=order', () => {
  const values = hydrateEquipmentFormValues(savedEquipment());
  assert.equal(values.documentaryClient.mode, 'order');
  assert.equal(values.equipment.instrument, 'Manómetro');
});

test('hidratar formulario: un equipo mode=different existente muestra el cliente final ya congelado', () => {
  const values = hydrateEquipmentFormValues(savedEquipment({
    certificate_client_mode: 'different', final_lab_client_id: 8,
    final_client_company_snapshot: 'CLIENTE FINAL XYZ', final_client_address_snapshot: 'Calle Z',
    final_client_attention_snapshot: 'Ing. Z',
  }));
  assert.equal(values.documentaryClient.mode, 'different');
  assert.equal(values.documentaryClient.finalLabClientId, 8);
  assert.equal(values.documentaryClient.finalClientCompany, 'CLIENTE FINAL XYZ');
});

test('hidratar formulario: muestra el service_type y linked_company_id existentes', () => {
  const values = hydrateEquipmentFormValues(savedEquipment({
    service_type: 'linked', linked_company_id: 12, linked_company_name_snapshot: 'Laboratorio Vinculado',
  }));
  assert.equal(values.service.serviceType, 'linked');
  assert.equal(values.service.linkedCompanyId, 12); // la vista resuelve el nombre a partir de este id
});

test('diff: sólo el servicio cambiado marca serviceChanged (ya no decide a qué endpoint llamar, sólo si conviene llamar al único endpoint integrado)', () => {
  const initial = hydrateEquipmentFormValues(savedEquipment());
  const current = { ...initial, service: { serviceType: 'traceable' as const, linkedCompanyId: null } };
  const changes = diffEquipmentEdit(initial, current);
  assert.deepEqual(changes, { equipmentChanged: false, certificateClientChanged: false, serviceChanged: true });
});

test('diff: sólo el cliente documental cambiado marca certificateClientChanged', () => {
  const initial = hydrateEquipmentFormValues(savedEquipment());
  const current = {
    ...initial,
    documentaryClient: selectFinalClient({ id: 5, company: 'Nuevo Cliente Final', address: '', attention: '' }),
  };
  const changes = diffEquipmentEdit(initial, current);
  assert.deepEqual(changes, { equipmentChanged: false, certificateClientChanged: true, serviceChanged: false });
});

test('edición sin cambios reales: diffEquipmentEdit no marca ninguna sección', () => {
  const initial = hydrateEquipmentFormValues(savedEquipment());
  const changes = diffEquipmentEdit(initial, initial);
  assert.deepEqual(changes, { equipmentChanged: false, certificateClientChanged: false, serviceChanged: false });
});

test('el resumen muestra "Pendiente" para Vinculado sin empresa autorizada todavía', () => {
  const summary = describeEquipmentSummary(
    {
      certificate_client_mode: 'order', final_client_company_snapshot: null,
      service_type: 'linked', linked_company_name_snapshot: null,
      certificate_folio: null, folio_status: 'pending',
    },
    'Cliente OT',
  );
  assert.equal(summary.linkedCompany, 'Pendiente');
  assert.equal(summary.folio, 'Pendiente');
});

// Fase 2 hardening (endurecimiento de consistencia): edición integrada en una
// sola transacción -- PATCH .../equipment/{id}/configured en vez de hasta 3
// llamadas independientes. Sin renderer de componentes disponible en este
// repo, se prueba la lógica pura que gobierna esa decisión (ver
// saveEquipmentEdit en app/(technician)/work-orders.tsx).

test('11. edición usa una sola llamada configurada: el body combina equipo + cliente documental + servicio + expected_edit_version en un único objeto', () => {
  const initial = hydrateEquipmentFormValues(savedEquipment());
  const current = {
    ...initial,
    equipment: { ...initial.equipment, instrument: 'Manómetro Nuevo' },
    documentaryClient: selectFinalClient({ id: 5, company: 'Cliente Final', address: 'Calle 1', attention: 'Ing. A' }),
    service: { serviceType: 'traceable' as const, linkedCompanyId: null },
  };
  const body = buildEquipmentEditRequestBody(current, 7);
  assert.equal(body.equipment.instrument, 'Manómetro Nuevo');
  assert.equal(body.equipment.expected_edit_version, 7);
  assert.deepEqual(body.certificate_client, {
    certificate_client_mode: 'different', final_lab_client_id: 5,
    final_client_company_snapshot: null, final_client_address_snapshot: null, final_client_attention_snapshot: null,
  });
  assert.deepEqual(body.service, { service_type: 'traceable', linked_company_id: null });
  // Una sola llamada: un único objeto con las tres secciones, no tres payloads separados.
  assert.deepEqual(Object.keys(body).sort(), ['certificate_client', 'equipment', 'service']);
});

test('12. error 409 conserva formulario abierto: shouldResetFormAfterSubmit("error") es false, por lo que saveEquipmentEdit no cierra el editor de equipo', () => {
  assert.equal(shouldResetFormAfterSubmit('error'), false);
});

test('13. error no limpia valores: reintentar con los mismos values (formulario no limpiado) produce exactamente el mismo body', () => {
  const initial = hydrateEquipmentFormValues(savedEquipment());
  const capturedBeforeError = { ...initial, equipment: { ...initial.equipment, instrument: 'Capturado antes del error' } };
  const firstAttempt = buildEquipmentEditRequestBody(capturedBeforeError, 3);
  const retryAfterError = buildEquipmentEditRequestBody(capturedBeforeError, 3);
  assert.deepEqual(retryAfterError, firstAttempt);
  assert.equal(retryAfterError.equipment.instrument, 'Capturado antes del error');
});

test('14. éxito actualiza el equipo mostrado: shouldResetFormAfterSubmit("success") es true, por lo que el editor se cierra y el work order se refresca con la respuesta', () => {
  assert.equal(shouldResetFormAfterSubmit('success'), true);
});

test('15. no-op no hace request: sin cambios reales, hasEquipmentEditChanges es false', () => {
  const initial = hydrateEquipmentFormValues(savedEquipment());
  assert.equal(hasEquipmentEditChanges(diffEquipmentEdit(initial, initial)), false);
});

test('cualquier cambio real (equipo, cliente documental o servicio) hace que hasEquipmentEditChanges sea true', () => {
  const initial = hydrateEquipmentFormValues(savedEquipment());
  assert.equal(
    hasEquipmentEditChanges(diffEquipmentEdit(initial, { ...initial, equipment: { ...initial.equipment, instrument: 'Otro' } })),
    true,
  );
  assert.equal(
    hasEquipmentEditChanges(diffEquipmentEdit(initial, { ...initial, service: { serviceType: 'traceable', linkedCompanyId: null } })),
    true,
  );
});
