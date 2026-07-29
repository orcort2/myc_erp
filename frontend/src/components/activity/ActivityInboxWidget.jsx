import { useEffect, useState } from 'react';
import { AlertCircle, Inbox, MessageSquare } from 'lucide-react';

import { listActivityInbox } from '../../services/api.js';
import { navigate } from '../../utils/routing.js';

import './activity-inbox.css';

function formatDateTime(value) {
  if (!value) return '';
  return new Intl.DateTimeFormat('es-MX', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));
}

export default function ActivityInboxWidget() {
  const [inbox, setInbox] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    async function load() {
      try {
        const result = await listActivityInbox({ limit: 8 });
        if (active) {
          setInbox(result);
          setError('');
        }
      } catch (requestError) {
        if (active) {
          setError(requestError?.message || 'No fue posible cargar Actividad.');
        }
      }
    }
    void load();
    const interval = window.setInterval(load, 60000);
    return () => {
      active = false;
      window.clearInterval(interval);
    };
  }, []);

  if (error && !inbox) {
    return null;
  }

  const items = inbox?.items ?? [];

  return (
    <section className="activity-inbox-widget" aria-label="Bandeja de Actividad">
      <header>
        <div>
          <p>Comunicación interna</p>
          <h2>Actividad pendiente</h2>
        </div>
        <div className="activity-inbox-widget__totals">
          <span>
            <MessageSquare aria-hidden="true" size={15} />
            {inbox?.unread_count ?? 0} sin leer
          </span>
          <span>
            <AlertCircle aria-hidden="true" size={15} />
            {inbox?.pending_attention_count ?? 0} por atender
          </span>
        </div>
      </header>

      {items.length === 0 ? (
        <div className="activity-inbox-widget__empty">
          <Inbox aria-hidden="true" size={25} />
          <span>No tienes conversaciones pendientes.</span>
        </div>
      ) : (
        <div className="activity-inbox-widget__list">
          {items.map((item) => (
            <button
              key={item.thread_id}
              onClick={() => navigate(item.entity.frontend_path)}
              type="button"
            >
              <div>
                <strong>{item.entity.reference}</strong>
                <span>{item.last_message.body}</span>
              </div>
              <div>
                <time>{formatDateTime(item.last_message.created_at)}</time>
                <span>
                  {item.unread_count ? `${item.unread_count} sin leer` : ''}
                  {item.pending_attention_count
                    ? ` · ${item.pending_attention_count} atención`
                    : ''}
                </span>
              </div>
            </button>
          ))}
        </div>
      )}
    </section>
  );
}
