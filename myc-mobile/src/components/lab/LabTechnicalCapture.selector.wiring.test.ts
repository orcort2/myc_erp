import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

/**
 * Cierre UX 2026-09 (item C): el selector de plantilla de hoja de campo debe
 * quedar delimitado (borde/alto máximo/scroll interno) con estados de
 * carga/error/vacío, en vez de una lista que crece sin límite.
 */
const source = readFileSync(
  resolve(dirname(fileURLToPath(import.meta.url)), './LabTechnicalCapture.tsx'),
  'utf8',
);

test('el selector de plantillas tiene un contenedor delimitado con scroll interno', () => {
  assert.match(source, /style=\{styles\.templateList\}/);
  assert.match(source, /const TEMPLATE_ROW_HEIGHT = 56/);
  assert.match(source, /templateList: \{[^}]*maxHeight: TEMPLATE_ROW_HEIGHT \* 5/);
  assert.doesNotMatch(source, /\.slice\(0,\s*5\)/);
  assert.match(source, /styles\.templateRow/);
  assert.match(source, /styles\.templateIndicatorSelected/);
  assert.doesNotMatch(source, /styles\.choice/);
});

test('el selector de plantillas cubre carga/error/vacío, no sólo la lista feliz', () => {
  assert.match(source, /templatesLoading \? \(/);
  assert.match(source, /templatesError \? \(/);
  assert.match(source, /<EmptyState/);
});

test('el status de la hoja se humaniza -- nunca "draft"/"completed" crudo en el badge', () => {
  assert.match(source, /fieldSheetStatusLabel\(sheet\.status\)/);
  assert.doesNotMatch(source, /label=\{sheet\.status\.toUpperCase\(\)\}/);
});

test('el status de la hoja tampoco se cuela crudo en el texto de "Solicitar desbloqueo"', () => {
  assert.doesNotMatch(source, /Hoja completed/);
});

test('cierre UX 2026-09 (item G): entrar a la hoja de un equipo (captura→hoja) usa FadeIn', () => {
  assert.match(source, /<FadeIn transitionKey=\{`\$\{activeEquipment\.id\}:\$\{sheet\?\.id \?\? 'selector'\}`\}>/);
});

test('Vinculado pendiente informa que la captura puede continuar y no ofrece ticket manual', () => {
  assert.match(source, /Folio pendiente de asignación/);
  assert.match(source, /Puedes continuar con la captura de la hoja de campo/);
  assert.doesNotMatch(source, /Ticket · Resolver folio Vinculado/);
});
