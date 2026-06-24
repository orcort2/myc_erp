import React from 'react';

function UserModal({
  availableRoles,
  form,
  isSubmitting,
  mode,
  onChange,
  onClose,
  onSubmit
}) {
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="client-modal settings-user-modal" onClick={(event) => event.stopPropagation()}>
        <div className="section-heading settings-user-modal__header">
          <div>
            <p>Usuarios</p>
            <h2>{mode === 'create' ? 'Nuevo usuario' : 'Editar usuario'}</h2>
          </div>

          <button className="secondary-button" type="button" onClick={onClose}>
            Cerrar
          </button>
        </div>

        <form className="settings-user-form" onSubmit={onSubmit}>
          <label className="field-label">
            Nombre completo
            <input
              className="text-input"
              name="full_name"
              onChange={onChange}
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
              onChange={onChange}
              placeholder="usuario@myc.com"
              type="email"
              value={form.email}
            />
          </label>

          {mode === 'create' ? (
            <label className="field-label">
              Contraseña
              <input
                className="text-input"
                name="password"
                onChange={onChange}
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
              onChange={onChange}
              value={form.role_name}
            >
              {availableRoles.map((role) => (
                <option key={role.id} value={role.name}>
                  {role.name}
                </option>
              ))}
            </select>
          </label>

          {mode === 'edit' ? (
            <label className="settings-checkbox">
              <input
                checked={form.is_active}
                name="is_active"
                onChange={onChange}
                type="checkbox"
              />
              Usuario activo
            </label>
          ) : null}

          <div className="client-form__actions--modal">
            <button className="secondary-button" onClick={onClose} type="button">
              Cancelar
            </button>
            <button className="primary-button" disabled={isSubmitting} type="submit">
              {isSubmitting
                ? 'Guardando...'
                : mode === 'create'
                  ? 'Crear usuario'
                  : 'Guardar cambios'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default UserModal;
