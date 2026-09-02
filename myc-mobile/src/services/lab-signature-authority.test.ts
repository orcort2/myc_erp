import assert from 'node:assert/strict';
import test from 'node:test';

import { PENDING_SIGNATURE_LABEL, resolveCalibradoPor } from './lab-signature-authority';

test('Calibró se deriva del firmante técnico real de la sesión de firma', () => {
  const name = resolveCalibradoPor({
    signature_session: {
      id: 1,
      root_work_order_id: 1,
      signed_at: '2026-09-01T10:00:00Z',
      signatures: [
        { id: 1, signature_type: 'technician', signer_name: 'Técnico LAB', signed_at: '2026-09-01T10:00:00Z' },
        { id: 2, signature_type: 'client', signer_name: 'Cliente LAB', signed_at: '2026-09-01T10:00:00Z' },
      ],
    },
  });
  assert.equal(name, 'Técnico LAB');
});

test('Calibró es Pendiente sin sesión de firma todavía (nunca texto libre)', () => {
  assert.equal(resolveCalibradoPor({ signature_session: null }), PENDING_SIGNATURE_LABEL);
  assert.equal(resolveCalibradoPor({ signature_session: undefined }), PENDING_SIGNATURE_LABEL);
});

test('Calibró es Pendiente si la sesión existe pero no trae firma técnica', () => {
  const name = resolveCalibradoPor({
    signature_session: {
      id: 1, root_work_order_id: 1, signed_at: '2026-09-01T10:00:00Z',
      signatures: [{ id: 2, signature_type: 'client', signer_name: 'Cliente LAB', signed_at: '2026-09-01T10:00:00Z' }],
    },
  });
  assert.equal(name, PENDING_SIGNATURE_LABEL);
});
