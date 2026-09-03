import assert from 'node:assert/strict';
import test from 'node:test';

import { filterFieldSheetTemplates, MAX_VISIBLE_TEMPLATES, templateDisplayLabel } from './field-sheet-template-selector';
import type { FieldSheetTemplate, FieldSheetTemplateMetadata } from '@/src/types/lab-work-order';

function template(name: string, key = name, metadata?: FieldSheetTemplateMetadata): FieldSheetTemplate {
  return { template_key: key, name, version: 1, blocks: [], result_sections: [], metadata };
}

const myc = (magnitude_key: string, magnitude_label: string, supported_equipment: string[], search_aliases: string[]): FieldSheetTemplateMetadata => ({
  organization_key: 'myc',
  organization_label: 'MYC',
  magnitude_key,
  magnitude_label,
  supported_equipment,
  search_aliases,
});

const capymet = (magnitude_key: string, magnitude_label: string): FieldSheetTemplateMetadata => ({
  organization_key: 'capymet',
  organization_label: 'CAPYMET',
  magnitude_key,
  magnitude_label,
});

const mycVariant = (
  magnitude_key: string,
  magnitude_label: string,
  document_variant_key: string,
  document_variant_label: string,
  supported_equipment: string[],
  search_aliases: string[],
): FieldSheetTemplateMetadata => ({
  organization_key: 'myc',
  organization_label: 'MYC',
  magnitude_key,
  magnitude_label,
  document_variant_key,
  document_variant_label,
  supported_equipment,
  search_aliases,
});

test('sin término de búsqueda, muestra hasta MAX_VISIBLE_TEMPLATES', () => {
  const many = Array.from({ length: 30 }, (_, index) => template(`Hoja ${index}`));
  const visible = filterFieldSheetTemplates(many, '');
  assert.equal(visible.length, MAX_VISIBLE_TEMPLATES);
});

test('filtra por nombre, insensible a mayúsculas/acentos', () => {
  const templates = [
    template('Hoja de Campo Presión'),
    template('Hoja de Campo Termómetro'),
    template('Hoja de Campo Termohigrómetro'),
    template('Hoja de Campo General'),
  ];
  assert.deepEqual(
    filterFieldSheetTemplates(templates, 'pres').map((item) => item.name),
    ['Hoja de Campo Presión'],
  );
  assert.deepEqual(
    filterFieldSheetTemplates(templates, 'term').map((item) => item.name),
    ['Hoja de Campo Termómetro', 'Hoja de Campo Termohigrómetro'],
  );
  assert.deepEqual(
    filterFieldSheetTemplates(templates, 'TÉRMOMETRO').map((item) => item.name),
    ['Hoja de Campo Termómetro'],
  );
});

test('sin coincidencias, resultado vacío (habilita "+ Solicitar hoja de campo")', () => {
  const templates = [template('Hoja de Campo Presión')];
  assert.deepEqual(filterFieldSheetTemplates(templates, 'valvula'), []);
});

test('el filtrado nunca excede MAX_VISIBLE_TEMPLATES aunque haya más coincidencias', () => {
  const templates = Array.from({ length: 10 }, (_, index) => template(`Presión ${index}`));
  assert.equal(filterFieldSheetTemplates(templates, 'presión').length, MAX_VISIBLE_TEMPLATES);
});

// --------------------------------------------------------------------------
// Fase 2 del catálogo LAB (2026-09): búsqueda por organización/magnitud/
// equipo soportado/alias, y nombre visible "[ORG] Magnitud".
// --------------------------------------------------------------------------

const mycPresion = template('Hoja de Campo Presión', 'myc_presion', myc('pressure', 'Presión', ['manómetro', 'vacuómetro', 'manovacuómetro'], ['manometro', 'vacuometro', 'presion diferencial']));
const mycElectrica = template('Hoja de Campo Eléctrica', 'myc_electrica', myc('electrical', 'Eléctrica', ['amperímetro', 'multímetro', 'megaóhmetro'], ['amperimetro', 'multimetro', 'megaohmetro']));
const capymetPresion = template('Hoja de Campo Presión CAPYMET', 'capymet_presion', capymet('pressure', 'Presión'));
const legacyNoMetadata = template('Hoja de Campo General');

test('buscar por equipo soportado encuentra la magnitud correcta (manómetro -> [MYC] Presión)', () => {
  const templates = [mycPresion, mycElectrica, capymetPresion, legacyNoMetadata];
  assert.deepEqual(
    filterFieldSheetTemplates(templates, 'manómetro').map((item) => item.template_key),
    ['myc_presion'],
  );
});

