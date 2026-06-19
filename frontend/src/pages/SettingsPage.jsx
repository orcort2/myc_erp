import React, { useEffect, useState } from 'react';

import {
  listRoles,
  listUsers,
  updateUserRoles,
  updateUserStatus
} from '../services/api.js';

function SettingsPage() {
  const [users, setUsers] = useState([]);
  const [roles, setRoles] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [savingUserId, setSavingUserId] = useState(null);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  async function loadSettings() {
    setError('');
    setIsLoading(true);

    try {
      const [usersData, rolesData] = await Promise.all([
        listUsers(),
        listRoles()
      ]);

      setUsers(Array.isArray(usersData) ? usersData : []);
      setRoles(Array.isArray(rolesData) ? rolesData : []);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    loadSettings();
  }, []);

  async function handleRoleChange(user, roleName) {
    setSavingUserId(user.id);
    setError('');
    setNotice('');

    try {
      const updated = await updateUserRoles(user.id, [roleName]);

      setUsers((current) =>
        current.map((item) => (item.id === updated.id ? updated : item))
      );

      setNotice(`Rol actualizado para ${updated.full_name}`);
    } catch (err) {
      setError(err.message);
    } finally {
      setSavingUserId(null);
    }
  }

  async function handleStatusToggle(user) {
    setSavingUserId(user.id);
    setError('');
    setNotice('');

    try {
      const updated = await updateUserStatus(user.id, !user.is_active);

      setUsers((current) =>
        current.map((item) => (item.id === updated.id ? updated : item))
      );

      setNotice(
        `${updated.full_name} ahora está ${updated.is_active ? 'activo' : 'inactivo'}`
      );
    } catch (err) {
      setError(err.message);
    } finally {
      setSavingUserId(null);
    }
  }

  return (
    <section className="module-workspace">
      <div className="module-workspace__hero">
        <div>
          <p>Configuración</p>
          <h1>Usuarios del sistema</h1>
          <span>Administración de usuarios, roles y acceso</span>
        </div>
      </div>

      {error ? <div className="form-error dashboard-error">{error}</div> : null}
      {notice ? <div className="form-notice dashboard-error">{notice}</div> : null}

      <section className="settings-card">
        <div className="section-heading">
          <div>
            <p>Usuarios</p>
            <h2>{isLoading ? 'Cargando...' : `${users.length} usuarios`}</h2>
          </div>

          <button className="primary-button" type="button" disabled>
            Nuevo usuario
          </button>
        </div>

        <div className="clients-table">
          <div className="clients-table__head">
            <span>Nombre</span>
            <span>Correo</span>
            <span>Estado</span>
            <span>Rol</span>
            <span>Acciones</span>
          </div>

          {isLoading ? (
            <div className="clients-empty">Cargando usuarios...</div>
          ) : users.length ? (
            users.map((user) => {
              const currentRole = user.roles?.[0]?.name ?? '';

              return (
                <div className="clients-table__row" key={user.id}>
                  <span>{user.full_name}</span>
                  <span>{user.email}</span>
                  <span className={user.is_active ? 'settings-status active' : 'settings-status inactive'}>
                    {user.is_active ? 'Activo' : 'Inactivo'}
                  </span>

                  <span>
                    <select
                      className="settings-role-select"
                      disabled={savingUserId === user.id}
                      value={currentRole}
                      onChange={(event)=> handleRoleChange(user , event.target.value)}
                      >
                        <option value="" Sin rol></option>
                        {roles.map((role) => (
                            <option key={role.id} value={role.name}>
                                {role.name}
                            </option>
                        ))}
                    </select>
                  </span>

                  <span className="clients-table__actions">
                    <button
                      className={user.is_active ? 'settings-action-button deactivate' : 'settings-action-button activate'}
                      disabled={savingUserId === user.id}
                      onClick={() => handleStatusToggle(user)}
                      type="button"
                    >
                      {user.is_active ? 'Desactivar' : 'Activar'}
                    </button>
                  </span>
                </div>
              );
            })
          ) : (
            <div className="clients-empty">No hay usuarios registrados.</div>
          )}
        </div>
      </section>
    </section>
  );
}

export default SettingsPage;