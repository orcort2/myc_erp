import { MessageSquare } from 'lucide-react';

import ActivityMessage from './ActivityMessage.jsx';

export default function ActivityConversation({
  messages,
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
}) {
  if (messages.length === 0) {
    return (
      <div className="activity-stream">
        <div className="activity-empty-state">
          <MessageSquare aria-hidden="true" size={28} />
          <strong>Sin actividad todavía</strong>
          <span>Escribe el primer comentario de este expediente.</span>
        </div>
      </div>
    );
  }

  return (
    <div className="activity-stream">
      {messages.map((message) => (
        <ActivityMessage
          key={message.id}
          busy={busy}
          currentUser={currentUser}
          editingBody={editingBody}
          editingId={editingId}
          message={message}
          onCancelEdit={onCancelEdit}
          onDownloadAttachment={onDownloadAttachment}
          onEditingBodyChange={onEditingBodyChange}
          onSaveEdit={onSaveEdit}
          onStartEdit={onStartEdit}
          onWithdraw={onWithdraw}
        />
      ))}
    </div>
  );
}