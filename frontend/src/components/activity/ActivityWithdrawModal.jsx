import { useEffect, useState } from 'react';
import { AlertTriangle, X } from 'lucide-react';

const DEFAULT_REASONS = [
  'Publicado por error',
  'Información incorrecta',
  'Mensaje duplicado',
  'Archivo incorrecto',
  'Otro',
];

export default function ActivityWithdrawModal({
  open,
  busy = false,
  reasons = DEFAULT_REASONS,
  onCancel,
  onConfirm,
}) {
  const [reason, setReason] = useState(reasons[0] ?? '');
  const [note, setNote] = useState('');

  useEffect(() => {
    if (!open) {
      setReason(reasons[0] ?? '');
      setNote('');
    }
  }, [open, reasons]);

  if (!open) {
    return null;
  }

  function handleSubmit(event) {
    event.preventDefault();

    if (!reason.trim()) {
      return;
    }

    onConfirm({
      reason: reason.trim(),
      note: note.trim() || null,
    });
  }

  return (
    <div
      className="activity-modal-backdrop"
      onClick={busy ? undefined : onCancel}
    >
      <div
        className="activity-modal"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="activity-modal-header">
          <div className="activity-modal-title">
            <AlertTriangle size={20} />
            <h3>Retirar mensaje</h3>
          </div>

          <button
            type="button"
            className="activity-modal-close"
            onClick={onCancel}
            disabled={busy}
          >
            <X size={18} />
          </button>
        </header>

        <form onSubmit={handleSubmit}>
          <div className="activity-modal-body">

            <label>
              Motivo

              <select
                value={reason}
                disabled={busy}
                onChange={(e) => setReason(e.target.value)}
              >
                {reasons.map((item) => (
                  <option
                    key={item}
                    value={item}
                  >
                    {item}
                  </option>
                ))}
              </select>
            </label>

            <label>
              Nota (opcional)

              <textarea
                rows={4}
                disabled={busy}
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder="Información adicional..."
              />
            </label>

          </div>

          <footer className="activity-modal-footer">

            <button
              type="button"
              className="secondary"
              disabled={busy}
              onClick={onCancel}
            >
              Cancelar
            </button>

            <button
              type="submit"
              className="danger"
              disabled={busy}
            >
              Retirar mensaje
            </button>

          </footer>
        </form>
      </div>
    </div>
  );
}