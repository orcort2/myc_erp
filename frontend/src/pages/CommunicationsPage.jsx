import {
  Bell,
  Building2,
  CheckCheck,
  MessageCircle,
  MessagesSquare,
  Plus,
  RefreshCw,
  Search,
  Send,
  UserRound,
  UsersRound,
  X,
} from 'lucide-react';
import { useEffect, useMemo, useRef, useState } from 'react';

import NotificationItem from '../components/notifications/NotificationItem.jsx';
import { useNotifications } from '../components/notifications/NotificationProvider.jsx';
import { openNotificationDestination } from '../components/notifications/notificationNavigation.js';
import {
  createCommunicationConversation,
  getCommunicationConversation,
  getCommunicationDirectory,
  listCommunicationConversations,
  sendCommunicationMessage,
} from '../services/api.js';
import fondoMensajeria from '../../assets/backgrounds/fondomensajeria.png';
import './communications.css';

const POLL_MS = 5000;

function formatMessageTime(value) {
  if (!value) return '';
  return new Intl.DateTimeFormat('es-MX', {
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value));
}

function NewConversationModal({ directory, onClose, onCreated }) {
  const [kind, setKind] = useState('internal');
  const [query, setQuery] = useState('');
  const [submittingId, setSubmittingId] = useState(null);
  const candidates = kind === 'internal' ? directory.users : directory.clients;
  const filtered = candidates.filter((item) => {
    const text = `${item.full_name || item.name || ''} ${item.email || ''}`.toLowerCase();
    return text.includes(query.toLowerCase());
  });

  async function choose(item) {
    setSubmittingId(item.id);
    try {
      const conversation = await createCommunicationConversation({
        conversation_type: kind,
        participant_user_id: kind === 'internal' ? item.id : null,
        client_id: kind === 'client' ? item.id : null,
      });
      onCreated(conversation);
    } finally {
      setSubmittingId(null);
    }
  }

  return (
    <div className="communications-modal-backdrop" role="presentation" onMouseDown={onClose}>
      <section className="communications-modal" role="dialog" aria-modal="true" aria-label="Nuevo mensaje" onMouseDown={(event) => event.stopPropagation()}>
        <header>
          <div>
            <strong>Nuevo mensaje</strong>
            <span>Inicia una conversación interna o con un cliente.</span>
          </div>
          <button aria-label="Cerrar" onClick={onClose} type="button"><X size={18} /></button>
        </header>

        <div className="communications-modal__types">
          <button className={kind === 'internal' ? 'is-active' : ''} onClick={() => setKind('internal')} type="button"><UsersRound size={16} /> Usuario</button>
          <button className={kind === 'client' ? 'is-active' : ''} onClick={() => setKind('client')} type="button"><Building2 size={16} /> Cliente</button>
        </div>

        <label className="communications-search">
          <Search size={16} />
          <input autoFocus onChange={(event) => setQuery(event.target.value)} placeholder={kind === 'internal' ? 'Buscar usuario…' : 'Buscar cliente…'} value={query} />
        </label>

        <div className="communications-modal__results">
          {filtered.map((item) => (
            <button disabled={submittingId !== null} key={item.id} onClick={() => choose(item)} type="button">
              <span className="communications-avatar">{kind === 'internal' ? <UserRound size={18} /> : <Building2 size={18} />}</span>
              <span><strong>{item.full_name || item.name}</strong><small>{item.email || 'Sin correo registrado'}</small></span>
              {submittingId === item.id ? <RefreshCw className="is-spinning" size={16} /> : null}
            </button>
          ))}
          {!filtered.length ? <div className="communications-empty-small">No se encontraron resultados.</div> : null}
        </div>
      </section>
    </div>
  );
}

