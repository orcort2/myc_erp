import assert from 'node:assert/strict';
import test from 'node:test';

import {
  ACTIVITY_ENTITY_DESTINATIONS,
  canEditActivityMessage,
  canResolveActivityAttention,
} from './activityEntities.js';

test('mantiene un destino canónico para las entidades institucionales', () => {
  assert.equal(ACTIVITY_ENTITY_DESTINATIONS.client, '/dashboard#clientes');
  assert.equal(ACTIVITY_ENTITY_DESTINATIONS.field_sheet, '/dashboard#servicios');
  assert.equal(ACTIVITY_ENTITY_DESTINATIONS.document, '/dashboard#documentos');
});

test('sólo permite editar mensajes humanos propios con capacidad explícita', () => {
  const user = { id: 7 };
  const message = { author: user, is_system: false, is_formal: false };
  assert.equal(canEditActivityMessage(message, user, { can_edit_own: true }), true);
  assert.equal(canEditActivityMessage({ ...message, is_system: true }, user, { can_edit_own: true }), false);
  assert.equal(canEditActivityMessage(message, { id: 8 }, { can_edit_own: true }), false);
});

test('respeta asignación individual al resolver una atención', () => {
  const attention = { assigned_user_id: 9 };
  assert.equal(
    canResolveActivityAttention(attention, { id: 9 }, { can_resolve_attention: true }),
    true,
  );
  assert.equal(
    canResolveActivityAttention(attention, { id: 8 }, { can_resolve_attention: true }),
    false,
  );
  assert.equal(
    canResolveActivityAttention(attention, { id: 8 }, {
      can_resolve_attention: true,
      can_moderate: true,
    }),
    true,
  );
});
