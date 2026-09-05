import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

/**
 * Cierre "grupos mixtos": cableado en app/(technician)/work-orders.tsx de
 * las dos piezas administrativas nuevas -- "Asignar OT extra" con su propia
 * modalidad (sección 4) y "Cambiar modalidad de trabajo" (secciones 6-9) --
 * mismo patrón assert.match sobre el source que el resto de wiring-tests de
 * este proyecto (sin framework de render de componentes RN).
 */
const source = readFileSync(
  resolve(dirname(fileURLToPath(import.meta.url)), '../../app/(technician)/work-orders.tsx'),
  'utf8',
);

test('"Asignar OT extra" pregunta la modalidad antes de crear la OT, nunca la hereda en silencio', () => {
  assert.match(source, /onPress=\{confirmAddAdditional\}/);
  const fn = source.slice(source.indexOf('function confirmAddAdditional'), source.indexOf('function confirmAddAdditional') + 600);
  assert.match(fn, /WORKFLOW_MODE_OPTIONS\.map/);
  assert.match(fn, /void addAdditional\(option\.value\)/);
});

test('addAdditional envía workflow_mode explícito en el POST /additional', () => {
  const fn = source.slice(source.indexOf('async function addAdditional'), source.indexOf('function confirmAddAdditional'));
  assert.match(fn, /\/additional\?workflow_mode=\$\{additionalWorkflowMode\}/);
});

test('"Cambiar modalidad de trabajo" sólo se ofrece antes de firmar la recepción, gateado por canCancel', () => {
  assert.match(
    source,
    /canCancel && workOrder\.status === 'draft' && workOrder\.signature_session_id == null &&[\s\S]{0,300}label="Cambiar modalidad de trabajo"/,
  );
});

test('el diálogo de cambio de modalidad exige un motivo y reutiliza postLabWorkOrderWorkflowModeChange', () => {
  const block = source.slice(
    source.indexOf("} else if (ticketDialogMode === 'change_workflow_mode') {"),
    source.indexOf("} else if (ticketDialogMode === 'cancel') {"),
  );
  assert.match(block, /postLabWorkOrderWorkflowModeChange/);
  assert.match(block, /reason: ticketReason\.trim\(\)/);
  assert.match(block, /setWorkOrder\(detail\)/);
});

test('el botón de confirmación del cambio de modalidad se deshabilita si no hay motivo o no cambió la modalidad', () => {
  const buttonBlock = source.slice(source.indexOf('<ActionRow>'), source.indexOf('</ActionRow>'));
  assert.match(buttonBlock, /ticketDialogMode === 'change_workflow_mode'\s*\n\s*&& newWorkflowMode === workOrder\?\.workflow_mode/);
});

test('nunca se refetch/parcha localmente: la respuesta de backend reemplaza el work order completo', () => {
  const block = source.slice(
    source.indexOf("} else if (ticketDialogMode === 'change_workflow_mode') {"),
    source.indexOf("} else if (ticketDialogMode === 'cancel') {"),
  );
  assert.doesNotMatch(block, /\{\s*\.\.\.workOrder,/);
});
