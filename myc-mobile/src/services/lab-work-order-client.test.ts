import assert from 'node:assert/strict';
import test from 'node:test';

import type { GeneralData, LabClient } from '../types/lab-work-order';
import { generalWithLabClient } from './lab-work-order-client';

const labClient = (overrides: Partial<LabClient>): LabClient => ({
  id: 0, operator_client_id: null, company: '', address: '', attention: '',
  postal_code: null, city: null, state: null, is_active: true,
  ...overrides,
} as LabClient);

const A = labClient({
  id: 1, company: 'Cliente A', address: 'Av. A 100', attention: 'Ana A',
  postal_code: '76000', city: 'Querétaro', state: 'Querétaro',
});
// B con el mínimo que permite el contrato: address/attention "" (no nulos), CP/ciudad/estado null.
const B = labClient({ id: 2, company: 'Cliente B' });

const base: GeneralData = {
  lab_client_id: null, reception_date: '2026-09-28', client_name: '', address: '', contact_name: '',
  contact_phone: '442 000 0000', contact_email: 'ot@example.com', postal_code: '', city: '', state_name: '',
  purchase_order: 'OC-7', notes: 'Frágil',
};

test('A → B: ningún dato derivado del cliente A sobrevive cuando B no lo proporciona', () => {
  const withA = generalWithLabClient(base, A);
  assert.equal(withA.postal_code, '76000');
  const withB = generalWithLabClient(withA, B);
  assert.deepEqual(
    [withB.lab_client_id, withB.client_name, withB.address, withB.contact_name, withB.postal_code, withB.city, withB.state_name],
    [2, 'Cliente B', '', '', '', '', ''],
  );
  for (const value of Object.values(withB)) {
    assert.ok(!['Av. A 100', 'Ana A', '76000', 'Querétaro', 'Cliente A', 1].includes(value as never), `sobrevivió ${String(value)}`);
  }
});

test('los campos que no derivan del cliente se conservan al cambiarlo', () => {
  const withB = generalWithLabClient(generalWithLabClient(base, A), B);
  assert.equal(withB.reception_date, base.reception_date);
  assert.equal(withB.contact_phone, base.contact_phone);
  assert.equal(withB.contact_email, base.contact_email);
  assert.equal(withB.purchase_order, base.purchase_order);
  assert.equal(withB.notes, base.notes);
});

test('B con datos completos los aplica todos', () => {
  const full = labClient({ id: 3, company: 'C', address: 'Calle C', attention: 'Carlos', postal_code: '01000', city: 'CDMX', state: 'CDMX' });
  const next = generalWithLabClient(generalWithLabClient(base, A), full);
  assert.deepEqual(
    [next.address, next.contact_name, next.postal_code, next.city, next.state_name],
    ['Calle C', 'Carlos', '01000', 'CDMX', 'CDMX'],
  );
});
