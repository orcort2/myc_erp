import {
  Download,
  FileText,
} from 'lucide-react';

function formatBytes(bytes) {
  if (bytes === null || bytes === undefined) {
    return 'Tamaño no disponible';
  }

  const numericBytes = Number(bytes);

  if (
    Number.isNaN(numericBytes)
    || numericBytes < 0
  ) {
    return 'Tamaño no disponible';
  }

  if (numericBytes === 0) {
    return '0 B';
  }

  const units = ['B', 'KB', 'MB', 'GB'];
  const unitIndex = Math.min(
    Math.floor(
      Math.log(numericBytes) / Math.log(1024),
    ),
    units.length - 1,
  );

  const value =
    numericBytes / (1024 ** unitIndex);

  return `${value.toFixed(unitIndex === 0 ? 0 : 1)} ${units[unitIndex]}`;
}

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

function getAuthorName(message) {
  return (
    message.author?.full_name
    || message.author?.name
    || message.author_name
    || (message.is_system ? 'Sistema' : 'Usuario')
  );
}

export default function ActivityFiles({
  files = [],
  onDownloadAttachment,
}) {
  if (files.length === 0) {
    return (
      <div className="activity-file-list">
        <div className="activity-empty-state">
          <FileText
            aria-hidden="true"
            size={28}
          />

          <strong>Sin archivos adjuntos</strong>

          <span>
            Los archivos compartidos en la conversación aparecerán
            aquí.
          </span>
        </div>
      </div>
    );
  }

  return (
    <div className="activity-file-list">
      {files.map(({ message, attachment }, index) => {
        const attachmentName =
          attachment.original_name
          || attachment.filename
          || attachment.name
          || 'Archivo adjunto';

        const authorName = getAuthorName(message);
        const createdAt =
          attachment.created_at
          || message.created_at;

        return (
          <button
            aria-label={`Descargar ${attachmentName}`}
            className="activity-file-item"
            key={
              attachment.id
              || `${message.id}-${attachmentName}-${index}`
            }
            onClick={() =>
              onDownloadAttachment(attachment)
            }
            type="button"
          >
            <span className="activity-file-icon">
              <FileText
                aria-hidden="true"
                size={20}
              />
            </span>

            <span className="activity-file-content">
              <strong className="activity-file-name">
                {attachmentName}
              </strong>

              <span className="activity-file-details">
                <span>
                  {formatBytes(attachment.size_bytes)}
                </span>

                <span aria-hidden="true">•</span>

                <span>{authorName}</span>

                {createdAt ? (
                  <>
                    <span aria-hidden="true">•</span>

                    <span>
                      {formatDateTime(createdAt)}
                    </span>
                  </>
                ) : null}
              </span>
            </span>

            <span className="activity-file-download">
              <Download
                aria-hidden="true"
                size={17}
              />
            </span>
          </button>
        );
      })}
    </div>
  );
}