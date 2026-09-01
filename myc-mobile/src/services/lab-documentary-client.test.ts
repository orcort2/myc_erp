import assert from 'node:assert/strict';
import test from 'node:test';

import { resolveDocumentaryClientLabel } from './lab-documentary-client';

test('1. modo order muestra el cliente receptor de la OT, no un dato propio del equipo', () => {
  const label = resolveDocumentaryClientLabel(
    { certificate_client_mode: 'order', final_client_company_snapshot: null },
    { client_name: 'Cliente Receptor A' },
  );
  assert.equal(label, 'Cliente Receptor A');
});

test('2. modo different muestra el snapshot propio del equipo, no el receptor de la OT', () => {
  const label = resolveDocumentaryClientLabel(
    { certificate_client_mode: 'different', final_client_company_snapshot: 'Cliente Documental B' },
    { client_name: 'Cliente Receptor A' },
  );
  assert.equal(label, 'Cliente Documental B');
});

test('3. un mismo grupo/OT puede mostrar clientes documentales distintos por equipo, sin mezclarlos', () => {
  const workOrder = { client_name: 'Cliente Receptor A' };
  const receptorEquipment = { certificate_client_mode: 'order' as const, final_client_company_snapshot: null };
  const differentEquipment = { certificate_client_mode: 'different' as const, final_client_company_snapshot: 'Cliente Documental C' };
  assert.equal(resolveDocumentaryClientLabel(receptorEquipment, workOrder), 'Cliente Receptor A');
  assert.equal(resolveDocumentaryClientLabel(differentEquipment, workOrder), 'Cliente Documental C');
});
