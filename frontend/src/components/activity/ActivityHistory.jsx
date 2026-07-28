import { History } from 'lucide-react';

function formatDateTime(value) {
  if (!value) {
    return '';
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return '';
  }

  return new Intl.DateTimeFormat('es-MX', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date);
}

function getEventTitle(message) {
  return (
    message.event_title
    || message.title
    || 'Evento del sistema'
  );
}

export default function ActivityHistory({
  messages = [],
}) {
  const systemMessages = messages.filter(
    (message) => message.is_system,
  );

  if (systemMessages.length === 0) {
    return (
      <div className="activity-history-list">
        <div className="activity-empty-state">
          <History
            aria-hidden="true"
            size={28}
          />

          <strong>Sin eventos automáticos</strong>

          <span>
            Los cambios importantes del sistema se incorporarán aquí
            conforme se conecten los módulos.
          </span>
        </div>
      </div>
    );
  }

  return (
    <div className="activity-history-list">
      {systemMessages.map((message) => (
        <article
          className="activity-history-item"
          key={message.id}
        >
          <span
            aria-hidden="true"
            className="activity-history-marker"
          />

          <div className="activity-history-content">
            <div className="activity-history-header">
              <strong>
                {getEventTitle(message)}
              </strong>

              <time dateTime={message.created_at}>
                {formatDateTime(message.created_at)}
              </time>
            </div>

            <p>{message.body}</p>
          </div>
        </article>
      ))}
    </div>
  );
}