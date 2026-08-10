import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const serviceOrders = readFileSync(new URL('./ServiceOrdersPage.jsx', import.meta.url), 'utf8');
const quality = readFileSync(new URL('./QualityPage.jsx', import.meta.url), 'utf8');
const api = readFileSync(new URL('../services/api.js', import.meta.url), 'utf8');


test('Calidad conserva la única acción frontend de autenticación', () => {
  assert.match(quality, /authenticateCertificate\(selectedCertificate\.id\)/);
  assert.match(quality, /Autenticar \/ Sellar/);
  assert.doesNotMatch(serviceOrders, /authenticateCertificate/);
  assert.doesNotMatch(serviceOrders, /Autenticar aprobados/);
});


test('el cliente API no expone el endpoint masivo retirado de ETS', () => {
  assert.match(api, /\/certificates\/\$\{certificateId\}\/authenticate/);
  assert.doesNotMatch(api, /authenticateApprovedCertificates/);
  assert.doesNotMatch(api, /certificates\/authenticate-approved/);
});
