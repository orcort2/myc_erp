import assert from 'node:assert/strict';
import test from 'node:test';

import {
  getEtsInvoiceContextView,
  getEtsInvoicePresentation,
} from './etsInvoicePresentation.js';

test('keeps an unresolved null context in loading without presentation', () => {
  assert.deepEqual(
    getEtsInvoiceContextView({ contextResolved: false, invoice: null }),
    { phase: 'loading', presentation: null }
  );
});

test('only resolves null as no invoice after the contextual request finishes', () => {
  const result = getEtsInvoiceContextView({
    contextResolved: true,
    invoice: null,
  });
  assert.equal(result.phase, 'empty');
  assert.equal(result.presentation.statusLabel, 'Sin factura');
});

test('presents an ETS without invoice as a reusable draft entry point', () => {
  assert.deepEqual(getEtsInvoicePresentation(null), {
    kind: 'empty',
    statusLabel: 'Sin factura',
    primaryActionLabel: 'Crear factura',
    canDownload: false,
  });
});

test('presents a draft without document downloads', () => {
  const context = getEtsInvoiceContextView({
    contextResolved: true,
    invoice: { status: 'draft' },
  });
  const result = context.presentation;
  assert.equal(context.phase, 'invoice');
  assert.equal(result.statusLabel, 'Borrador');
  assert.equal(result.primaryActionLabel, 'Continuar factura');
  assert.equal(result.canDownload, false);
});

test('presents a stamped invoice with both existing download actions', () => {
  const context = getEtsInvoiceContextView({
    contextResolved: true,
    invoice: { status: 'issued' },
  });
  const result = context.presentation;
  assert.equal(context.phase, 'invoice');
  assert.equal(result.statusLabel, 'Timbrada');
  assert.equal(result.primaryActionLabel, 'Ver factura');
  assert.equal(result.canDownload, true);
});

test('presents a cancelled invoice as read-only detail', () => {
  const result = getEtsInvoicePresentation({ status: 'cancelled' });
  assert.equal(result.statusLabel, 'Cancelada');
  assert.equal(result.primaryActionLabel, 'Ver detalle');
  assert.equal(result.canDownload, false);
});
