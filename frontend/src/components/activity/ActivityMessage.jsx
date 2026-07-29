import {
  AlertCircle,
  CheckCircle2,
  Download,
  Edit3,
  Paperclip,
  Send,
  Trash2,
  X,
} from 'lucide-react';
import {
  canEditActivityMessage,
  canResolveActivityAttention,
} from './activityEntities.js';

function formatDateTime(value) {
  if (!value) return '';

  return new Intl.DateTimeFormat('es-MX', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));
}

function formatBytes(bytes) {
  const value = Number(bytes || 0);

  if (value < 1024) {
    return `${value} B`;
  }

  if (value < 1024 * 1024) {
    return `${(value / 1024).toFixed(1)} KB`;
  }

  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

export default function ActivityMessage({
  message,
  capabilities = {},
  currentUser,
  editingId,
  editingBody,
  busy,
  onEditingBodyChange,
  onStartEdit,
  onCancelEdit,
  onSaveEdit,
  onWithdraw,
  onDownloadAttachment,
  onRequestAttention,
  onResolveAttention,
}) {
  const ownMessage = message.author?.id === currentUser?.id;
  const isEditing = editingId === message.id;

  const canEdit = canEditActivityMessage(
    message,
    currentUser,
    capabilities,
  );
  const canWithdraw = (
    (ownMessage && capabilities.can_delete_own)
    || (!ownMessage && capabilities.can_moderate)
  ) && !message.withdrawn_at && !message.is_system && !message.is_formal;
  const canRequestAttention = (
    capabilities.can_request_attention
    && !message.withdrawn_at
    && !message.is_system
  );
  const pendingAttention = (message.attention_requests ?? [])
    .filter((attention) => attention.status === 'pending');

  return (
    <article
      className={`activity-message ${
        message.is_system ? 'is-system' : ''
      }`}
    >
      <header>
        <div>
          <strong>{message.author?.full_name || 'Sistema'}</strong>
          <span>{formatDateTime(message.created_at)}</span>

          {message.edited_at ? <span>· Editado</span> : null}
        </div>

        {canEdit || canWithdraw || canRequestAttention ? (
          <div className="activity-message-actions">
            {canRequestAttention ? (
              <button
                aria-label="Solicitar atención"
                disabled={busy}
                onClick={() => onRequestAttention(message)}
                title="Solicitar atención"
                type="button"
              >
                <AlertCircle aria-hidden="true" size={15} />
              </button>
            ) : null}

            {canEdit ? (
              <button
                aria-label="Editar comentario"
                onClick={() => onStartEdit(message)}
                title="Editar"
                type="button"
              >
                <Edit3 aria-hidden="true" size={15} />
              </button>
            ) : null}

            {canWithdraw ? (
              <button
                aria-label="Retirar comentario"
                disabled={busy}
                onClick={() => onWithdraw(message)}
                title="Retirar"
                type="button"
              >
                <Trash2 aria-hidden="true" size={15} />
              </button>
            ) : null}
          </div>
        ) : null}
      </header>

      {message.withdrawn_at ? (
        <p className="activity-withdrawn">
          Mensaje retirado por el autor.
        </p>
      ) : isEditing ? (
        <div className="activity-edit-box">
          <textarea
            maxLength={10000}
            onChange={(event) =>
              onEditingBodyChange(event.target.value)
            }
            value={editingBody}
          />

          <div>
            <button
              disabled={busy}
              onClick={onCancelEdit}
              type="button"
            >
              <X aria-hidden="true" size={15} />
              Cancelar
            </button>

            <button
              disabled={busy || !editingBody.trim()}
              onClick={() => onSaveEdit(message)}
              type="button"
            >
              <Send aria-hidden="true" size={15} />
              Guardar
            </button>
          </div>
        </div>
      ) : (
        <p>{message.body}</p>
      )}

      {!message.withdrawn_at && message.attachments?.length ? (
        <div className="activity-attachments">
          {message.attachments.map((attachment) => (
            <button
              key={attachment.id}
              onClick={() => onDownloadAttachment(attachment)}
              type="button"
            >
              <Paperclip aria-hidden="true" size={15} />

              <span>
                {attachment.original_name}
                <small>{formatBytes(attachment.size_bytes)}</small>
              </span>

              <Download aria-hidden="true" size={15} />
            </button>
          ))}
        </div>
      ) : null}

      {pendingAttention.length ? (
        <div className="activity-attention-list">
          {pendingAttention.map((attention) => {
            const canResolve = canResolveActivityAttention(
              attention,
              currentUser,
              capabilities,
            );
            return (
              <div className={`activity-attention is-${attention.priority}`} key={attention.id}>
                <AlertCircle aria-hidden="true" size={17} />
                <div>
                  <strong>Atención {attention.priority}</strong>
                  <span>
                    {attention.assigned_user?.full_name
                      || attention.assigned_area
                      || 'Área responsable'}
                  </span>
                </div>
                {canResolve ? (
                  <button
                    disabled={busy}
                    onClick={() => onResolveAttention(attention)}
                    type="button"
                  >
                    <CheckCircle2 aria-hidden="true" size={15} />
                    Resolver
                  </button>
                ) : null}
              </div>
            );
          })}
        </div>
      ) : null}

      {message.revisions?.length ? (
        <details className="activity-revisions">
          <summary>
            Ver historial de edición ({message.revisions.length})
          </summary>

          {message.revisions.map((revision) => (
            <div key={revision.id}>
              <span>{formatDateTime(revision.created_at)}</span>
              <p>{revision.previous_body}</p>
            </div>
          ))}
        </details>
      ) : null}
    </article>
  );
}
