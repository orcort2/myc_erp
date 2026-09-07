import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

import {
  flowContextLabel,
  inferStepForStatus,
  isReceptionEditable,
  resolveStepAfterStatusUpdate,
  statusPresentation,
} from './lab-work-order-step';

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

// Fase 5: work-orders.tsx evita interrumpir una firma en curso del mismo
// cohorte conservando el paso 'signatures' cuando llega un evento realtime,
// pero eso nunca puede sustituir un status terminal ya confirmado por
// backend -- un estado visual local jamás gana sobre el estado real.
test('Fase 5: conserva "signatures" ante un evento del mismo cohorte mientras el status siga sin cerrar', () => {
  assert.equal(resolveStepAfterStatusUpdate('signatures', true, 'in_progress'), 'signatures');
  assert.equal(resolveStepAfterStatusUpdate('signatures', true, 'ready_to_close'), 'signatures');
});

test('una firma realmente activa conserva la protección de reconciliación existente', () => {
  assert.equal(resolveStepAfterStatusUpdate('signatures', true, 'in_progress'), 'signatures');
});

test('Fase 5: un status terminal del mismo cohorte SIEMPRE gana sobre "signatures" conservado', () => {
  assert.equal(resolveStepAfterStatusUpdate('signatures', true, 'completed'), 'completed');
  assert.equal(resolveStepAfterStatusUpdate('signatures', true, 'partially_closed'), 'completed');
  assert.equal(resolveStepAfterStatusUpdate('signatures', true, 'cancelled'), 'completed');
});

test('Fase 5: un cohorte distinto nunca conserva "signatures" -- siempre re-deriva del status real', () => {
  assert.equal(resolveStepAfterStatusUpdate('signatures', false, 'in_progress'), 'technical');
  assert.equal(resolveStepAfterStatusUpdate('signatures', false, 'completed'), 'completed');
});

test('Fase 5: fuera del paso "signatures" siempre re-deriva del status real, sin excepción', () => {
  assert.equal(resolveStepAfterStatusUpdate('technical', true, 'ready_to_close'), 'review');
  assert.equal(resolveStepAfterStatusUpdate('review', true, 'completed'), 'completed');
});

test('Fase 5: ambos puntos de reconciliación en work-orders.tsx usan resolveStepAfterStatusUpdate, no el carve-out inline anterior', () => {
  const source = screenSource();
  const occurrences = source.split('resolveStepAfterStatusUpdate(current, sameSignatureCohort, detail.status)').length - 1;
  assert.equal(occurrences, 2);
  // El carve-out inline (paso 'signatures' conservado sin mirar si el status
  // ya es terminal) quedó reemplazado por completo -- si reaparece, alguien
  // reintrodujo el bug que Fase 5 corrigió.
  assert.equal(source.includes("current === 'signatures'\n"), false);
});

test('realtime, openExisting y selectRelated no confunden una firma histórica preservada con una captura activa', () => {
  const source = screenSource();
  const policyChecks = source.split('const skipPreservedSignatures = canSkipSignaturesAfterReopen(detail)').length - 1;
  const historicalStateClears = source.split('skipPreservedSignatures || current == null ? null').length - 1;
  const guardedCohorts = source.split('const sameSignatureCohort = !skipPreservedSignatures').length - 1;
  assert.equal(policyChecks, 3);
  assert.equal(historicalStateClears, 3);
  assert.equal(guardedCohorts, 2);
});

