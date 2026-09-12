import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

const source = readFileSync(
  resolve(
    dirname(fileURLToPath(import.meta.url)),
    '../../app/(technician)/work-orders.tsx',
  ),
  'utf8',
);

test('el flujo técnico usa el canon de botones acordado', () => {
  assert.match(
    source,
    /<SecondaryButton icon="arrow-left" label="Volver a equipos" onPress=\{\(\) => setStep\('capture'\)\}/,
  );

  assert.match(
    source,
    /<PrimaryButton icon="arrow-right-circle" label="Continuar a cierre" onPress=\{\(\) => setStep\('review'\)\}/,
  );

  assert.match(
    source,
    /<SecondaryButton icon="download" label="Descargar paquete disponible"/,
  );
});

test('KeyboardAvoidingView es la única autoridad de teclado -- ningún ScrollView administrativo repite el ajuste automático', () => {
  assert.equal(
    source.includes('\n              automaticallyAdjustKeyboardInsets\n'),
    false,
  );

  assert.equal(
    source.includes('\n                  automaticallyAdjustKeyboardInsets\n'),
    false,
  );

  const keyboardAvoidingOpenTags =
    source.split('<KeyboardAvoidingView').length - 1;

  assert.equal(
    keyboardAvoidingOpenTags,
    4,
    'las 4 hojas administrativas deben seguir usando KeyboardAvoidingView',
  );
});

test('el modal principal, el editor de equipo, el diálogo administrativo compartido y la distribución de folios siguen permitiendo scroll con el campo activo visible', () => {
  assert.match(
    source,
    /<ScrollView[\s\S]{0,80}contentContainerStyle=\{styles\.modalContent\}[\s\S]{0,200}keyboardShouldPersistTaps="handled"/,
  );

  const overlayScrolls =
    source.split(
      /<ScrollView\s*\n\s*contentContainerStyle=\{styles\.overlayContent\}/,
    ).length - 1;

  assert.equal(
    overlayScrolls,
    3,
    'editor de equipo, diálogo compartido y distribución de folios comparten el mismo contrato de ScrollView',
  );
});

test('datos generales y equipo presentan fieldErrors estructurados junto al control', () => {
  assert.match(
    source,
    /setGeneralErrors\(Object\.fromEntries\(error\.fieldErrors/,
  );

  assert.match(
    source,
    /setEquipmentErrors\(Object\.fromEntries\(error\.fieldErrors/g,
  );

  assert.match(
    source,
    /<AlertBanner tone="danger">Revisa los campos marcados/,
  );

  assert.match(
    source,
    /fieldErrors=\{equipmentErrors\}/,
  );

  assert.match(
    source,
    /onFieldChange=\{clearEquipmentError\}/,
  );
});

test('anular ingreso de equipo usa el endpoint administrativo void y nunca el DELETE legacy', () => {
  assert.equal(
    source.includes(
      '/equipment/${equipmentEditor.id}?expected_edit_version=${workOrder.edit_version}',
    ),
    false,
    'el DELETE legacy de equipo no debe seguir presente',
  );

  assert.equal(
    source.includes('async function removeEquipment()'),
    false,
    'removeEquipment legacy no debe existir',
  );

  assert.match(
    source,
    /\/equipment\/\$\{voidingEquipment\.id\}\/void/,
  );

  assert.match(
    source,
    /method:\s*'POST'/,
  );

  assert.match(
    source,
    /reason,/,
  );

  assert.match(
    source,
    /expected_edit_version:\s*workOrder\.edit_version/,
  );
});

test('anular ingreso queda reservado a autoridad administrativa y exige confirmación explícita', () => {
  assert.match(
    source,
    /\{canCancel && \(\s*<OperationalActionStack>/,
  );

  assert.match(
    source,
    /label="Anular ingreso del equipo"/,
  );

  assert.match(
    source,
    /setTicketDialogMode\('void_equipment'\)/,
  );

  assert.match(
    source,
    /ticketDialogMode === 'void_equipment' && canCancel/,
  );

  assert.match(
    source,
    /ticketReason\.trim\(\)\.length < 3/,
  );
});

test('el diálogo identifica el equipo que será anulado y conserva el lenguaje de trazabilidad', () => {
  assert.match(
    source,
    /Se anulará el ingreso del equipo/,
  );

  assert.match(
    source,
    /dejará de formar parte activa de esta recepción/,
  );

  assert.match(
    source,
    /registro histórico se conservará/,
  );
});
