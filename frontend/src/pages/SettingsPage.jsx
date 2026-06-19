import React, { useEffect, useMemo, useState } from 'react';

import {
  createUser,
  listRoles,
  listUsers,
  updateUser,
  updateUserRoles,
  updateUserStatus
} from '../services/api.js';

const EMPTY_FORM = {
  full_name: '',
  email: '',
  password: '',
  role_name: '',
  is_active: true
};

function SettingsPage() {
  const [users, setUsers] = useState([]);
  const [roles, setRoles] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [savingUserId, setSavingUserId] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [modalMode, setModalMode] = useState(null);
  const [selectedUser, setSelectedUser] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);

  const availableRoles = useMemo(
    () => roles.filter((role) => role.is_active !== false),
    [roles]
  );

  async function loadSettings() {
    setError('');
    setIsLoading(true);

    try {
      const [usersData, rolesData] = await Promise.all([listUsers(), listRoles()]);
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

  function closeModal() {
    setModalMode(null);
    setSelectedUser(null);
    setForm(EMPTY_FORM);
  }

  function openCreateModal() {
    setError('');
    setNotice('');
    setSelectedUser(null);
    setForm({
      ...EMPTY_FORM,
      role_name: availableRoles[0]?.name ?? ''
    });
    setModalMode('create');
  }

  function openEditModal(user) {
    setError('');
    setNotice('');
    setSelectedUser(user);
    setForm({
      full_name: user.full_name ?? '',
      email: user.email ?? '',
      password: '',
      role_name: user.roles?.[0]?.name ?? availableRoles[0]?.name ?? '',
      is_active: Boolean(user.is_active)
    });
    setModalMode('edit');
  }

  function handleFormChange(event) {
    const { name, value, type, checked } = event.target;
    setForm((current) => ({
      ...current,
      [name]: type === 'checkbox' ? checked : value
    }));
  }

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
      if (selectedUser?.id === updated.id) {
        setSelectedUser(updated);
        setForm((current) => ({ ...current, is_active: updated.is_active }));
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setSavingUserId(null);
    }
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError('');
    setNotice('');

    if (!form.full_name.trim()) {
      setError('Captura el nombre completo.');
      return;
    }

    if (!form.email.trim()) {
      setError('Captura el correo.');
      return;
    }

    if (!form.role_name) {
      setError('Selecciona un rol.');
      return;
    }

    if (modalMode === 'create' && form.password.trim().length < 8) {
      setError('La contraseña debe tener al menos 8 caracteres.');
      return;
    }

    setIsSubmitting(true);

    try {
      if (modalMode === 'create') {
        const created = await createUser({
          email: form.email.trim().toLowerCase(),
          full_name: form.full_name.trim(),
          password: form.password,
          role_names: [form.role_name]
        });
        setUsers((current) => [created, ...current]);
        setNotice(`Usuario creado: ${created.full_name}`);
      } else if (modalMode === 'edit' && selectedUser) {
        const updated = await updateUser(selectedUser.id, {
          email: form.email.trim().toLowerCase(),
          full_name: form.full_name.trim(),
          role_names: [form.role_name],
          is_active: form.is_active
        });
        setUsers((current) =>
          current.map((item) => (item.id === updated.id ? updated : item))
        );
        setNotice(`Usuario actualizado: ${updated.full_name}`);
      }

      closeModal();
    } catch (err) {
      setError(err.message);
    } finally {
      setIsSubmitting(false);
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

          <button className="primary-button" type="button" onClick={openCreateModal}>
            Nuevo usuario
          </button>
        </div>

        <div className="clients-table settings-users-table">
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
                <div
                  className="clients-table__row settings-users-table__row"
                  key={user.id}
                  onClick={() => openEditModal(user)}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter' || event.key === ' ') {
                      event.preventDefault();
                      openEditModal(user);
                    }
                  }}
                  role="button"
                  tabIndex={0}
                >
                  <span>{user.full_name}</span>
                  <span>{user.email}</span>
                  <span className={user.is_active ? 'settings-status active' : 'settings-status inactive'}>
                    {user.is_active ? 'Activo' : 'Inactivo'}
                  </span>

                  <span onClick={(event) => event.stopPropagation()}>
                    <select
                      className="settings-role-select"
                      disabled={savingUserId === user.id}
                      value={currentRole}
                      onChange={(event) => handleRoleChange(user, event.target.value)}
                    >
                      {availableRoles.map((role) => (
                        <option key={role.id} value={role.name}>
                          {role.name}
                        </option>
                      ))}
                    </select>
                  </span>

                  <span className="clients-table__actions" onClick={(event) => event.stopPropagation()}>
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

      {modalMode ? (
        <div className="modal-backdrop" onClick={closeModal}>
          <div
            className="client-modal settings-user-modal"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="section-heading settings-user-modal__header">
              <div>
                <p>Usuarios</p>
                <h2>{modalMode === 'create' ? 'Nuevo usuario' : 'Editar usuario'}</h2>
              </div>

              <button className="secondary-button" type="button" onClick={closeModal}>
                Cerrar
              </button>
            </div>

            <form className="settings-user-form" onSubmit={handleSubmit}>
              <label className="field-label">
                Nombre completo
                <input
                  className="text-input"
                  name="full_name"
                  onChange={handleFormChange}
                  placeholder="Nombre completo"
                  type="text"
                  value={form.full_name}
                />
              </label>

              <label className="field-label">
                Correo
                <input
                  className="text-input"
                  name="email"
                  onChange={handleFormChange}
                  placeholder="usuario@myc.com"
                  type="email"
                  value={form.email}
                />
              </label>

              {modalMode === 'create' ? (
                <label className="field-label">
                  Contraseña
                  <input
                    className="text-input"
                    name="password"
                    onChange={handleFormChange}
                    placeholder="Minimo 8 caracteres"
                    type="password"
                    value={form.password}
                  />
                </label>
              ) : null}

              <label className="field-label">
                Rol
                <select
                  className="settings-role-select"
                  name="role_name"
                  onChange={handleFormChange}
                  value={form.role_name}
                >
                  {availableRoles.map((role) => (
                    <option key={role.id} value={role.name}>
                      {role.name}
                    </option>
                  ))}
                </select>
              </label>

              {modalMode === 'edit' ? (
                <label className="settings-checkbox">
                  <input
                    checked={form.is_active}
                    name="is_active"
                    onChange={handleFormChange}
                    type="checkbox"
                  />
                  Usuario activo
                </label>
              ) : null}

              <div className="client-form__actions--modal">
                <button className="secondary-button" onClick={closeModal} type="button">
                  Cancelar
                </button>
                <button className="primary-button" disabled={isSubmitting} type="submit">
                  {isSubmitting
                    ? 'Guardando...'
                    : modalMode === 'create'
                      ? 'Crear usuario'
                      : 'Guardar cambios'}
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}
    </section>
  );
}

export default SettingsPage;
