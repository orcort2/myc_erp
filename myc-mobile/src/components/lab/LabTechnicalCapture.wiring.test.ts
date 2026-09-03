import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

/**
 * Cierre UX 2026-09: verificación de cableado (mismo patrón de assert.match
 * sobre el source ya usado en lab-work-order-closure.test.ts) para los
 * puntos que la lógica pura (field-sheet-template-selector,
 * lab-signature-authority, field-sheet-draft-view-state) no puede probar
 * por sí sola: que el componente realmente los usa donde corresponde.
 */
const source = readFileSync(
  resolve(dirname(fileURLToPath(import.meta.url)), './LabTechnicalCapture.tsx'),
  'utf8',
);

test('el selector de hoja filtra todas las plantillas cargadas sin recortar la fuente', () => {
  assert.match(source, /filterFieldSheetTemplates\(templates, templateSearch\)/);
  assert.doesNotMatch(source, /\{templates\.map\(\(template\)/);
  assert.doesNotMatch(source, /\.slice\(0,\s*5\)/);
});

test('sin resultados de búsqueda, la solicitud vive dentro del selector, no en un botón aparte', () => {
  assert.match(source, /visibleTemplates\.length === 0/);
  assert.match(source, /\+ Solicitar hoja de campo/);
  assert.doesNotMatch(source, /label="No encuentro la hoja necesaria"/);
});

test('Calibró/Revisó/Elaboró se leen de autoridad real, nunca como TextInput libre', () => {
  assert.match(source, /SIGNATURE_AUTHORITY_KEYS/);
  assert.match(source, /resolveCalibradoPor\(workOrder\)/);
  assert.match(source, /PENDING_SIGNATURE_LABEL/);
});

test('guardar borrador transiciona a modo consulta; completar hoja sigue bloqueada a edición directa', () => {
  assert.match(source, /viewModeAfterDraftSaved/);
  assert.match(source, /viewModeAfterEditRequested/);
  assert.match(source, /captureIsAlwaysReadOnly\(sheet\.status\)/);
});

test('la hoja completed ofrece PDF y, sólo con la OT abierta, desbloqueo', () => {
  assert.match(source, /downloadFieldSheetPdf/);
  assert.match(source, /field-sheet\/pdf/);
  assert.match(source, /requestFieldSheetReopen/);
  assert.match(source, /field-sheet-reopen/);
  assert.match(source, /!\['completed', 'partially_closed'\]\.includes\(workOrder\.status\)/);
});

test('los accesos y acciones usan el canon visual vigente', () => {
  assert.match(source, /<ActionTile icon="table-edit" label="Valores"/);
  assert.match(source, /<SecondaryButton[^>]*label="Ver \/ descargar PDF"/);
  assert.match(source, /<SecondaryButton label="Guardar borrador"/);
  assert.match(source, /<PrimaryButton label="Completar hoja"/);
  assert.match(source, /<AdministrativeButton label="Solicitar desbloqueo"/);
  assert.match(source, /<DangerButton[^>]*label="Eliminar borrador"/);
  assert.doesNotMatch(source, /<ActionTile[^>]*label="(?:Guardar borrador|Completar hoja)"/);
});

test('fecha de recepción respeta autoridad OT y la solicitud técnica es informativa', () => {
  assert.match(source, /canOverrideReceptionDate \? \(/);
  assert.match(source, /<MycDatePickerField[\s\S]*updateReceptionDate/);
  assert.match(source, /<ReadOnlyField label=\{field\.label\} value=\{workOrder\.reception_date\}/);
  assert.match(source, /<AdministrativeButton[\s\S]*label="Solicitar cambio de fecha"/);
  assert.match(source, /tickets\/reception-date-change/);
  assert.match(source, /La fecha no cambiará automáticamente/);
});

test('el borrador editable se descarta por DELETE explícito y no aparece para completed', () => {
  assert.match(source, /method: 'DELETE'/);
  assert.match(source, /!captureIsAlwaysReadOnly\(sheet\.status\)/);
  assert.match(source, /<DangerButton label="Eliminar borrador"/);
});
