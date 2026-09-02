import assert from 'node:assert/strict';
import test from 'node:test';

import { filterFieldSheetTemplates, MAX_VISIBLE_TEMPLATES } from './field-sheet-template-selector';
import type { FieldSheetTemplate } from '@/src/types/lab-work-order';

function template(name: string, key = name): FieldSheetTemplate {
  return { template_key: key, name, version: 1, blocks: [], result_sections: [] };
}

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
