import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

import { inferStepForStatus, isReceptionEditable, statusPresentation } from './lab-work-order-step';

function screenSource(): string {
  return readFileSync(
    resolve(dirname(fileURLToPath(import.meta.url)), '../../app/(technician)/work-orders.tsx'),
    'utf8',
  );
}

// Fase 3: recepción firmada + máquina de estados. Sin renderer de
// componentes en este repo, se prueba la lógica pura que gobierna a qué
// paso lleva cada status (inferStepForStatus/isReceptionEditable) y, para
// el contenido de pantalla que no es una función pura (JSX de
// work-orders.tsx), se verifica por presencia de texto/expresión en el
// código fuente -- mismo patrón ya usado en lab-work-order-closure.test.ts.

test('1 y 15. draft lleva a configurar equipos, no a captura técnica todavía', () => {
  assert.equal(inferStepForStatus('draft'), 'capture');
});

test('16. in_progress muestra captura activa', () => {
  assert.equal(inferStepForStatus('in_progress'), 'technical');
});

test('received_signed también lleva a captura técnica (recepción ya firmada, lista para capturar)', () => {
  assert.equal(inferStepForStatus('received_signed'), 'technical');
});

test('17. ready_to_close lleva directo a confirmar cierre, sin volver a pedir firma', () => {
  assert.equal(inferStepForStatus('ready_to_close'), 'review');
});

test('legacy: ready_for_signatures conserva la pantalla histórica de firma completada', () => {
  assert.equal(inferStepForStatus('ready_for_signatures'), 'signatures');
});

test('20. los estados terminales (completed, partially_closed, cancelled) siguen funcionando', () => {
  assert.equal(inferStepForStatus('completed'), 'completed');
  assert.equal(inferStepForStatus('partially_closed'), 'completed');
  assert.equal(inferStepForStatus('cancelled'), 'completed');
});

test('10. received_signed se presenta como "RECEPCIÓN FIRMADA"', () => {
  assert.equal(statusPresentation('received_signed').label, 'RECEPCIÓN FIRMADA');
});

test('in_progress y ready_to_close tienen etiquetas propias, distintas de "EN PROCESO"', () => {
  assert.equal(statusPresentation('in_progress').label, 'EN CAPTURA');
  assert.equal(statusPresentation('ready_to_close').label, 'LISTA PARA CIERRE');
});

test('11 y 12. received_signed ya no es editable -- equipo/cliente/servicio quedan de sólo lectura', () => {
  assert.equal(isReceptionEditable('received_signed'), false);
  assert.equal(isReceptionEditable('in_progress'), false);
  assert.equal(isReceptionEditable('ready_to_close'), false);
});

test('sólo draft admite editar la recepción', () => {
  assert.equal(isReceptionEditable('draft'), true);
});

test('11. received_signed oculta agregar equipo (editable gatea "+ Añadir equipo")', () => {
  const source = screenSource();
  assert.match(source, /editable && canManageEquipment.*Añadir equipo/);
});

test('12. received_signed oculta editar equipo (editable gatea abrir el editor de equipo)', () => {
  const source = screenSource();
  assert.match(source, /editable && canManageEquipment && showEquipmentEditor\(item\)/);
});

test('editable se deriva de isReceptionEditable, no de una comparación de status suelta', () => {
  const source = screenSource();
  assert.match(source, /isReceptionEditable\(workOrder\.status\)/);
});

test('1, 2, 3. el paso de firma muestra una revisión de recepción con cliente receptor y equipos', () => {
  const source = screenSource();
  assert.match(source, /REVISIÓN DE RECEPCIÓN/);
  assert.match(source, /Cliente receptor: \{workOrder\.client_name\}/);
  assert.match(source, /workOrder\.equipment\.map/);
});

test('4, 5, 6. cada equipo en la revisión de recepción muestra cliente documental, servicio y folio', () => {
  const source = screenSource();
  // describeEquipmentSummary ya resuelve cliente documental/servicio/folio
  // (incluyendo "Pendiente" para vinculado sin autorizar, ver
  // lab-equipment-configured-payload.test.ts); aquí sólo se confirma que la
  // revisión de recepción efectivamente los muestra.
  assert.match(source, /describeEquipmentSummary\(item, workOrder\.client_name\)/);
  assert.match(source, /summary\.client.*summary\.service.*Folio: \{summary\.folio\}/);
});

test('10. received_signed muestra "Recepción firmada" con acción para continuar a captura técnica', () => {
  const source = screenSource();
  assert.match(source, /Recepción firmada/);
  assert.match(source, /Continuar a captura técnica/);
});

test('17. ready_to_close ofrece una acción de cierre explícita, no de firma', () => {
  const source = screenSource();
  assert.match(source, /Confirmar cierre/);
  assert.match(source, /Cerrar OT \$\{workOrder\.folio\}/);
});

test('18. un error al firmar no limpia signatureFlowState -- el formulario conserva lo capturado', () => {
  const source = screenSource();
  const applySignatures = source.slice(
    source.indexOf('async function applySignatures'),
    source.indexOf('async function completeClosure'),
  );
  const catchBlock = applySignatures.slice(applySignatures.indexOf('} catch (error) {'));
  assert.equal(catchBlock.includes('setSignatureFlowState(null)'), false);
});

test('8 y 9. la firma de recepción reutiliza MobileSignatureFlow sin un segundo sistema de firmas', () => {
  // canContinueSignature/validateSignatureSubmission (probados a fondo en
  // signature-flow-state.test.ts: "a tap or negligible movement does not
  // count as a signature", "both client and technician require an explicit
  // real drawing", "a trimmed name and a real stroke allow progression")
  // gobiernan exactamente igual la firma de recepción -- Fase 3 no
  // construye un componente nuevo, sólo cambia CUÁNDO se invoca.
  const source = screenSource();
  const signaturesBlock = source.slice(
    source.indexOf("step === 'signatures' && workOrder.status === 'draft'"),
    source.indexOf("step === 'signatures' && workOrder.status === 'ready_for_signatures'"),
  );
  assert.match(signaturesBlock, /<MobileSignatureFlow/);
  assert.match(signaturesBlock, /onSubmit=\{applySignatures\}/);
});

test('7. vinculado pendiente en la revisión de recepción reutiliza el mismo "Pendiente" comprensible que el resumen del equipo (describeEquipmentSummary, no un texto nuevo)', () => {
  const source = screenSource();
  // La revisión de recepción arma cada fila con describeEquipmentSummary,
  // que ya produce folio: "Pendiente" para vinculado sin folio autorizado
  // (ver lab-equipment-configured-payload.test.ts: 'el resumen muestra
  // "Pendiente" para Vinculado sin empresa autorizada todavía') -- no se
  // reinventa una presentación distinta sólo para este paso.
  const signaturesBlock = source.slice(
    source.indexOf("step === 'signatures' && workOrder.status === 'draft'"),
    source.indexOf("step === 'signatures' && workOrder.status === 'ready_for_signatures'"),
  );
  assert.match(signaturesBlock, /describeEquipmentSummary/);
});

test('19. un conflicto de versión (REVISION_CONFLICT) se presenta con el mensaje del backend, sin sustituirlo', () => {
  const source = screenSource();
  // request() ya propaga detail.message tal cual llega del backend (incluye
  // REVISION_CONFLICT) como ApiError; los catch de guardado siempre usan
  // error.message antes que un texto genérico.
  assert.match(source, /error instanceof Error \? error\.message : /);
});
