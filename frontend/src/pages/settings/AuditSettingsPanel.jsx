import React, { useEffect, useMemo, useState } from 'react';

import { listAuditLogs, listUsers } from '../../services/api.js';

const DEFAULT_FILTERS = {
  action: '',
  entity: '',
  user_id: '',
  limit: '100'
};

function formatAuditValue(value) {
  if (value === null || value === undefined || value === '') {
    return 'Sin dato';
  }
  if (Array.isArray(value)) {
    return value.length ? value.join(', ') : 'Sin dato';
  }
  if (typeof value === 'boolean') {
    return value ? 'Activo' : 'Inactivo';
  }
  return String(value);
}

function buildAuditSummary(log) {
  const beforeValues = log.previous_values ?? {};
  const afterValues = log.new_values ?? {};
  const changedKeys = Array.from(
    new Set([...Object.keys(beforeValues), ...Object.keys(afterValues)])
  ).filter((key) => JSON.stringify(beforeValues[key]) !== JSON.stringify(afterValues[key]));

  if (!changedKeys.length) {
    return log.comment || 'Sin detalle adicional';
  }

  return changedKeys
    .map((key) => `${key}: ${formatAuditValue(beforeValues[key])} -> ${formatAuditValue(afterValues[key])}`)
    .join(' | ');
}

