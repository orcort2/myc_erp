import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

/**
 * Cierre de contrato canónico LAB (2026-09): LabTechnicalCapture debe
 * renderizar los campos comunes desde el contrato canónico fijo, no desde
 * `definition.blocks` -- y nunca ramificar por template_key/instrumento.
 */
const source = readFileSync(
  resolve(dirname(fileURLToPath(import.meta.url)), './LabTechnicalCapture.tsx'),
  'utf8',
);

test('los campos comunes ya no se derivan de resolveBlockFields sobre definition.blocks', () => {
  assert.doesNotMatch(source, /const ordinaryFields/);
  assert.doesNotMatch(source, /resolveBlockFields\(block, \{ fallbackLabels: FIELD_LABELS, readOnlyKeys: readOnlyFields \}\)/);
});

test('las 5 secciones canónicas se renderizan en el orden fijo del contrato, no por plantilla', () => {
  assert.match(source, /CANONICAL_GROUP_ORDER\.map\(\(group\) => \(/);
  assert.match(source, /canonicalFieldsByGroup\(group\)\.map\(\(field\) => renderCanonicalField\(field\)\)/);
});

test('los campos especializados quedan en su propia sección, fuera del contrato canónico', () => {
  assert.match(source, /specializedCaptureFields\(definition\?\.blocks, \{ fallbackLabels: FIELD_LABELS, readOnlyKeys: readOnlyFields \}\)/);
  assert.match(source, /title="Datos técnicos especializados"/);
});

test('un campo canónico readonly se lee siempre de canonicalFieldValue (sheet/equipment), nunca de `values` a secas', () => {
  assert.match(source, /canonicalFieldValue\(field, \{ sheet, equipment: activeEquipment, values \}\)/);
});

test('no hay branches por template_key ni por nombre de instrumento en la captura común', () => {
  assert.doesNotMatch(source, /template_key === ['"]/);
  assert.doesNotMatch(source, /selectedTemplate === ['"](?:anemometro|calibradores|presion|bascula|temperatura)['"]/);
  assert.doesNotMatch(source, /activeEquipment\.instrument === /);
});

test('temperatura sigue sin implementarse en este componente', () => {
  assert.doesNotMatch(source, /'temperatura'/);
});

test('los dos campos booleanos canónicos (condición general / considerar desviaciones) tienen su propio control, no un TextInput libre', () => {
  assert.match(source, /field\.kind === 'boolean'/);
  assert.match(source, /setField\(field\.key, true\)/);
  assert.match(source, /setField\(field\.key, false\)/);
});
