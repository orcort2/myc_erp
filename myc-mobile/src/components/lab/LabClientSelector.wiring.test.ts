import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

/**
 * Cierre UX 2026-09 (item C): LabClientSelector debe quedar en un contenedor
 * delimitado (Card) con estados de carga/error/vacío visibles y feedback de
 * presión en cada fila -- antes la búsqueda fallaba en silencio y no había
 * borde/tarjeta que delimitara la lista.
 */
const source = readFileSync(
  resolve(dirname(fileURLToPath(import.meta.url)), './LabClientSelector.tsx'),
  'utf8',
);

test('el selector vive dentro de la tarjeta delimitada (Card), en ambos modos', () => {
  assert.match(source, /<Card>[\s\S]*Buscar cliente/);
  assert.match(source, /<Card>[\s\S]*Crear cliente/);
});

test('un error de búsqueda ya no se traga en silencio', () => {
  assert.doesNotMatch(source, /búsqueda silenciosa/);
  assert.match(source, /setSearchError\(/);
  assert.match(source, /<AlertBanner tone="danger">\{searchError\}<\/AlertBanner>/);
});

test('la búsqueda muestra un estado de carga explícito, no una lista vacía ambigua', () => {
  assert.match(source, /<LoadingState label="Buscando clientes…" \/>/);
});

test('cada fila de resultado da feedback de presión, no sólo seleccionado', () => {
  assert.match(source, /pressed && styles\.resultRowPressed/);
});