export default function CommunicationsPage({ user }) {
  const [section, setSection] = useState('notifications');
  const [conversationKind, setConversationKind] = useState('internal');
  const [conversations, setConversations] = useState([]);
  const [selected, setSelected] = useState(null);
  const [directory, setDirectory] = useState({ users: [], clients: [] });
  const [query, setQuery] = useState('');
  const [draft, setDraft] = useState('');
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [sending, setSending] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [communicationError, setCommunicationError] = useState('');
  const messagesEndRef = useRef(null);
  const notifications = useNotifications();

  const visibleConversations = useMemo(() => conversations.filter((conversation) => {
    if (conversation.conversation_type !== conversationKind) return false;
    return conversation.title.toLowerCase().includes(query.toLowerCase());
  }), [conversationKind, conversations, query]);

  async function loadConversations({ silent = false } = {}) {
    try {
      const data = await listCommunicationConversations();
      setConversations(data || []);
      setCommunicationError('');
      if (selected?.id) {
        const detail = await getCommunicationConversation(selected.id);
        setSelected(detail);
      }
    } catch (error) {
      if (!silent) setCommunicationError(error?.message || 'No fue posible cargar las conversaciones.');
    }
  }

  useEffect(() => {
    Promise.all([loadConversations(), getCommunicationDirectory().then(setDirectory)]).catch(() => {});
    const timer = window.setInterval(() => loadConversations({ silent: true }), POLL_MS);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [selected?.messages?.length]);

  async function openConversation(conversation) {
    setLoadingMessages(true);
    try {
      setSelected(await getCommunicationConversation(conversation.id));
    } finally {
      setLoadingMessages(false);
    }
  }

  async function sendMessage(event) {
    event.preventDefault();
    const body = draft.trim();
    if (!body || !selected || sending) return;
    setSending(true);
    try {
      const message = await sendCommunicationMessage(selected.id, body);
      setSelected((current) => ({ ...current, messages: [...(current.messages || []), message], last_message: message, last_message_at: message.created_at }));
      setDraft('');
      await loadConversations({ silent: true });
    } finally {
      setSending(false);
    }
  }

  async function openNotification(notification) {
    try { await notifications.markRead(notification.id); } finally { openNotificationDestination(notification); }
  }

  function handleCreated(conversation) {
    setModalOpen(false);
    setSection('messages');
    setConversationKind(conversation.conversation_type);
    setSelected(conversation);
    loadConversations({ silent: true });
  }

  const filteredNotifications = notifications.notifications.filter((item) => item.title?.toLowerCase().includes(query.toLowerCase()) || item.body?.toLowerCase().includes(query.toLowerCase()));

  return (
    <section className="communications-page">
      <header className="communications-page__header">
        <div><h1>Comunicaciones</h1><p>Notificaciones, conversaciones internas y atención a clientes en un solo espacio.</p></div>
        <button className="communications-primary-button" onClick={() => setModalOpen(true)} type="button"><Plus size={17} /> Nuevo mensaje</button>
      </header>

      {communicationError ? <div className="communications-error">{communicationError}</div> : null}

      <div className="communications-shell">
        <aside className="communications-sidebar">
          <nav className="communications-sections" aria-label="Secciones de comunicaciones">
            <button className={section === 'notifications' ? 'is-active' : ''} onClick={() => { setSection('notifications'); setSelected(null); }} type="button">
              <Bell size={17} /><span>Notificaciones</span>{notifications.unreadCount ? <b>{notifications.unreadCount}</b> : null}
            </button>
            <button className={section === 'messages' && conversationKind === 'internal' ? 'is-active' : ''} onClick={() => { setSection('messages'); setConversationKind('internal'); setSelected(null); }} type="button"><MessagesSquare size={17} /><span>Mensajes internos</span></button>
            <button className={section === 'messages' && conversationKind === 'client' ? 'is-active' : ''} onClick={() => { setSection('messages'); setConversationKind('client'); setSelected(null); }} type="button"><Building2 size={17} /><span>Clientes</span></button>
            <button className="is-disabled" title="Se habilitará con el CRM" type="button"><MessageCircle size={17} /><span>Prospectos</span><small>Próximamente</small></button>
          </nav>

          <label className="communications-search communications-search--sidebar"><Search size={15} /><input onChange={(event) => setQuery(event.target.value)} placeholder="Buscar…" value={query} /></label>

          <div className="communications-list">
            {section === 'notifications' ? (
              <>
                <div className="communications-list__toolbar"><strong>Notificaciones</strong><button disabled={!notifications.unreadCount} onClick={notifications.markAllRead} title="Marcar todas como leídas" type="button"><CheckCheck size={16} /></button></div>
                {filteredNotifications.map((item) => <NotificationItem compact key={item.id} notification={item} onOpen={openNotification} />)}
                {!notifications.loading && !filteredNotifications.length ? <div className="communications-empty-small">No hay notificaciones.</div> : null}
              </>
            ) : (
              <>
                <div className="communications-list__toolbar"><strong>{conversationKind === 'internal' ? 'Mensajes internos' : 'Clientes'}</strong><button onClick={() => loadConversations()} title="Actualizar" type="button"><RefreshCw size={15} /></button></div>
                {visibleConversations.map((conversation) => (
                  <button className={`communications-conversation-row ${selected?.id === conversation.id ? 'is-active' : ''}`} key={conversation.id} onClick={() => openConversation(conversation)} type="button">
                    <span className="communications-avatar">{conversation.conversation_type === 'client' ? <Building2 size={18} /> : <UserRound size={18} />}</span>
                    <span><strong>{conversation.title}</strong><small>{conversation.last_message?.body || 'Conversación nueva'}</small></span>
                    <time>{formatMessageTime(conversation.last_message_at)}</time>
                  </button>
                ))}
                {!visibleConversations.length ? <div className="communications-empty-small">Todavía no hay conversaciones.</div> : null}
              </>
            )}
          </div>
        </aside>

        <main className={`communications-content ${selected ? 'has-conversation' : ''}`} style={{ '--communications-wallpaper': `url(${fondoMensajeria})` }}>
          {section === 'notifications' ? (
            <div className="communications-welcome">
              <span className="communications-welcome__icon"><Bell size={32} /></span>
              <h2>Centro de notificaciones</h2>
              <p>Selecciona una notificación en el panel izquierdo para abrir su actividad relacionada.</p>
              <button onClick={() => notifications.refresh()} type="button"><RefreshCw className={notifications.loading ? 'is-spinning' : ''} size={16} /> Actualizar</button>
            </div>
          ) : selected ? (
            <div className="communications-chat">
              <header className="communications-chat__header">
                <span className="communications-avatar communications-avatar--large">{selected.conversation_type === 'client' ? <Building2 size={22} /> : <UserRound size={22} />}</span>
                <div><strong>{selected.title}</strong><span>{selected.conversation_type === 'client' ? 'Cliente · canal atendido por MYC' : 'Conversación interna'}</span></div>
              </header>
              <div className="communications-chat__messages">
                {loadingMessages ? <div className="communications-loading"><RefreshCw className="is-spinning" size={20} /> Cargando conversación…</div> : null}
                {(selected.messages || []).map((message) => {
                  const own = message.sender.id === user?.id;
                  return <article className={`communications-bubble ${own ? 'is-own' : ''}`} key={message.id}><strong>{own ? 'Tú' : message.sender.full_name}</strong><p>{message.body}</p><time>{formatMessageTime(message.created_at)}</time></article>;
                })}
                {!loadingMessages && !(selected.messages || []).length ? <div className="communications-chat__empty">Escribe el primer mensaje de esta conversación.</div> : null}
                <div ref={messagesEndRef} />
              </div>
              <form className="communications-composer" onSubmit={sendMessage}>
                <textarea onChange={(event) => setDraft(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); sendMessage(event); } }} placeholder="Escribe un mensaje…" rows={1} value={draft} />
                <button disabled={!draft.trim() || sending} type="submit">{sending ? <RefreshCw className="is-spinning" size={18} /> : <Send size={18} />}</button>
              </form>
            </div>
          ) : (
            <div className="communications-welcome communications-welcome--wallpaper">
              <span className="communications-welcome__icon"><MessagesSquare size={34} /></span>
              <h2>{conversationKind === 'internal' ? 'Mensajería interna' : 'Atención a clientes'}</h2>
              <p>{conversationKind === 'internal' ? 'Selecciona una conversación o inicia una nueva con otro usuario del ERP.' : 'Concentra aquí la comunicación y el seguimiento de cada cliente.'}</p>
              <button onClick={() => setModalOpen(true)} type="button"><Plus size={16} /> Nuevo mensaje</button>
            </div>
          )}
        </main>

        {selected && section === 'messages' ? (
          <aside className="communications-details">
            <span className="communications-avatar communications-avatar--profile">{selected.conversation_type === 'client' ? <Building2 size={28} /> : <UserRound size={28} />}</span>
            <h3>{selected.title}</h3>
            <p>{selected.conversation_type === 'client' ? selected.client?.email || 'Sin correo registrado' : selected.participants?.find((item) => item.id !== user?.id)?.email || 'Usuario interno'}</p>
            <dl><div><dt>Canal</dt><dd>{selected.conversation_type === 'client' ? 'Cliente' : 'Interno'}</dd></div><div><dt>Creada</dt><dd>{formatMessageTime(selected.created_at)}</dd></div><div><dt>Mensajes</dt><dd>{selected.messages?.length || 0}</dd></div></dl>
            {selected.conversation_type === 'client' ? <small className="communications-details__note">La recepción desde el portal web quedará habilitada al conectar la identidad del cliente. Esta conversación ya conserva el historial institucional.</small> : null}
          </aside>
        ) : null}
      </div>

      {modalOpen ? <NewConversationModal directory={directory} onClose={() => setModalOpen(false)} onCreated={handleCreated} /> : null}
    </section>
  );
}
