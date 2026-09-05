import assert from 'node:assert/strict';
import test from 'node:test';

import {
  canRegisterAnotherEquipmentByEquipmentUnit,
  describeEquipmentByEquipmentAction,
  describeMixedSignatureOutcome,
  formatEquipmentByEquipmentBlocker,
  summarizeMixedSignatureOutcome,
  WORKFLOW_MODE_OPTIONS,
} from './lab-equipment-by-equipment-flow';
import type { LabRelatedWorkOrder } from '@/src/types/lab-work-order';

function member(overrides: Partial<LabRelatedWorkOrder>): LabRelatedWorkOrder {
  return {
    id: 1,
    folio: 6400,
    sequence_number: 1,
    status: 'draft',
    workflow_mode: 'group',
    signature_session_id: null,
    equipment_count: 1,
    ...overrides,
  };
}

test('el selector de modalidad nunca expone los nombres internos group/equipment_by_equipment', () => {
  const labels = WORKFLOW_MODE_OPTIONS.map((option) => option.title);
  assert.deepEqual(labels, ['Equipo por equipo', 'Grupo de equipos']);
  for (const option of WORKFLOW_MODE_OPTIONS) {
    assert.ok(option.description.length > 0);
    assert.doesNotMatch(option.title, /equipment_by_equipment|group/);
  }
});

// El estado se reconstruye exclusivamente desde field_sheet_id/field_sheet_status
// -- nunca desde un evento efímero "acabo de guardar este equipo". Esto debe
// funcionar igual justo después de crear, tras refresh, tras cerrar/reabrir
// la app y para equipos que ya existían antes del cambio de workflow_mode.
test('un equipo activo sin FieldSheet ofrece "Seleccionar Hoja de Campo"', () => {
  const descriptor = describeEquipmentByEquipmentAction({ field_sheet_id: null, field_sheet_status: null });
  assert.equal(descriptor.action, 'select_sheet');
  assert.equal(descriptor.label, 'Seleccionar Hoja de Campo');
});

test('un equipo con FieldSheet draft/in_progress ofrece "Continuar captura"', () => {
  for (const status of ['draft', 'in_progress']) {
    const descriptor = describeEquipmentByEquipmentAction({ field_sheet_id: 42, field_sheet_status: status });
    assert.equal(descriptor.action, 'continue_capture');
    assert.equal(descriptor.label, 'Continuar captura');
  }
});

test('un equipo con FieldSheet completed se presenta como listo', () => {
  const descriptor = describeEquipmentByEquipmentAction({ field_sheet_id: 42, field_sheet_status: 'completed' });
  assert.equal(descriptor.action, 'ready');
  assert.equal(descriptor.label, 'Hoja lista');
});

test('formatEquipmentByEquipmentBlocker antepone el número de equipo cuando existe', () => {
  const formatted = formatEquipmentByEquipmentBlocker({
    work_order_id: 1,
    work_order_folio: 6400,
    equipment_id: 5,
    equipment_position: 2,
    equipment: 'Manómetro',
    reason: 'falta resultado final',
  });
  assert.equal(formatted, 'Equipo 2 — falta resultado final.');
});

test('formatEquipmentByEquipmentBlocker no antepone equipo cuando el blocker es a nivel de OT', () => {
  const formatted = formatEquipmentByEquipmentBlocker({
    work_order_id: 1,
    work_order_folio: 6400,
    equipment_id: null,
    equipment_position: null,
    equipment: null,
    reason: 'La OT no tiene equipos activos',
  });
  assert.equal(formatted, 'La OT no tiene equipos activos.');
});

test('canRegisterAnotherEquipmentByEquipmentUnit respeta el máximo de 10', () => {
  assert.equal(canRegisterAnotherEquipmentByEquipmentUnit(0), true);
  assert.equal(canRegisterAnotherEquipmentByEquipmentUnit(9), true);
  assert.equal(canRegisterAnotherEquipmentByEquipmentUnit(10), false);
});

// Cierre "grupos mixtos": UNA firma nunca implica el mismo resultado final
// para todas las OT -- describeMixedSignatureOutcome/summarizeMixedSignatureOutcome
// deben reportar el estado REAL por OT, nunca "todo entregado" por defecto.
test('un miembro equipment_by_equipment completado se reporta como completado y entregado', () => {
  const outcome = describeMixedSignatureOutcome(member({ folio: 6400, workflow_mode: 'equipment_by_equipment', status: 'completed' }));
  assert.equal(outcome, 'OT 6400 completada y entregada');
});

test('un miembro group que sólo firmó recepción se reporta como pendiente de captura, nunca como entregado', () => {
  const outcome = describeMixedSignatureOutcome(member({ folio: 6402, workflow_mode: 'group', status: 'received_signed' }));
  assert.equal(outcome, 'OT 6402 recepción firmada, pendiente de captura técnica');
});

test('summarizeMixedSignatureOutcome refleja el resultado real y distinto de cada OT del evento', () => {
  const summary = summarizeMixedSignatureOutcome([
    member({ folio: 6400, workflow_mode: 'equipment_by_equipment', status: 'completed' }),
    member({ folio: 6401, workflow_mode: 'equipment_by_equipment', status: 'completed' }),
    member({ folio: 6402, workflow_mode: 'group', status: 'received_signed' }),
  ]);
  assert.equal(
    summary,
    'OT 6400 completada y entregada. OT 6401 completada y entregada. OT 6402 recepción firmada, pendiente de captura técnica',
  );
  assert.doesNotMatch(summary, /todo entregado/i);
});
