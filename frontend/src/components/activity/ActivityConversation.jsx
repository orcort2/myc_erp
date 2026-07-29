import {
  useEffect,
  useRef,
} from 'react';

import ActivityMessage from './ActivityMessage.jsx';

export default function ActivityConversation({
  busy,
  currentUser,
  editingBody,
  editingId,
  messages,
  onCancelEdit,
  onDownloadAttachment,
  onEditingBodyChange,
  onSaveEdit,
  onStartEdit,
  onWithdraw,
}) {
  const streamRef = useRef(null);
  const previousMessageCountRef = useRef(0);

  function scrollToBottom({
    behavior = 'auto',
  } = {}) {
    const stream = streamRef.current;

    if (!stream) {
      return;
    }

    stream.scrollTo({
      top: stream.scrollHeight,
      behavior,
    });
  }

  /*
   * Posiciona la conversación en el mensaje más reciente:
   *
   * - al cargar inicialmente los mensajes, sin animación;
   * - al recibir o publicar un mensaje nuevo, suavemente;
   * - al actualizar la colección de mensajes después de
   *   volver a abrir el Centro de Actividad.
   */
  useEffect(() => {
    const previousMessageCount =
      previousMessageCountRef.current;

    const currentMessageCount =
      messages.length;

    const behavior =
      previousMessageCount === 0
        ? 'auto'
        : currentMessageCount > previousMessageCount
          ? 'smooth'
          : 'auto';

    const frameId = window.requestAnimationFrame(() => {
      scrollToBottom({
        behavior,
      });

      previousMessageCountRef.current =
        currentMessageCount;
    });

    return () => {
      window.cancelAnimationFrame(frameId);
    };
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className="activity-stream">
        <div className="activity-empty-state">
          <strong>
            Todavía no hay actividad
          </strong>

          <span>
            Publica el primer comentario de este expediente.
          </span>
        </div>
      </div>
    );
  }

  return (
    <div
      className="activity-stream"
      ref={streamRef}
    >
      {messages.map((message) => (
        <ActivityMessage
          busy={busy}
          currentUser={currentUser}
          editingBody={editingBody}
          editingId={editingId}
          key={message.id}
          message={message}
          onCancelEdit={onCancelEdit}
          onDownloadAttachment={
            onDownloadAttachment
          }
          onEditingBodyChange={
            onEditingBodyChange
          }
          onSaveEdit={onSaveEdit}
          onStartEdit={onStartEdit}
          onWithdraw={onWithdraw}
        />
      ))}
    </div>
  );
}