import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

const source = readFileSync(
  resolve(dirname(fileURLToPath(import.meta.url)), '../../app/(technician)/work-orders.tsx'),
  'utf8',
);

test('el flujo técnico usa el canon de botones acordado', () => {
  // Normalización visual (actividad B): estos wrappers ahora también
  // llevan un icon= semántico -- el atributo se agregó antes de label=.
  assert.match(source, /<SecondaryButton icon="arrow-left" label="Volver a equipos" onPress=\{\(\) => setStep\('capture'\)\}/);
  assert.match(source, /<PrimaryButton icon="arrow-right-circle" label="Continuar a cierre" onPress=\{\(\) => setStep\('review'\)\}/);
  assert.match(source, /<SecondaryButton icon="download" label="Descargar paquete disponible"/);
});

// Corrección 2026-09-08: KeyboardAvoidingView (behavior="padding" en iOS) y
// ScrollView.automaticallyAdjustKeyboardInsets compensaban el teclado a la
// vez -- doble ajuste que subía el sheet/modal de más y tapaba encabezado y
// campos, sobre todo en iOS. KeyboardAvoidingView queda como única
// autoridad en las 4 hojas de este archivo: el modal principal de OT, el
// editor de equipo, el diálogo administrativo compartido (Reabrir orden /
// Anular entrega / Cancelar OT / Cambiar modalidad / solicitar reapertura)
// y la distribución de folios. El scroll y la visibilidad del campo activo
// siguen garantizados por KeyboardAvoidingView + keyboardShouldPersistTaps
// (ya presente en las 4), sin el ajuste automático duplicado.
test('KeyboardAvoidingView es la única autoridad de teclado -- ningún ScrollView administrativo repite el ajuste automático', () => {
  assert.equal(source.includes('\n              automaticallyAdjustKeyboardInsets\n'), false);
  assert.equal(source.includes('\n                  automaticallyAdjustKeyboardInsets\n'), false);
  const keyboardAvoidingOpenTags = source.split('<KeyboardAvoidingView').length - 1;
  assert.equal(keyboardAvoidingOpenTags, 4, 'las 4 hojas administrativas deben seguir usando KeyboardAvoidingView');
});

test('el modal principal, el editor de equipo, el diálogo administrativo compartido y la distribución de folios siguen permitiendo scroll con el campo activo visible', () => {
  assert.match(source, /<ScrollView[\s\S]{0,80}contentContainerStyle=\{styles\.modalContent\}[\s\S]{0,200}keyboardShouldPersistTaps="handled"/);
  const overlayScrolls = source.split(/<ScrollView\s*\n\s*contentContainerStyle=\{styles\.overlayContent\}/).length - 1;
  assert.equal(overlayScrolls, 3, 'editor de equipo, diálogo compartido y distribución de folios comparten el mismo contrato de ScrollView');
});

test('datos generales y equipo presentan fieldErrors estructurados junto al control', () => {
  assert.match(source, /setGeneralErrors\(Object\.fromEntries\(error\.fieldErrors/);
  assert.match(source, /setEquipmentErrors\(Object\.fromEntries\(error\.fieldErrors/g);
  assert.match(source, /<AlertBanner tone="danger">Revisa los campos marcados/);
  assert.match(source, /fieldErrors=\{equipmentErrors\}/);
  assert.match(source, /onFieldChange=\{clearEquipmentError\}/);
});
