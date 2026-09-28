import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

/**
 * Wiring estructural (no mide layout real): en las tarjetas de Solicitudes el
 * título es flexible y multilínea y el badge de estado conserva su ancho.
 * La validación visual (iPhone 16e / SE 3) se hace en simulador.
 */
const source = readFileSync(
  resolve(dirname(fileURLToPath(import.meta.url)), '../../app/(technician)/tickets.tsx'),
  'utf8',
);

function style(name: string): string {
  const match = new RegExp(`\\b${name}: \\{([^}]*)\\}`).exec(source);
  assert.ok(match, `estilo ${name} no encontrado`);
  return match[1];
}

test('cardTop: fila alineada arriba con separación, sin space-between que empuje el badge', () => {
  const cardTop = style('cardTop');
  assert.match(cardTop, /flexDirection: 'row'/);
  assert.match(cardTop, /alignItems: 'flex-start'/);
  assert.match(cardTop, /gap: 10/);
  assert.doesNotMatch(cardTop, /justifyContent/);
});

test('título de tarjeta flexible y badge de estado que no se encoge', () => {
  assert.match(style('cardTitle'), /flex: 1, flexShrink: 1/);
  assert.match(style('status'), /flexShrink: 0/);
  // El tamaño tipográfico del título no se reduce artificialmente.
  assert.match(style('folio'), /fontSize: 19/);
});

test('tickets operativos y grupos anticipados comparten la misma composición', () => {
  const rows = source.split('<View style={styles.cardTop}>').slice(1).map((block) => block.slice(0, block.indexOf('</View>')));
  assert.equal(rows.length, 2);
  for (const row of rows) {
    assert.match(row, /^\s*<Text style=\{\[styles\.folio, styles\.cardTitle\]\}>/);
    assert.match(row, /<Text style=\{styles\.status\}>/);
  }
  assert.match(source, /Grupo anticipado · #\{group\.id\}/);
});

test('sin truncamiento ni reducción de fuente en los títulos de tarjeta', () => {
  const cards = source.slice(source.indexOf('visibleTickets.map((ticket)'), source.indexOf('No hay solicitudes que coincidan'));
  assert.doesNotMatch(cards, /numberOfLines|adjustsFontSizeToFit|ellipsizeMode/);
});

test('el detalle del modal conserva styles.folio sin la política flexible de la tarjeta', () => {
  assert.match(source, /<Text style=\{styles\.folio\}>\{TICKET_TYPE_LABELS\[selected\.type\]\}/);
  assert.match(source, /<Text style=\{styles\.folio\}>\{selectedGroup\.quantity\} órdenes de trabajo<\/Text>/);
});
