import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

import { actionableRequestCount, filterTicketsByKind, visibleRequestKinds } from './request-inbox';
import type { LabWorkOrderGroupRequest } from '../types/lab-work-order';
import type { OperationalTicket } from '../types/operational-ticket';

test('actionable count includes only pending entities the reviewer can process', () => {
  const tickets = [{ status: 'pending' }, { status: 'resolved' }] as OperationalTicket[];
  const groups = [{ status: 'pending' }, { status: 'in_review' }] as LabWorkOrderGroupRequest[];
  assert.equal(actionableRequestCount(tickets, groups, { canReviewTickets: true, canClaimGroups: true }), 2);
  assert.equal(actionableRequestCount(tickets, groups, { canReviewTickets: false, canClaimGroups: true }), 1);
});

test('request filters preserve separate reopening and group projections', () => {
  assert.deepEqual(visibleRequestKinds('all'), { showTickets: true, showGroups: true });
  assert.deepEqual(visibleRequestKinds('reopenings'), { showTickets: true, showGroups: false });
  assert.deepEqual(visibleRequestKinds('groups'), { showTickets: false, showGroups: true });
});

test('cierre UX 2026-09: "Reaperturas" filtra por tipo, no sólo muestra/oculta toda la sección', () => {
  const tickets = [
    { id: 1, type: 'reopen_work_order' },
    { id: 2, type: 'field_sheet_reopen' },
    { id: 3, type: 'manual_myc_folio' },
    { id: 4, type: 'linked_folio' },
    { id: 5, type: 'partial_close' },
    { id: 6, type: 'certificate_folio_block' },
    { id: 7, type: 'field_sheet_template_request' },
  ] as OperationalTicket[];

  assert.deepEqual(
    filterTicketsByKind(tickets, 'reopenings').map((item) => item.id),
    [1, 2],
  );
  // 'all' y 'groups' no filtran por tipo -- la sección de tickets ya se
  // oculta completa vía visibleRequestKinds cuando kind === 'groups'.
  assert.deepEqual(filterTicketsByKind(tickets, 'all'), tickets);
  assert.deepEqual(filterTicketsByKind(tickets, 'groups'), tickets);
});

test('la solicitud linked_folio presenta identidad real del equipo al Admin', () => {
  const source = readFileSync(
    resolve(dirname(fileURLToPath(import.meta.url)), '../../app/(technician)/tickets.tsx'),
    'utf8',
  );
  for (const field of [
    'equipment_position', 'equipment_instrument', 'equipment_brand',
    'equipment_model', 'equipment_identification', 'equipment_serial_number',
    'equipment_folio_status',
  ]) {
    assert.match(source, new RegExp(`selected\\.${field}`));
  }
  assert.doesNotMatch(source, /selected\.type === 'linked_folio'[\s\S]*?Equipo #\{selected\.equipment_id\}/);
});
