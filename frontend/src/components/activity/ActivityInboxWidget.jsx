import { useEffect, useState } from 'react';
import { AlertCircle, ArrowRight, Inbox, MessageSquare } from 'lucide-react';

import { listActivityInbox } from '../../services/api.js';
import { navigate } from '../../utils/routing.js';

import './activity-inbox.css';

export default function ActivityInboxWidget() {
  const [inbox, setInbox] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;

    async function load() {
      try {
        const result = await listActivityInbox({ limit: 1 });
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

  const unreadCount = inbox?.unread_count ?? 0;
  const pendingAttentionCount = inbox?.pending_attention_count ?? 0;
  const hasPendingActivity = unreadCount > 0 || pendingAttentionCount > 0;

  return (
    <section className="activity-inbox-widget activity-inbox-widget--summary" aria-label="Resumen de Actividad interna">
      <div className="activity-inbox-widget__summary-copy">
        <span className="activity-inbox-widget__summary-icon" aria-hidden="true">
          {hasPendingActivity ? <MessageSquare size={22} /> : <Inbox size={22} />}
        </span>
        <div>
          <p>Comunicación interna</p>
          <h2 className="dashboard-title">Actividad</h2>
          <span className="activity-inbox-widget__summary-text">
            {hasPendingActivity
              ? 'Tienes elementos pendientes de revisión.'
              : 'No tienes actividad pendiente.'}
          </span>
        </div>
      </div>

      <div className="activity-inbox-widget__summary-actions">
        <div className="activity-inbox-widget__totals" aria-label="Contadores de Actividad">
          <span>
            <MessageSquare aria-hidden="true" size={15} />
            <strong>{unreadCount}</strong> sin leer
          </span>
          <span>
            <AlertCircle aria-hidden="true" size={15} />
            <strong>{pendingAttentionCount}</strong> por atender
          </span>
        </div>

        <button
          className="activity-inbox-widget__open"
          onClick={() => navigate('/communications')}
          type="button"
        >
          Ver actividad
          <ArrowRight aria-hidden="true" size={17} />
        </button>
      </div>
    </section>
  );
}
