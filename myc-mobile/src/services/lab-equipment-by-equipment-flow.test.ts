import assert from 'node:assert/strict';
import test from 'node:test';

import {
  canRegisterAnotherEquipmentByEquipmentUnit,
  describeEquipmentByEquipmentAction,
  formatEquipmentByEquipmentBlocker,
  WORKFLOW_MODE_OPTIONS,
} from './lab-equipment-by-equipment-flow';

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
