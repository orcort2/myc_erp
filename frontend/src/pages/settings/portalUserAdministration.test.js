import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const modal = readFileSync(new URL('./UserModal.jsx', import.meta.url), 'utf8');
const users = readFileSync(new URL('./UsersSettingsPanel.jsx', import.meta.url), 'utf8');
const access = readFileSync(new URL('./PortalAccessSettingsPanel.jsx', import.meta.url), 'utf8');
const portalLayout = readFileSync(new URL('../../portal/ClientPortalLayout.jsx', import.meta.url), 'utf8');

test('UserModal expone las siete pestañas administrativas', () => {
  for (const label of ['Perfil', 'Acceso', 'Roles y permisos', 'Organización', 'Comunicaciones', 'Actividad', 'Seguridad']) {
    assert.match(modal, new RegExp(label));
  }
});

test('usuario interno conserva username independiente y múltiples roles', () => {
  assert.match(users, /username: form\.username/);
  assert.match(users, /role_names: form\.role_names/);
  assert.doesNotMatch(users, /roles\?\.\[0\]/);
  assert.doesNotMatch(users, /role_names:\s*\[form\./);
});

test('administración del portal usa roles múltiples y separa el contador global', () => {
  assert.match(access, /MultiRolePicker/);
  assert.match(access, /role_codes: invite\.role_codes/);
  assert.match(access, /Registros públicos globales/);
  assert.match(access, /No se atribuyen al cliente seleccionado/);
  assert.match(access, /approvePortalLinkRequest/);
  assert.match(access, /suspendPortalMembership/);
  assert.match(access, /savePortalConfiguration/);
});

test('cuenta del portal presenta organización y trazabilidad de membresía', () => {
  for (const field of ['client_legal_name', 'client_commercial_name', 'approved_by_name', 'approved_at', 'source']) {
    assert.match(modal, new RegExp(field));
  }
});

test('invitación conserva varios roles y el registro pendiente está en bandeja global', () => {
  assert.match(access, /role_codes: invite\.role_codes/);
  assert.match(access, /Registros públicos globales/);
  assert.match(access, /pendingRegistrations\.map/);
});

test('solicitudes de vínculo exponen creación, aprobación y rechazo explícitos', () => {
  assert.match(access, /createPortalLinkRequest/);
  assert.match(access, /approvePortalLinkRequest/);
  assert.match(access, /rejectPortalLinkRequest/);
});

test('membresías exponen suspensión, reactivación, revocación y contacto principal', () => {
  for (const operation of ['suspendPortalMembership', 'reactivatePortalMembership', 'revokePortalMembership', 'setPrimaryPortalMembership']) {
    assert.match(access, new RegExp(operation));
  }
});

test('configuración del portal se carga y persiste mediante su contrato real', () => {
  assert.match(access, /getPortalConfiguration/);
  assert.match(access, /savePortalConfiguration/);
  assert.doesNotMatch(access, /require_mfa:\s*true/);
});

test('navegación de usuarios del portal depende de users.view', () => {
  assert.match(portalLayout, /permission: 'users\.view'/);
  assert.match(portalLayout, /user\?\.permissions\?\.includes\(entry\.permission\)/);
});