test('buscar por equipo soportado con alias sin acentos también encuentra la magnitud (multímetro -> [MYC] Eléctrica)', () => {
  const templates = [mycPresion, mycElectrica, capymetPresion, legacyNoMetadata];
  assert.deepEqual(
    filterFieldSheetTemplates(templates, 'multimetro').map((item) => item.template_key),
    ['myc_electrica'],
  );
});

test('buscar "capymet" devuelve únicamente las hojas CAPYMET', () => {
  const templates = [mycPresion, mycElectrica, capymetPresion, legacyNoMetadata];
  assert.deepEqual(
    filterFieldSheetTemplates(templates, 'capymet').map((item) => item.template_key),
    ['capymet_presion'],
  );
});

test('buscar "presión" puede mostrar hojas de más de una organización', () => {
  const templates = [mycPresion, mycElectrica, capymetPresion, legacyNoMetadata];
  const matches = filterFieldSheetTemplates(templates, 'presión').map((item) => item.template_key);
  assert.ok(matches.includes('myc_presion'));
  assert.ok(matches.includes('capymet_presion'));
});

test('una plantilla sin metadata de organización/magnitud sigue siendo buscable por su name', () => {
  const templates = [mycPresion, legacyNoMetadata];
  assert.deepEqual(
    filterFieldSheetTemplates(templates, 'general').map((item) => item.template_key),
    [legacyNoMetadata.template_key],
  );
});

test('templateDisplayLabel usa "[ORG] Magnitud" cuando hay metadata, y cae a name cuando no la hay', () => {
  assert.equal(templateDisplayLabel(mycPresion), '[MYC] Presión');
  assert.equal(templateDisplayLabel(capymetPresion), '[CAPYMET] Presión');
  assert.equal(templateDisplayLabel(legacyNoMetadata), 'Hoja de Campo General');
});

// --------------------------------------------------------------------------
// Micro-cierre Fases 1/2 (hallazgo 2): variante documental dentro de la
// magnitud -- "[ORG] Magnitud · Variante", y búsqueda por variante.
// --------------------------------------------------------------------------

const mycCalibradores = template(
  'Hoja de Campo Calibradores',
  'calibradores',
  mycVariant(
    'dimensional', 'Dimensional', 'calibradores', 'Calibradores',
    ['calibrador vernier', 'calibrador de altura', 'calibrador de profundidad'],
    ['vernier', 'calibrador', 'dimensional'],
  ),
);

test('templateDisplayLabel incluye la variante documental cuando existe: "[MYC] Dimensional · Calibradores"', () => {
  assert.equal(templateDisplayLabel(mycCalibradores), '[MYC] Dimensional · Calibradores');
});

test('templateDisplayLabel omite el separador de variante cuando document_variant_label es null (una magnitud, una plantilla)', () => {
  assert.equal(templateDisplayLabel(mycPresion), '[MYC] Presión');
  assert.ok(!templateDisplayLabel(mycPresion).includes('·'));
});

test('buscar "dimensional" (la magnitud) encuentra la variante Calibradores', () => {
  const templates = [mycCalibradores, mycPresion, legacyNoMetadata];
  assert.deepEqual(
    filterFieldSheetTemplates(templates, 'dimensional').map((item) => item.template_key),
    ['calibradores'],
  );
});

test('buscar "calibradores" (la variante) encuentra la plantilla correspondiente', () => {
  const templates = [mycCalibradores, mycPresion, legacyNoMetadata];
  assert.deepEqual(
    filterFieldSheetTemplates(templates, 'calibradores').map((item) => item.template_key),
    ['calibradores'],
  );
});

test('buscar "vernier" (equipo soportado) encuentra la plantilla por supported_equipment/search_aliases', () => {
  const templates = [mycCalibradores, mycPresion, legacyNoMetadata];
  assert.deepEqual(
    filterFieldSheetTemplates(templates, 'vernier').map((item) => item.template_key),
    ['calibradores'],
  );
});

test('buscar "myc" encuentra todas las plantillas MYC, con o sin variante documental', () => {
  const templates = [mycCalibradores, mycPresion, capymetPresion, legacyNoMetadata];
  const matches = filterFieldSheetTemplates(templates, 'myc').map((item) => item.template_key);
  assert.ok(matches.includes('calibradores'));
  assert.ok(matches.includes('myc_presion'));
  assert.ok(!matches.includes('capymet_presion'));
});
