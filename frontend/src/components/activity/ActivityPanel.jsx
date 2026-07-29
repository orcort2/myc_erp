import { useEffect, useMemo, useState } from 'react';
import {
  FileText,
  History,
  MessageSquare,
} from 'lucide-react';

import ActivityComposer from './ActivityComposer.jsx';
import ActivityConversation from './ActivityConversation.jsx';
import ActivityAttentionModal from './ActivityAttentionModal.jsx';
import ActivityFiles from './ActivityFiles.jsx';
import ActivityHistory from './ActivityHistory.jsx';
import ActivityWithdrawModal from './ActivityWithdrawModal.jsx';

import {
  addActivityAttachment,
  createActivityMessage,
  downloadActivityAttachment,
  getActivity,
  getCurrentUser,
  listActivityMentionableUsers,
  markActivityRead,
  requestActivityAttention,
  resolveActivityAttention,
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
  const [mentionUsers, setMentionUsers] = useState([]);

  const [body, setBody] = useState('');
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [mentionedUsers, setMentionedUsers] = useState([]);

  const [editingId, setEditingId] = useState(null);
  const [editingBody, setEditingBody] = useState('');

  const [withdrawTarget, setWithdrawTarget] = useState(null);
  const [attentionTarget, setAttentionTarget] = useState(null);

  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(false);
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
      setBody('');
      setSelectedFiles([]);
      setMentionedUsers([]);
      setError('');
      return undefined;
    }

    let cancelled = false;

    async function loadActivity() {
      setError('');
      setLoading(true);

      try {
        const [activity, user] = await Promise.all([
          getActivity(entityType, entityId),
          currentUser
            ? Promise.resolve(currentUser)
            : getCurrentUser(),
        ]);

        let users = [];

        if (activity.capabilities?.can_mention) {
          try {
            users = await listActivityMentionableUsers();
          } catch {
          /*
           * La conversación debe seguir disponible aunque el
           * catálogo de usuarios no pueda cargarse. En ese caso
           * solamente se desactiva temporalmente el autocompletado.
           */
            users = [];
          }
        }

        if (cancelled) {
          return;
        }

        setThread(activity);
        setCurrentUser(user);
        setMentionUsers(
          users.filter(
            (candidate) =>
              candidate?.is_active !== false
              && candidate?.id !== user?.id,
          ),
        );
        if (activity.unread_count > 0) {
          try {
            await markActivityRead(entityType, entityId);
            setThread((current) => current
              ? { ...current, unread_count: 0 }
              : current);
          } catch {
            // La lectura visible permanece disponible aunque falle el acuse.
          }
        }
      } catch (requestError) {
        if (cancelled) {
          return;
        }

        setError(
          requestError?.message
            || 'No fue posible cargar la actividad.',
        );
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void loadActivity();

    return () => {
      cancelled = true;
    };
  }, [entityType, entityId]);

  async function refresh() {
    if (!entityType || !entityId) {
      return false;
    }

    setError('');

    try {
      const activity = await getActivity(
        entityType,
        entityId,
      );

      setThread(activity);

      if (!currentUser) {
        const user = await getCurrentUser();
        setCurrentUser(user);
      }

      return true;
    } catch (requestError) {
      setError(
        requestError?.message
          || 'No fue posible actualizar la actividad.',
      );

      return false;
    }
  }

  function handleAddFiles(incomingFiles) {
    setSelectedFiles((currentFiles) => {
      const combinedFiles = [
        ...currentFiles,
        ...incomingFiles,
      ];

      return combinedFiles.filter(
        (file, index, filesArray) =>
          filesArray.findIndex(
            (candidate) =>
              candidate.name === file.name
              && candidate.size === file.size
              && candidate.lastModified === file.lastModified,
          ) === index,
      );
    });
  }

  function handleRemoveFile(fileIndex) {
    setSelectedFiles((currentFiles) =>
      currentFiles.filter(
        (_, index) => index !== fileIndex,
      ),
    );
  }

  function appendMessageToThread(message) {
    setThread((currentThread) => {
      if (!currentThread) {
        return {
          messages: [message],
        };
      }

      const currentMessages =
        currentThread.messages ?? [];

      const alreadyExists = currentMessages.some(
        (currentMessage) =>
          currentMessage.id === message.id,
      );

      if (alreadyExists) {
        return currentThread;
      }

      return {
        ...currentThread,
        messages: [
          ...currentMessages,
          message,
        ],
      };
    });
  }

  async function handleSubmit() {
    const trimmedBody = body.trim();

    if (
      busy
      || (
        !trimmedBody
        && selectedFiles.length === 0
      )
    ) {
      return;
    }

    const filesToUpload = [...selectedFiles];

    setBusy(true);
    setError('');

    let createdMessage;

    try {
      createdMessage = await createActivityMessage(
        entityType,
        entityId,
        {
          body: trimmedBody || 'Archivo adjunto',
          mentioned_user_ids: mentionedUsers.map(
            (user) => user.id,
          ),
        },
      );
    } catch (requestError) {
      setError(
        requestError?.message
          || 'No fue posible crear el mensaje.',
      );

      setBusy(false);
      return;
    }

    /*
     * El mensaje ya existe en el servidor.
     * Lo agregamos inmediatamente al estado local.
     */
    appendMessageToThread(createdMessage);

    /*
     * Limpiamos el compositor después de crear correctamente
     * el mensaje. Los archivos que fallen se restaurarán después.
     */
    setBody('');
    setSelectedFiles([]);
    setMentionedUsers([]);

    if (filesToUpload.length === 0) {
      setBusy(false);
      return;
    }

    const failedFiles = [];

    for (const file of filesToUpload) {
      try {
        await addActivityAttachment(
          createdMessage.id,
          file,
        );
      } catch {
        failedFiles.push(file);
      }
    }

    /*
     * Restauramos exclusivamente los archivos que no pudieron
     * subirse. Los que sí fueron enviados no vuelven al compositor.
     */
    if (failedFiles.length > 0) {
      setSelectedFiles(failedFiles);

      setError(
        failedFiles.length === 1
          ? `No fue posible subir el archivo: ${failedFiles[0].name}`
          : `No fue posible subir ${failedFiles.length} archivos.`,
      );
    }

    /*
     * Recuperamos la estructura definitiva del mensaje y sus
     * adjuntos. Si esta actualización falla, no restauramos
     * archivos que ya fueron enviados.
     */
    await refresh();

    setBusy(false);
  }

  async function confirmAttention(payload) {
    if (!attentionTarget || busy) {
      return;
    }
    setBusy(true);
    setError('');
    try {
      await requestActivityAttention(attentionTarget.id, payload);
      setAttentionTarget(null);
      await refresh();
    } catch (requestError) {
      setError(
        requestError?.message
          || 'No fue posible solicitar la atención.',
      );
    } finally {
      setBusy(false);
    }
  }

  async function handleResolveAttention(attention) {
    if (busy) {
      return;
    }
    setBusy(true);
    setError('');
    try {
      await resolveActivityAttention(attention.id);
      await refresh();
    } catch (requestError) {
      setError(
        requestError?.message
          || 'No fue posible resolver la atención.',
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
          .map(
            (mention) =>
              mention.mentioned_user_id,
          ),
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
    if (busy) {
      return;
    }

    setWithdrawTarget(message);
  }

  async function confirmWithdraw({
    reason,
    note,
  }) {
    if (!withdrawTarget || busy) {
      return;
    }

    setBusy(true);
    setError('');

    try {
      await withdrawActivityMessage(
        withdrawTarget.id,
        {
          reason,
          note,
        },
      );

      if (editingId === withdrawTarget.id) {
        setEditingId(null);
        setEditingBody('');
      }

      setWithdrawTarget(null);

      await refresh();
    } catch (requestError) {
      setError(
        requestError?.message
          || 'No fue posible retirar el mensaje.',
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

  function handleCancelWithdraw() {
    if (busy) {
      return;
    }

    setWithdrawTarget(null);
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
          onClick={() =>
            setActiveTab('conversation')
          }
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
          onClick={() =>
            setActiveTab('files')
          }
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
          onClick={() =>
            setActiveTab('history')
          }
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

      {loading ? (
        <div className="activity-loading" role="status">
          Cargando actividad…
        </div>
      ) : null}

      {!loading && activeTab === 'conversation' ? (
        <>
          <ActivityConversation
            busy={busy}
            capabilities={thread?.capabilities}
            currentUser={currentUser}
            editingBody={editingBody}
            editingId={editingId}
            messages={messages}
            onCancelEdit={handleCancelEdit}
            onDownloadAttachment={
              downloadActivityAttachment
            }
            onEditingBodyChange={
              setEditingBody
            }
            onSaveEdit={handleSaveEdit}
            onRequestAttention={setAttentionTarget}
            onResolveAttention={handleResolveAttention}
            onStartEdit={handleStartEdit}
            onWithdraw={handleWithdraw}
          />

          {thread?.capabilities?.can_create ? (
            <ActivityComposer
              body={body}
              busy={busy}
              mentionUsers={
                thread?.capabilities?.can_mention
                  ? mentionUsers
                  : []
              }
              mentionedUsers={mentionedUsers}
              onBodyChange={setBody}
              onFilesChange={
                thread?.capabilities?.can_attach_files
                  ? handleAddFiles
                  : () => {}
              }
              onMentionedUsersChange={
                setMentionedUsers
              }
              onRemoveFile={handleRemoveFile}
              onSubmit={handleSubmit}
              selectedFiles={selectedFiles}
            />
          ) : null}
        </>
      ) : null}

      {activeTab === 'files' ? (
        <ActivityFiles
          files={files}
          onDownloadAttachment={
            downloadActivityAttachment
          }
        />
      ) : null}

      {activeTab === 'history' ? (
        <ActivityHistory messages={messages} />
      ) : null}

      <ActivityWithdrawModal
        busy={busy}
        onCancel={handleCancelWithdraw}
        onConfirm={confirmWithdraw}
        open={Boolean(withdrawTarget)}
        reasons={WITHDRAW_REASONS}
      />

      <ActivityAttentionModal
        busy={busy}
        message={attentionTarget}
        onCancel={() => setAttentionTarget(null)}
        onConfirm={confirmAttention}
        users={mentionUsers}
      />
    </section>
  );
}
