import { Paperclip, Send, X } from 'lucide-react';

export default function ActivityComposer({
  body,
  selectedFile,
  busy,
  onBodyChange,
  onFileChange,
  onRemoveFile,
  onSubmit,
}) {
  const canSubmit = Boolean(body.trim()) && !busy;

  return (
    <form className="activity-composer" onSubmit={onSubmit}>
      <textarea
        maxLength={10000}
        onChange={(event) => onBodyChange(event.target.value)}
        placeholder="Escribe un comentario interno…"
        value={body}
      />

      <div>
        <label className="activity-file-picker">
          <Paperclip aria-hidden="true" size={16} />

          <span>
            {selectedFile ? selectedFile.name : 'Adjuntar'}
          </span>

          <input
            accept=".pdf,.png,.jpg,.jpeg,.webp,.xlsx,.docx,.txt"
            onChange={(event) =>
              onFileChange(event.target.files?.[0] ?? null)
            }
            type="file"
          />
        </label>

        {selectedFile ? (
          <button
            aria-label="Quitar archivo adjunto"
            className="activity-file-remove"
            onClick={onRemoveFile}
            title="Quitar archivo"
            type="button"
          >
            <X aria-hidden="true" size={15} />
          </button>
        ) : null}

        <button
          className="activity-send"
          disabled={!canSubmit}
          type="submit"
        >
          <Send aria-hidden="true" size={16} />

          {busy ? 'Publicando…' : 'Publicar'}
        </button>
      </div>
    </form>
  );
}