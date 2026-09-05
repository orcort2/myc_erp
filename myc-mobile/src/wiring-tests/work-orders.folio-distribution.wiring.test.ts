import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

/**
 * Auditoría independiente del SHA 102a989: los endpoints backend de
 * "Distribuir folios disponibles" (GET/POST .../certificate-folios/{preview,distribute})
 * existían pero Mobile no los consumía. Cablea la integración real dentro de
 * app/(technician)/work-orders.tsx -- mismo patrón assert.match sobre el
 * source que el resto de wiring-tests de este proyecto (sin framework de
 * render de componentes RN).
 */
const source = readFileSync(
  resolve(dirname(fileURLToPath(import.meta.url)), '../../app/(technician)/work-orders.tsx'),
  'utf8',
);

test('"Distribuir folios disponibles" vive en Acciones administrativas, gateada por canCancel', () => {
  assert.match(
    source,
    /\{canCancel && \(\s*\n\s*<OperationalActionStack>\s*\n\s*<AdministrativeButton\s*\n\s*disabled=\{busy\}\s*\n\s*icon="ticket-confirmation-outline"\s*\n\s*label="Distribuir folios disponibles"/,
  );
});

test('el botón vive dentro de la sección de Acciones administrativas (nunca visible a cliente operativo)', () => {
  const adminSectionStart = source.indexOf('{workOrder && canDelete && (');
  const adminSectionEnd = source.indexOf('{equipmentEditor && (');
  assert.ok(adminSectionStart > -1 && adminSectionEnd > adminSectionStart);
  const adminSection = source.slice(adminSectionStart, adminSectionEnd);
  assert.match(adminSection, /label="Distribuir folios disponibles"/);
  // Un único botón real -- la única otra ocurrencia del texto es el
  // comentario/docstring de openFolioDistribution, nunca otro botón.
  const buttonOccurrences = [...source.matchAll(/label="Distribuir folios disponibles"/g)];
  assert.equal(buttonOccurrences.length, 1);
});

test('abrir el diálogo primero pide preview -- nunca confirma a ciegas', () => {
  const fn = source.slice(
    source.indexOf('async function openFolioDistribution'),
    source.indexOf('async function confirmFolioDistribution'),
  );
  assert.match(fn, /getLabCertificateFolioDistributionPreview/);
  assert.match(fn, /setFolioDistributionPreview\(preview\)/);
});

test('el botón de confirmar sólo se ofrece cuando el pool alcanza y hay pending real', () => {
  const overlay = source.slice(
    source.indexOf('{folioDistributionOpen && canCancel'),
    source.indexOf('</SafeAreaView>'),
  );
  assert.match(overlay, /!hasNoPendingCertificateFolios\(folioDistributionPreview\)\s*\n\s*&& isFolioDistributionSufficient\(folioDistributionPreview\)/);
  assert.match(overlay, /label="Distribuir folios"/);
});

test('pool insuficiente muestra una alerta explícita y nunca ofrece confirmar', () => {
  const overlay = source.slice(
    source.indexOf('{folioDistributionOpen && canCancel'),
    source.indexOf('</SafeAreaView>'),
  );
  assert.match(overlay, /!isFolioDistributionSufficient\(folioDistributionPreview\)[\s\S]{0,120}<AlertBanner tone="danger">/);
});

test('confirmar reutiliza postLabCertificateFolioDistribution y refetch completo vía openExisting', () => {
  const fn = source.slice(
    source.indexOf('async function confirmFolioDistribution'),
    source.indexOf('async function createWorkOrder'),
  );
  assert.match(fn, /postLabCertificateFolioDistribution/);
  assert.match(fn, /await openExisting\(orderId\)/);
  assert.doesNotMatch(fn, /\{\s*\.\.\.workOrder,/);
});

test('segunda ejecución sin pendientes se comunica explícitamente, sin fingir folios asignados', () => {
  const fn = source.slice(
    source.indexOf('async function confirmFolioDistribution'),
    source.indexOf('async function createWorkOrder'),
  );
  assert.match(fn, /No había equipo pendiente por asignar/);
});
