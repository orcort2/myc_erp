import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const read = (name) => readFileSync(new URL(`./${name}`, import.meta.url), 'utf8');
const files = ['InvoiceToolbar.jsx', 'InvoiceDetailView.jsx', 'useInvoiceWorkbenchController.js'];

test('CFDI issuing flow no longer mentions test/sandbox wording', () => {
  for (const name of files) {
    const source = read(name);
    assert.doesNotMatch(source, /CFDI de prueba/, name);
    assert.doesNotMatch(source, /sandbox/i, name);
  }
});

test('issue button reads "Generar CFDI" and "Generando CFDI…"', () => {
  for (const name of ['InvoiceToolbar.jsx', 'InvoiceDetailView.jsx']) {
    const source = read(name);
    assert.match(source, /'Generar CFDI'/, name);
    assert.match(source, /'Generando CFDI…'/, name);
  }
});