test('el CTA de una reapertura preservada continúa a technical sin abrir ni crear un flujo de firmas', () => {
  const source = screenSource();
  const captureBlock = source.slice(source.indexOf("step === 'capture' &&"), source.indexOf("step === 'technical' &&"));
  assert.match(captureBlock, /onPress=\{\(\) => setStep\(canSkipSignaturesAfterReopen\(workOrder\) \? 'technical' : 'signatures'\)\}/);
  assert.match(captureBlock, /canSkipSignaturesAfterReopen\(workOrder\) \? 'Continuar proceso' : 'Continuar a recepción de equipos'/);
  assert.equal(captureBlock.includes('openSignatureFlow('), false);
  assert.equal(captureBlock.includes('setSignatureFlowState('), false);
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

test('la revisión de recepción no usa lenguaje de cierre', () => {
  assert.equal(flowContextLabel('capture', 'draft'), 'Recepción de equipos');
  assert.equal(flowContextLabel('signatures', 'draft'), 'Revisión y firma de recepción');
  assert.equal(flowContextLabel('technical', 'received_signed'), 'Captura técnica');
  assert.equal(flowContextLabel('review', 'ready_to_close'), 'Cierre técnico');
  assert.equal(flowContextLabel('completed', 'completed'), 'Grupo histórico');
});

test('11. received_signed oculta agregar equipo (editable gatea "+ Añadir equipo")', () => {
  const source = screenSource();
  assert.match(source, /editable && canManageEquipment.*Añadir equipo/);
});

test('12. received_signed oculta editar equipo (editable gatea abrir el editor de equipo)', () => {
  const source = screenSource();
  // El flujo equipo-por-equipo (encargo posterior) necesitó una rama extra
  // en el onPress (abrir captura directa cuando el equipo ya tiene acción de
  // hoja asignada), así que la condición pasó de un && encadenado a un
  // if -- la garantía real (editable && canManageEquipment sigue
  // gateando showEquipmentEditor) es la misma en ambas formas.
  assert.match(source, /editable && canManageEquipment[\s\S]{0,20}showEquipmentEditor\(item\)/);
});

test('editable se deriva de isReceptionEditable, no de una comparación de status suelta', () => {
  const source = screenSource();
  assert.match(source, /isReceptionEditable\(workOrder\.status\)/);
});

test('1, 2, 3. el paso de firma usa un encabezado único y muestra OT con equipos', () => {
  const source = screenSource();
  assert.match(source, /RECEPCIÓN DE EQUIPOS/);
  assert.doesNotMatch(source, /REVISIÓN DE RECEPCIÓN/);
  assert.doesNotMatch(source, /Cliente receptor:/);
  assert.match(source, /receptionOrder\.equipment\.map/);
});

test('4, 5, 6. cada equipo en la revisión de recepción muestra cliente documental, servicio y folio', () => {
  const source = screenSource();
  // describeEquipmentSummary ya resuelve cliente documental/servicio/folio
  // (incluyendo "Pendiente" para vinculado sin autorizar, ver
  // lab-equipment-configured-payload.test.ts); aquí sólo se confirma que la
  // revisión de recepción efectivamente los muestra.
  assert.match(source, /describeEquipmentSummary\(item, receptionOrder\.client_name\)/);
  assert.match(source, /summary\.client.*summary\.service/);
  assert.match(source, /Folio: \{summary\.folio\}/);
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

// --------------------------------------------------------------------------
// Auditoría de semántica de reapertura (2026-09) -- causa raíz OT 6443
// --------------------------------------------------------------------------
// Producción: OT 6443 fue cerrada, luego reabierta preservando la firma
// (signature_session_id conservado, signature_preserved=true,
// signature_required=false); backend regresaba la OT a "draft" y Mobile
// interpretaba ese "draft" siempre como "falta recepción", mostrando de
// nuevo "Recepción de equipos" pese a que las 5 FieldSheets seguían
// completed/is_current intactas en BD. La corrección real vive en el
// backend (operational_tickets.py::_reopen_closed_cohort: preserve ahora
// produce "in_progress", no "draft" -- invalidate sigue siendo "draft"
// porque ahí sí hace falta repetir la recepción/firma). Estas pruebas fijan
// el contrato que Mobile ya cumple gracias a ese cambio de status de
// dominio, sin necesitar lógica especial de reopen aquí.

test('OT 6443: una reapertura preserve (status in_progress) nunca vuelve a "Recepción de equipos"', () => {
  const step = inferStepForStatus('in_progress');
  assert.equal(step, 'technical');
  assert.equal(flowContextLabel(step, 'in_progress'), 'Captura técnica');
});

test('OT 6443: una reapertura invalidate (status draft) sí exige recepción de nuevo -- comportamiento correcto, no el bug', () => {
  // Distinto del caso preserve: invalidate limpia signature_session_id y
  // exige signature_required=true, así que volver a "Recepción de equipos"
  // aquí es el comportamiento correcto, no una regresión del bug de OT 6443.
  const step = inferStepForStatus('draft');
  assert.equal(step, 'capture');
  assert.equal(flowContextLabel(step, 'draft'), 'Recepción de equipos');
});

test('el mensaje obsoleto "volvió a draft y puede editarse" ya no existe en el reopen directo', () => {
  const source = screenSource();
  assert.doesNotMatch(source, /volvió a draft/);
});

test('reopenDirectly navega de inmediato al step correcto tras el 200 (no depende de un refresh/evento aparte)', () => {
  const source = screenSource();
  const reopenDirectlyBlock = source.slice(
    source.indexOf('async function reopenDirectly()'),
    source.indexOf('async function reopenDirectly()') + 1500,
  );
  assert.match(reopenDirectlyBlock, /setStep\(inferStepForStatus\(detail\.status\)\)/);
  assert.match(reopenDirectlyBlock, /La OT fue reabierta para correcciones\. La recepción y las firmas preservadas se mantienen\./);
});

test('"Solicitar desbloqueo" de OT (ticket reopen) dice que la OT sigue cerrada hasta aprobación', () => {
  const source = screenSource();
  assert.match(source, /La OT seguirá cerrada hasta que un usuario autorizado apruebe el ticket\./);
});

test('sección 12: "Completar cambios" reemplaza la etiqueta normal de cierre exclusivamente cuando workOrder.reopened_at existe (metadata backend, no state local)', () => {
  const source = screenSource();
  const occurrences = source.split("'Completar cambios'").length - 1;
  assert.equal(occurrences, 2, 'ambas variantes del botón de cierre (con y sin canSkipSignaturesAfterReopen) deben usar la misma condición');
  assert.match(source, /workOrder\.reopened_at \? 'Completar cambios'/);
  // Usa el MISMO mecanismo de cierre (completeClosure) -- nunca un endpoint paralelo.
  assert.doesNotMatch(source, /\/complete-changes/);
});

// --------------------------------------------------------------------------
// Auditoría quirúrgica (2026-09-06) -- "Completar cambios" no debe quedar
// pegado una vez que la OT vuelve a completed.
// --------------------------------------------------------------------------
// reopened_at es trazabilidad histórica PERMANENTE (nunca se limpia, ni debe
// limpiarse) -- así que la condición para mostrar "Completar cambios" no
// puede depender sólo de reopened_at != null, se combina con el STEP actual
// (derivado de status, nunca state local suelto). Estas pruebas fijan que:
// (a) el botón vive exclusivamente dentro del bloque step === 'review'
// (OT todavía abierta tras el reopen), nunca dentro de step === 'completed'
// (donde vive el bloque histórico/entrega); y (b) completeClosure siempre
// fuerza setStep('completed') al recibir un 200, así que la pantalla nunca
// se queda mostrando el botón de cierre después de que la OT ya cerró.

test('"Completar cambios" vive exclusivamente en step === \'review\' -- nunca aparece en el bloque step === \'completed\'', () => {
  const source = screenSource();
  const reviewBlockStart = source.indexOf("step === 'review' &&");
  const completedBlockStart = source.indexOf("step === 'completed' &&");
  assert.ok(reviewBlockStart !== -1 && completedBlockStart !== -1 && reviewBlockStart < completedBlockStart);

  const reviewBlock = source.slice(reviewBlockStart, completedBlockStart);
  assert.match(reviewBlock, /'Completar cambios'/);

  // El bloque 'completed' se extiende hasta el siguiente paso declarado con
  // el mismo patrón "step === '...' &&" (o fin de archivo si es el último).
  const nextStepBlockStart = source.indexOf("step === '", completedBlockStart + 1);
  const completedBlock = source.slice(
    completedBlockStart,
    nextStepBlockStart === -1 ? undefined : nextStepBlockStart,
  );
  assert.doesNotMatch(completedBlock, /Completar cambios/);
});

test('completeClosure siempre fuerza setStep(\'completed\') al recibir 200 -- la pantalla de "Completar cambios" nunca queda pegada tras un cierre exitoso', () => {
  const source = screenSource();
  const fnStart = source.indexOf('async function completeClosure(');
  const fnBody = source.slice(fnStart, fnStart + 800);
  assert.match(fnBody, /const detail = await postLabCompletion\(/);
  assert.match(fnBody, /setStep\('completed'\)/);
});

test('reopened_at != null y status completed: el mismo workOrder ya no cae en el bloque review (regresión "pegado")', () => {
  // inferStepForStatus ignora reopened_at por diseño -- el status terminal
  // manda siempre, así que un workOrder ya completed (con o sin
  // reopened_at histórico) resuelve a 'completed', nunca a 'review'.
  const stepWithHistory = inferStepForStatus('completed');
  assert.equal(stepWithHistory, 'completed');
  assert.notEqual(stepWithHistory, 'review');
});
