import assert from 'node:assert/strict';
import { existsSync, readFileSync, readdirSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

/**
 * Cierre UX 2026-09: Hojas de Campo deja de ser un módulo independiente en
 * Inicio -- Clientes ocupa su lugar. La captura sigue viviendo exclusivamente
 * dentro de OT (equipo -> hoja -> captura -> resultados), sin una pantalla
 * global de Hojas de Campo ni rutas huérfanas apuntando a ella.
 */

const appDir = resolve(dirname(fileURLToPath(import.meta.url)), '../../app/(technician)');

function readSource(relativePath: string): string {
  return readFileSync(resolve(appDir, relativePath), 'utf8');
}

test('Inicio ya no ofrece la tarjeta independiente "Hojas de Campo"', () => {
  const source = readSource('index.tsx');
  assert.doesNotMatch(source, /Hojas de Campo/);
  assert.doesNotMatch(source, /Pendientes, en captura y completadas/);
});

test('Inicio ofrece la tarjeta "Clientes" en su lugar', () => {
  const source = readSource('index.tsx');
  assert.match(source, /Clientes/);
  assert.match(source, /\(technician\)\/clients/);
});

test('field-sheets.tsx (tray independiente) ya no existe como archivo', () => {
  assert.equal(existsSync(resolve(appDir, 'field-sheets.tsx')), false);
});

test('ninguna pantalla navega a la ruta huérfana (technician)/field-sheets', () => {
  const files = readdirSync(appDir, { withFileTypes: true, recursive: true })
    .filter((entry) => entry.isFile() && (entry.name.endsWith('.tsx') || entry.name.endsWith('.ts')));
  for (const file of files) {
    const source = readFileSync(resolve(file.parentPath ?? appDir, file.name), 'utf8');
    assert.doesNotMatch(
      source,
      /\(technician\)\/field-sheets['"`]/,
      `${file.name} todavía navega a la ruta huérfana (technician)/field-sheets`,
    );
  }
});

test('OT sigue siendo el único punto de acceso a la captura de FieldSheet', () => {
  const workOrdersSource = readSource('work-orders.tsx');
  assert.match(workOrdersSource, /LabTechnicalCapture/);
  const captureSource = readFileSync(
    resolve(appDir, '../../src/components/lab/LabTechnicalCapture.tsx'),
    'utf8',
  );
  assert.match(captureSource, /equipment\/\$\{[^}]*equipment\.id\}\/field-sheet/);
});