function AuditSettingsPanel() {
  const [logs, setLogs] = useState([]);
  const [users, setUsers] = useState([]);
  const [filters, setFilters] = useState(DEFAULT_FILTERS);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedLog, setSelectedLog] = useState(null);

  const actionOptions = useMemo(() => {
    const actions = new Set(logs.map((log) => log.action).filter(Boolean));
    return Array.from(actions).sort();
  }, [logs]);

  const entityOptions = useMemo(() => {
    const entities = new Set(logs.map((log) => log.entity).filter(Boolean));
    return Array.from(entities).sort();
  }, [logs]);

  useEffect(() => {
    loadAuditData(DEFAULT_FILTERS);
    loadUsers();
  }, []);

  async function loadUsers() {
    try {
      const data = await listUsers();
      setUsers(Array.isArray(data) ? data : []);
    } catch {
      setUsers([]);
    }
  }

  async function loadAuditData(nextFilters = filters) {
    setError('');
    setIsLoading(true);

    try {
      const params = {
        action: nextFilters.action || undefined,
        entity: nextFilters.entity || undefined,
        user_id: nextFilters.user_id || undefined,
        limit: Number(nextFilters.limit || 100)
      };
      const data = await listAuditLogs(params);
      setLogs(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  }

  function handleFilterChange(event) {
    const { name, value } = event.target;
    setFilters((current) => ({
      ...current,
      [name]: value
    }));
  }

  function handleFilterSubmit(event) {
    event.preventDefault();
    loadAuditData(filters);
  }

  function handleResetFilters() {
    setFilters(DEFAULT_FILTERS);
    loadAuditData(DEFAULT_FILTERS);
  }

  return (
    <section className="settings-panel">
      {error ? <div className="form-error dashboard-error">{error}</div> : null}

      <div className="section-heading">
        <div>
          <p>Auditoria</p>
          <h2>{isLoading ? 'Cargando...' : `${logs.length} registros`}</h2>
        </div>
      </div>

      <form className="settings-filters" onSubmit={handleFilterSubmit}>
        <label className="field-label">
          Accion
          <select
            className="settings-role-select"
            name="action"
            onChange={handleFilterChange}
            value={filters.action}
          >
            <option value="">Todas</option>
            {actionOptions.map((action) => (
              <option key={action} value={action}>
                {action}
              </option>
            ))}
          </select>
        </label>

        <label className="field-label">
          Entidad
          <select
            className="settings-role-select"
            name="entity"
            onChange={handleFilterChange}
            value={filters.entity}
          >
            <option value="">Todas</option>
            {entityOptions.map((entity) => (
              <option key={entity} value={entity}>
                {entity}
              </option>
            ))}
          </select>
        </label>

        <label className="field-label">
          Usuario
          <select
            className="settings-role-select"
            name="user_id"
            onChange={handleFilterChange}
            value={filters.user_id}
          >
            <option value="">Todos</option>
            {users.map((user) => (
              <option key={user.id} value={user.id}>
                {user.full_name}
              </option>
            ))}
          </select>
        </label>

        <label className="field-label">
          Limite
          <select
            className="settings-role-select"
            name="limit"
            onChange={handleFilterChange}
            value={filters.limit}
          >
            <option value="25">25</option>
            <option value="50">50</option>
            <option value="100">100</option>
            <option value="200">200</option>
          </select>
        </label>

        <div className="settings-filters__actions">
          <button className="secondary-button" onClick={handleResetFilters} type="button">
            Limpiar
          </button>
          <button className="primary-button" type="submit">
            Filtrar
          </button>
        </div>
      </form>

        <div className="audit-log-table">
          <div className="audit-log-table__head">
          <span>Fecha</span>
          <span>Usuario</span>
          <span>Accion</span>
          <span>Entidad</span>
          <span>ID entidad</span>
          <span>Resumen del cambio</span>
        </div>

        {isLoading ? (
          <div className="clients-empty">Cargando auditoria...</div>
        ) : logs.length ? (
          logs.map((log) => (
            <div
              className="audit-log-table__row audit-log-row"
              key={log.id}
              onClick={() => setSelectedLog(log)}
              role="button"
              tabIndex={0}
              onKeyDown={(event) =>{
                if (event.key === 'Enter'){
                  setSelectedLog(log);
                }
              }}>
              <span>{new Date(log.created_at).toLocaleString('es-MX')}</span>
              <span>{log.user_name ?? 'Sistema'}</span>
              <span>
                <span className="settings-audit-badge">{log.action}</span>
              </span>
              <span>{log.entity}</span>
              <span>{log.entity_id ?? 'N/A'}</span>
              <span className="settings-audit-summary">{buildAuditSummary(log)}</span>
            </div>
          ))
        ) : (
          <div className="audit-log-empty">No hay registros de auditoria para los filtros seleccionados.</div>
        )}
      </div>

              {selectedLog ? (
          <div className="modal-backdrop" role="presentation" onClick={() => setSelectedLog(null)}>
            <section
              className="client-modal audit-detail-modal"
              aria-modal="true"
              role="dialog"
              onClick={(event) => event.stopPropagation()}
            >
              <div className="section-heading">
                <div>
                  <p>Detalle de auditoría</p>
                  <h2>{selectedLog.action}</h2>
                  <span>
                    {new Date(selectedLog.created_at).toLocaleString('es-MX')} · {selectedLog.user_name ?? 'Sistema'}
                  </span>
                </div>
                <button className="icon-text-button" type="button" onClick={() => setSelectedLog(null)}>
                  Cerrar
                </button>
              </div>

              <div className="audit-detail-grid">
                <article>
                  <span>Entidad</span>
                  <strong>{selectedLog.entity}</strong>
                </article>
                <article>
                  <span>ID entidad</span>
                  <strong>{selectedLog.entity_id ?? 'N/A'}</strong>
                </article>
                <article>
                  <span>Usuario</span>
                  <strong>{selectedLog.user_name ?? 'Sistema'}</strong>
                </article>
                <article>
                  <span>Comentario</span>
                  <strong>{selectedLog.comment ?? 'Sin comentario'}</strong>
                </article>
              </div>

              <div className="audit-detail-values">
                <article>
                  <h3>Antes</h3>
                  <pre>{JSON.stringify(selectedLog.previous_values ?? {}, null, 2)}</pre>
                </article>
                <article>
                  <h3>Después</h3>
                  <pre>{JSON.stringify(selectedLog.new_values ?? {}, null, 2)}</pre>
                </article>
              </div>
            </section>
          </div>
        ) : null}
    </section>
  );
}

export default AuditSettingsPanel;
