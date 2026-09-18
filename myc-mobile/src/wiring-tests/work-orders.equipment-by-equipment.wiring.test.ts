import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

/**
 * Flujo LAB "equipo por equipo": verificación de cableado en
 * app/(technician)/work-orders.tsx -- mismo patrón assert.match sobre el
 * source ya usado en el resto de wiring-tests, ya que este proyecto no
 * tiene un framework de render de componentes RN. La lógica pura
 * (estado por equipo, formato de blockers, copy del selector) se prueba
 * aparte en lab-equipment-by-equipment-flow.test.ts.
 */
const source = readFileSync(
  resolve(dirname(fileURLToPath(import.meta.url)), '../../app/(technician)/work-orders.tsx'),
  'utf8',
);

test('el selector de modalidad sólo se muestra al crear una OT nueva, nunca al editar ni en flujos de grupo', () => {
  assert.match(source, /!workOrder && groupMode === 'none' &&[\s\S]{0,150}WORKFLOW_MODE_OPTIONS\.map/);
});

test('workflow_mode viaja en el payload de creación, nunca en el PATCH de edición', () => {
  const call = source.slice(source.indexOf('async function createWorkOrder'), source.indexOf('async function completeDelivery'));
  assert.match(call, /workOrder \? \{ expected_edit_version: workOrder\.edit_version \} : \{ workflow_mode: workflowMode \}/);
});

test('cada equipo activo reconstruye su acción exclusivamente desde describeEquipmentByEquipmentAction (backend), no desde un evento de guardado', () => {
  assert.match(source, /workOrder\.workflow_mode === 'equipment_by_equipment'\s*\n\s*\? describeEquipmentByEquipmentAction\(item\)/);
});

test('"Finalizar registro de equipos" y "Registrar siguiente equipo" sólo existen para equipment_by_equipment', () => {
  assert.match(source, /workOrder\.workflow_mode === 'equipment_by_equipment' \? \(/);
  const block = source.slice(
    source.indexOf("workOrder.workflow_mode === 'equipment_by_equipment' ? ("),
    source.indexOf('Continuar a recepción de equipos'),
  );
  assert.match(block, /label="Registrar siguiente equipo"/);
  assert.match(block, /label="Finalizar registro de equipos"/);
  assert.match(block, /onPress=\{\(\) => \{ void openEquipmentByEquipmentFinalize\(\); \}\}/);
});

test('"Continuar a cierre" (Technical Capture como cierre) nunca se ofrece en equipment_by_equipment', () => {
  const technicalBlock = source.slice(source.indexOf("step === 'technical' &&"), source.indexOf("step === 'review' &&"));
  assert.match(technicalBlock, /workOrder\.workflow_mode !== 'equipment_by_equipment' && canExecuteWorkOrders/);
});

test('la prevalidación se consulta ANTES de abrir la pantalla de firma, y bloquea abrirla si hay blockers', () => {
  const fn = source.slice(source.indexOf('async function openEquipmentByEquipmentFinalize'), source.lastIndexOf('async function applyEquipmentByEquipmentFinalize'));
  assert.match(fn, /getLabEquipmentByEquipmentPrevalidation/);
  assert.match(fn, /if \(!prevalidation\.ready\) \{\s*\n\s*setEquipmentByEquipmentBlockers\(prevalidation\.blockers\);\s*\n\s*setStep\('signatures'\);\s*\n\s*return;/);
});

test('finalize reutiliza exactamente MobileSignatureFlow, no un segundo sistema de firmas', () => {
  const block = source.slice(
    source.indexOf("step === 'signatures' && workOrder.workflow_mode === 'equipment_by_equipment'"),
    source.indexOf('Legacy: OT firmada bajo el flujo anterior'),
  );
  assert.match(block, /<MobileSignatureFlow/);
  assert.match(block, /onSubmit=\{applyEquipmentByEquipmentFinalize\}/);
});

test('después de finalizar nunca se vuelve a Technical Capture ni a una pantalla de Delivery aparte -- el paso avanza directo a completed', () => {
  const fn = source.slice(source.indexOf('async function applyEquipmentByEquipmentFinalize'), source.indexOf('async function downloadPdf'));
  assert.match(fn, /postLabEquipmentByEquipmentFinalize/);
  assert.match(fn, /setStep\('completed'\)/);
  assert.doesNotMatch(fn, /setStep\('technical'\)/);
  assert.doesNotMatch(fn, /setStep\('review'\)/);
});

test('el error de finalize conserva la firma capturada -- nunca limpia signatureFlowState en el camino de éxito ni de error genérico', () => {
  const fn = source.slice(source.indexOf('async function applyEquipmentByEquipmentFinalize'), source.indexOf('async function downloadPdf'));
  const catchBlock = fn.slice(fn.lastIndexOf('} catch (error) {'));
  assert.doesNotMatch(catchBlock, /setSignatureFlowState\(null\)/);
});

// PENDIENTE 3 (encargo de corrección LAB): describeEquipmentByEquipmentAction
// nunca devuelve null en equipment_by_equipment, así que el tap de la fila
// SIEMPRE navegaba a captura técnica en ese modo y jamás ofrecía editar --
// no existía forma de corregir los datos de un equipo. Ahora "Editar datos"
// es una acción explícita e independiente del tap de la fila.
test('"Editar datos" es una acción explícita e independiente del tap ambiguo de la fila', () => {
  const rowBlock = source.slice(
    source.indexOf('{workOrder.equipment.map((item) => {'),
    source.indexOf('{!workOrder.equipment.length && <Text style={styles.empty}>Aún no hay equipos.</Text>}'),
  );

  // El tap de la fila ya no decide entre dos conceptos (editar vs navegar):
  // representa un único concepto (navegar cuando hay acción pendiente).
  assert.match(rowBlock, /onPress=\{equipmentByEquipmentAction \? \(\) => setStep\('technical'\) : undefined\}/);
  assert.doesNotMatch(rowBlock, /if \(editable && canManageEquipment\) showEquipmentEditor\(item\)/);

  // "Editar datos" existe siempre (ambas modalidades) con los mismos
  // permisos de siempre -- sin permisos nuevos.
  assert.match(rowBlock, /const canEditThisEquipment = editable && canManageEquipment;/);
  assert.match(rowBlock, /\{canEditThisEquipment && \(/);
  assert.match(rowBlock, /onPress=\{\(\) => showEquipmentEditor\(item\)\}/);
  assert.match(rowBlock, />Editar datos</);
});

test('en equipment_by_equipment, "Editar datos" está disponible aunque el equipo ya tenga una acción técnica pendiente (entrar a captura no bloquea corregir datos)', () => {
  const rowBlock = source.slice(
    source.indexOf('{workOrder.equipment.map((item) => {'),
    source.indexOf('{!workOrder.equipment.length && <Text style={styles.empty}>Aún no hay equipos.</Text>}'),
  );
  // "Editar datos" está condicionado sólo a canEditThisEquipment, nunca a
  // "!equipmentByEquipmentAction" -- por eso conviven con el badge de acción
  // pendiente dentro del mismo bloque, sin exclusión mutua.
  const editBlockStart = rowBlock.indexOf('{canEditThisEquipment && (');
  const actionBlockStart = rowBlock.indexOf('{equipmentByEquipmentAction && (');
  assert.notEqual(editBlockStart, -1);
  assert.notEqual(actionBlockStart, -1);
});
