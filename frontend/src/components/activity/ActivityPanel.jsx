import { useEffect, useMemo, useState } from 'react';
import {
  FileText,
  History,
  MessageSquare,
} from 'lucide-react';

import ActivityComposer from './ActivityComposer.jsx';
import ActivityConversation from './ActivityConversation.jsx';
import ActivityFiles from './ActivityFiles.jsx';
import ActivityHistory from './ActivityHistory.jsx';
import ActivityWithdrawModal from './ActivityWithdrawModal.jsx';

import {
  addActivityAttachment,
  createActivityMessage,
  downloadActivityAttachment,
  getActivity,
  getCurrentUser,
  updateActivityMessage,
  withdrawActivityMessage,
} from '../../services/api.js';

import './activity.css';

const WITHDRAW_REASONS = [
  'Publicado por error',
  'Información incorrecta',
  'Mensaje duplicado',
  'Archivo incorrecto',
  'Otro',
];


export default function ActivityPanel({
  entityType,
  entityId,
}) {
  const [activeTab, setActiveTab] = useState('conversation');
  const [thread, setThread] = useState(null);
  const [currentUser, setCurrentUser] = useState(null);

  const [body, setBody] = useState('');
  const [selectedFile, setSelectedFile] = useState(null);

  const [editingId, setEditingId] = useState(null);
  const [editingBody, setEditingBody] = useState('');

  const [withdrawTarget, setWithdrawTarget] = useState(null);

  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const messages = thread?.messages ?? [];

  const files = useMemo(
    () =>
      messages.flatMap((message) =>
        (message.attachments ?? []).map((attachment) => ({
          message,
          attachment,
        })),
      ),
    [messages],
  );

  useEffect(() => {
    if (!entityType || !entityId) {
      setThread(null);
      setError('');
      return;
    }

    let cancelled = false;

    async function loadActivity() {
      setError('');

      try {
        const [activity, user] = await Promise.all([
          getActivity(entityType, entityId),
          currentUser
            ? Promise.resolve(currentUser)
            : getCurrentUser(),
        ]);

        if (cancelled) {
          return;
        }

        setThread(activity);
        setCurrentUser(user);
      } catch (requestError) {
        if (cancelled) {
          return;
        }

        setError(
          requestError?.message
            || 'No fue posible cargar la actividad.',
        );
      }
    }

    void loadActivity();

    return () => {
      cancelled = true;
    };
  }, [entityType, entityId]);

  async function refresh() {
    if (!entityType || !entityId) {
      return;
    }

    setError('');

    try {
      const activity = await getActivity(entityType, entityId);
      setThread(activity);

      if (!currentUser) {
        const user = await getCurrentUser();
        setCurrentUser(user);
      }
    } catch (requestError) {
      setError(
        requestError?.message
          || 'No fue posible actualizar la actividad.',
      );
    }
  }

  async function handleSubmit(event) {
    event.preventDefault();

    const trimmedBody = body.trim();

    if (!trimmedBody || busy) {
      return;
    }

    setBusy(true);
    setError('');

    try {
      const message = await createActivityMessage(
        entityType,
        entityId,
        {
          body: trimmedBody,
          mentioned_user_ids: [],
        },
      );

      if (selectedFile) {
        await addActivityAttachment(
          message.id,
          selectedFile,
        );
      }

      setBody('');
      setSelectedFile(null);

      await refresh();
    } catch (requestError) {
      setError(
        requestError?.message
          || 'No fue posible publicar el mensaje.',
      );
    } finally {
      setBusy(false);
    }
  }

  async function handleSaveEdit(message) {
    const trimmedBody = editingBody.trim();

    if (!trimmedBody || busy) {
      return;
    }

    setBusy(true);
    setError('');

    try {
      await updateActivityMessage(message.id, {
        body: trimmedBody,
        reason: 'Corrección realizada por el autor',
        mentioned_user_ids: (message.mentions ?? [])
          .filter((mention) => !mention.revoked_at)
          .map((mention) => mention.mentioned_user_id),
      });

      setEditingId(null);
      setEditingBody('');

      await refresh();
    } catch (requestError) {
      setError(
        requestError?.message
          || 'No fue posible actualizar el mensaje.',
      );
    } finally {
      setBusy(false);
    }
  }

  function handleWithdraw(message) {
    setWithdrawTarget(message);
  }

  async function confirmWithdraw({ reason, note }) {
    if (!withdrawTarget || busy) {
      return;
    }

    setBusy(true);
    setError('');

    try {
      await withdrawActivityMessage(withdrawTarget.id, {
        reason,
        note,
      });

      if (editingId === withdrawTarget.id) {
        setEditingId(null);
        setEditingBody('');
      }

      setWithdrawTarget(null);

      await refresh();
    } catch (requestError) {
      setError(
        requestError?.message ??
          'No fue posible retirar el mensaje.',
      );
    } finally {
      setBusy(false);
    }
  }

  function handleStartEdit(message) {
    setEditingId(message.id);
    setEditingBody(message.body ?? '');
  }

  function handleCancelEdit() {
    setEditingId(null);
    setEditingBody('');
  }

  if (!entityType || !entityId) {
    return (
      <div className="activity-empty-state">
        <MessageSquare
          aria-hidden="true"
          size={30}
        />

        <strong>
          Actividad disponible al guardar el expediente
        </strong>

        <span>
          Guarda primero el registro para iniciar su conversación
          y trazabilidad.
        </span>
      </div>
    );
  }

  return (
    <section className="activity-panel">
      <nav
        aria-label="Actividad"
        className="activity-tabs"
      >
        <button
          className={
            activeTab === 'conversation'
              ? 'is-active'
              : ''
          }
          onClick={() => setActiveTab('conversation')}
          type="button"
        >
          <MessageSquare
            aria-hidden="true"
            size={16}
          />

          Conversación
        </button>

        <button
          className={
            activeTab === 'files'
              ? 'is-active'
              : ''
          }
          onClick={() => setActiveTab('files')}
          type="button"
        >
          <FileText
            aria-hidden="true"
            size={16}
          />

          Archivos

          <span>{files.length}</span>
        </button>

        <button
          className={
            activeTab === 'history'
              ? 'is-active'
              : ''
          }
          onClick={() => setActiveTab('history')}
          type="button"
        >
          <History
            aria-hidden="true"
            size={16}
          />

          Historial
        </button>
      </nav>

      {error ? (
        <div
          className="activity-error"
          role="alert"
        >
          {error}
        </div>
      ) : null}

      {activeTab === 'conversation' ? (
        <>
          <ActivityConversation
            busy={busy}
            currentUser={currentUser}
            editingBody={editingBody}
            editingId={editingId}
            messages={messages}
            onCancelEdit={handleCancelEdit}
            onDownloadAttachment={downloadActivityAttachment}
            onEditingBodyChange={setEditingBody}
            onSaveEdit={handleSaveEdit}
            onStartEdit={handleStartEdit}
            onWithdraw={handleWithdraw}
          />

          <ActivityComposer
            body={body}
            busy={busy}
            onBodyChange={setBody}
            onFileChange={setSelectedFile}
            onRemoveFile={() => setSelectedFile(null)}
            onSubmit={handleSubmit}
            selectedFile={selectedFile}
          />
        </>
      ) : null}

      {activeTab === 'files' ? (
        <ActivityFiles
          files={files}
          onDownloadAttachment={downloadActivityAttachment}
        />
      ) : null}

      {activeTab === 'history' ? (
        <ActivityHistory messages={messages} />
      ) : null}

      <ActivityWithdrawModal
        open={Boolean(withdrawTarget)}
        busy={busy}
        reasons={WITHDRAW_REASONS}
        onCancel={() => setWithdrawTarget(null)}
        onConfirm={confirmWithdraw}
        />
    </section>
  );
}