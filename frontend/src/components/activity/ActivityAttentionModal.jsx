import { useEffect, useState } from 'react';
import { AlertCircle, X } from 'lucide-react';

const PRIORITIES = [
  ['low', 'Baja'],
  ['normal', 'Normal'],
  ['high', 'Alta'],
  ['urgent', 'Urgente'],
];

export default function ActivityAttentionModal({
  busy = false,
  message,
  onCancel,
  onConfirm,
  users = [],
}) {
  const [assignedUserId, setAssignedUserId] = useState('');
  const [assignedArea, setAssignedArea] = useState('');
  const [priority, setPriority] = useState('normal');

  useEffect(() => {
    if (message) {
      setAssignedUserId('');
      setAssignedArea('');
      setPriority('normal');
    }
  }, [message]);

  if (!message) {
    return null;
  }

  const validTarget = Boolean(assignedUserId || assignedArea.trim());

  return (
    <div className="activity-modal-backdrop" role="presentation">
      <section
        aria-labelledby="activity-attention-title"
        aria-modal="true"
        className="activity-modal activity-attention-modal"
        role="dialog"
      >
        <header className="activity-modal-header">
          <div className="activity-modal-title">
            <AlertCircle aria-hidden="true" size={19} />
            <h3 id="activity-attention-title">Solicitar atención</h3>
          </div>
          <button
            aria-label="Cerrar"
            className="activity-modal-close"
            disabled={busy}
            onClick={onCancel}
            type="button"
          >
            <X aria-hidden="true" size={18} />
          </button>
        </header>

        <div className="activity-modal-body">
          <p>
            Asigna el seguimiento a una persona o a un área. La solicitud
            quedará ligada a este mensaje y será auditable.
          </p>

          <label>
            Responsable
            <select
              disabled={busy}
              onChange={(event) => setAssignedUserId(event.target.value)}
              value={assignedUserId}
            >
              <option value="">Sin responsable individual</option>
              {users.map((user) => (
                <option key={user.id} value={user.id}>
                  {user.full_name} {user.role_name ? `· ${user.role_name}` : ''}
                </option>
              ))}
            </select>
          </label>

          <label>
            Área
            <input
              disabled={busy}
              maxLength={80}
              onChange={(event) => setAssignedArea(event.target.value)}
              placeholder="Ej. Calidad, Finanzas, Operaciones"
              value={assignedArea}
            />
          </label>

          <label>
            Prioridad
            <select
              disabled={busy}
              onChange={(event) => setPriority(event.target.value)}
              value={priority}
            >
              {PRIORITIES.map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </label>
        </div>

        <footer className="activity-modal-footer">
          <button disabled={busy} onClick={onCancel} type="button">
            Cancelar
          </button>
          <button
            disabled={busy || !validTarget}
            onClick={() => onConfirm({
              assigned_user_id: assignedUserId
                ? Number(assignedUserId)
                : null,
              assigned_area: assignedArea.trim() || null,
              priority,
            })}
            type="button"
          >
            Solicitar atención
          </button>
        </footer>
      </section>
    </div>
  );
}
