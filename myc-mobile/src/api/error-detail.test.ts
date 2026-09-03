import assert from 'node:assert/strict';
import test from 'node:test';

import { readApiErrorDetail } from './error-detail';

function jsonResponse(body: unknown, status = 409): Response {
  return {
    status,
    json: async () => body,
  } as Response;
}

test('cierre UX 2026-09: readApiErrorDetail traduce códigos crudos conocidos a mensajes humanos', async () => {
  const detail = await readApiErrorDetail(jsonResponse({ detail: 'OT_NOT_CLOSED' }));
  assert.equal(detail.message, 'Esta OT todavía no está cerrada; no se puede solicitar ni ejecutar la reapertura.');
  assert.equal(detail.code, null);
});

test('readApiErrorDetail deja pasar mensajes de servidor que no son un código conocido', async () => {
  const detail = await readApiErrorDetail(jsonResponse({ detail: 'Ya existe una solicitud activa para esta OT' }));
  assert.equal(detail.message, 'Ya existe una solicitud activa para esta OT');
});

test('readApiErrorDetail traduce el mensaje también cuando viene dentro de {message, missing_fields}', async () => {
  const detail = await readApiErrorDetail(
    jsonResponse({ detail: { message: 'TICKET_SELF_APPROVAL_FORBIDDEN', missing_fields: null } }),
  );
  assert.equal(detail.message, 'No puedes aprobar o rechazar una solicitud que tú mismo creaste.');
});

test('readApiErrorDetail conserva code/items estructurados y humaniza el mensaje derivado', async () => {
  const detail = await readApiErrorDetail(
    jsonResponse({ detail: { code: 'LAB_DRAFT_SHEETS_INVALID', items: [{ equipment_id: 1 }] } }, 422),
  );
  assert.equal(detail.code, 'LAB_DRAFT_SHEETS_INVALID');
  assert.deepEqual(detail.items, [{ equipment_id: 1 }]);
  // LAB_DRAFT_SHEETS_INVALID no está en el diccionario de humanización -- la
  // UI lo consume vía `.code`/`.items`, nunca muestra `.message` para este caso.
  assert.equal(detail.message, 'LAB_DRAFT_SHEETS_INVALID');
});

test('readApiErrorDetail convierte el 422 estándar de FastAPI en fieldErrors útiles', async () => {
  const detail = await readApiErrorDetail(jsonResponse({
    detail: [
      { type: 'date_from_datetime_parsing', loc: ['body', 'reception_date'], msg: 'Input should be a valid date' },
      { type: 'missing', loc: ['body', 'equipment', 'serial_number'], msg: 'Field required' },
    ],
  }, 422));
  assert.equal(detail.message, 'Revisa los campos marcados.');
  assert.equal(detail.code, 'validation_error');
  assert.deepEqual(detail.fieldErrors, [
    {
      field: 'reception_date',
      code: 'date_from_datetime_parsing',
      message: 'Fecha de recepción: formato incorrecto. Usa AAAA-MM-DD.',
      expected: null,
    },
    {
      field: 'equipment.serial_number',
      code: 'missing',
      message: 'Revisa el campo equipment.serial number.',
      expected: null,
    },
  ]);
});
