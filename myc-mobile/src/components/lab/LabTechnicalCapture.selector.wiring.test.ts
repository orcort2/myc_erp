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
  assert.match(source, /templateList: \{[^}]*maxHeight/);
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
  assert.match(source, /<FadeIn transitionKey=\{activeEquipment\.id\}>/);
});
