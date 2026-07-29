import {
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import {
  AtSign,
  FilePlus2,
  Paperclip,
  Send,
  X,
} from 'lucide-react';

function formatBytes(bytes) {
  const numericBytes = Number(bytes ?? 0);

  if (!Number.isFinite(numericBytes) || numericBytes < 0) {
    return 'Tamaño no disponible';
  }

  if (numericBytes < 1024) {
    return `${numericBytes} B`;
  }

  if (numericBytes < 1024 * 1024) {
    return `${(numericBytes / 1024).toFixed(1)} KB`;
  }

  return `${(
    numericBytes /
    (1024 * 1024)
  ).toFixed(1)} MB`;
}

function hasDraggedFiles(event) {
  return Array.from(
    event.dataTransfer?.types ?? [],
  ).includes('Files');
}

function getUserName(user) {
  return (
    user?.full_name
    || user?.name
    || user?.email
    || `Usuario ${user?.id ?? ''}`
  ).trim();
}

function normalizeText(value) {
  return String(value ?? '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLocaleLowerCase('es-MX');
}

function getMentionSearch(body, cursorPosition) {
  const textBeforeCursor = body.slice(0, cursorPosition);
  const atIndex = textBeforeCursor.lastIndexOf('@');

  if (atIndex < 0) {
    return null;
  }

  const previousCharacter =
    atIndex > 0
      ? textBeforeCursor[atIndex - 1]
      : '';

  if (
    previousCharacter
    && !/\s|[([{]/.test(previousCharacter)
  ) {
    return null;
  }

  const query = textBeforeCursor.slice(atIndex + 1);

  if (
    query.includes('\n')
    || query.length > 80
    || /[.,;:!?()[\]{}<>/\\]/.test(query)
  ) {
    return null;
  }

  return {
    atIndex,
    query,
  };
}

function bodyContainsMention(body, user) {
  const mentionToken = `@${getUserName(user)}`;

  return normalizeText(body).includes(
    normalizeText(mentionToken),
  );
}

export default function ActivityComposer({
  body,
  busy = false,
  mentionUsers = [],
  mentionedUsers = [],
  selectedFiles = [],
  onBodyChange,
  onFilesChange,
  onMentionedUsersChange,
  onRemoveFile,
  onSubmit,
}) {
  const fileInputRef = useRef(null);
  const textareaRef = useRef(null);

  const [dragActive, setDragActive] = useState(false);
  const [mentionSearch, setMentionSearch] = useState(null);
  const [highlightedMentionIndex, setHighlightedMentionIndex] = useState(0);
  const [pendingCaretPosition, setPendingCaretPosition] = useState(null);

  const canSubmit =
    !busy
    && (
      body.trim().length > 0
      || selectedFiles.length > 0
    );

  const filteredMentionUsers = useMemo(() => {
    if (!mentionSearch) {
      return [];
    }

    const normalizedQuery = normalizeText(
      mentionSearch.query.trim(),
    );

    return mentionUsers
      .filter((user) => {
        if (!user || user.is_active === false) {
          return false;
        }

        const haystack = normalizeText(
          `${getUserName(user)} ${user.email ?? ''}`,
        );

        return (
          !normalizedQuery
          || haystack.includes(normalizedQuery)
        );
      })
      .slice(0, 8);
  }, [mentionSearch, mentionUsers]);

  useEffect(() => {
    setHighlightedMentionIndex(0);
  }, [mentionSearch?.query]);

  useEffect(() => {
    if (pendingCaretPosition === null) {
      return;
    }

    const frameId = window.requestAnimationFrame(() => {
      const textarea = textareaRef.current;

      if (!textarea) {
        return;
      }

      textarea.focus();
      textarea.setSelectionRange(
        pendingCaretPosition,
        pendingCaretPosition,
      );

      setPendingCaretPosition(null);
    });

    return () => {
      window.cancelAnimationFrame(frameId);
    };
  }, [body, pendingCaretPosition]);

  function updateMentionSearch(value, cursorPosition) {
    setMentionSearch(
      getMentionSearch(value, cursorPosition),
    );
  }

  function synchronizeSelectedMentions(nextBody) {
    const remainingMentionedUsers = mentionedUsers.filter(
      (user) => bodyContainsMention(nextBody, user),
    );

    if (
      remainingMentionedUsers.length
      !== mentionedUsers.length
    ) {
      onMentionedUsersChange(
        remainingMentionedUsers,
      );
    }
  }

  function handleBodyChange(event) {
    const nextBody = event.target.value;
    const cursorPosition = event.target.selectionStart;

    onBodyChange(nextBody);
    synchronizeSelectedMentions(nextBody);
    updateMentionSearch(nextBody, cursorPosition);
  }

  function handleTextareaClick(event) {
    updateMentionSearch(
      body,
      event.currentTarget.selectionStart,
    );
  }

  function handleTextareaSelect(event) {
    updateMentionSearch(
      body,
      event.currentTarget.selectionStart,
    );
  }

  function selectMention(user) {
    if (!mentionSearch || !user) {
      return;
    }

    const textarea = textareaRef.current;
    const cursorPosition =
      textarea?.selectionStart
      ?? body.length;

    const mentionText = `@${getUserName(user)}`;
    const beforeMention = body.slice(
      0,
      mentionSearch.atIndex,
    );
    const afterCursor = body.slice(cursorPosition);
    const separator =
      afterCursor.startsWith(' ')
        ? ''
        : ' ';

    const nextBody =
      `${beforeMention}${mentionText}${separator}${afterCursor}`;

    const nextCaretPosition =
      beforeMention.length
      + mentionText.length
      + separator.length;

    const alreadySelected = mentionedUsers.some(
      (selectedUser) => selectedUser.id === user.id,
    );

    if (!alreadySelected) {
      onMentionedUsersChange([
        ...mentionedUsers,
        user,
      ]);
    }

    onBodyChange(nextBody);
    setMentionSearch(null);
    setPendingCaretPosition(nextCaretPosition);
  }

  function handleFileChange(event) {
    const incomingFiles = Array.from(
      event.target.files ?? [],
    );

    if (incomingFiles.length > 0) {
      onFilesChange(incomingFiles);
    }

    event.target.value = '';
  }

  function handleDragEnter(event) {
    event.preventDefault();
    event.stopPropagation();

    if (busy || !hasDraggedFiles(event)) {
      return;
    }

    setDragActive(true);
  }

  function handleDragOver(event) {
    if (!hasDraggedFiles(event)) {
      return;
    }

    event.preventDefault();
    event.stopPropagation();

    if (!busy) {
      setDragActive(true);
    }
  }

  function handleDragLeave(event) {
    event.preventDefault();
    event.stopPropagation();

    if (
      event.currentTarget.contains(
        event.relatedTarget,
      )
    ) {
      return;
    }

    setDragActive(false);
  }

  function handleDrop(event) {
    event.preventDefault();
    event.stopPropagation();

    setDragActive(false);

    if (
      busy
      || !hasDraggedFiles(event)
    ) {
      return;
    }

    const incomingFiles = Array.from(
      event.dataTransfer.files ?? [],
    );

    if (incomingFiles.length > 0) {
      onFilesChange(incomingFiles);
    }
  }

  function handleKeyDown(event) {
    if (
      mentionSearch
      && filteredMentionUsers.length > 0
    ) {
      if (event.key === 'ArrowDown') {
        event.preventDefault();

        setHighlightedMentionIndex(
          (currentIndex) =>
            (currentIndex + 1)
            % filteredMentionUsers.length,
        );

        return;
      }

      if (event.key === 'ArrowUp') {
        event.preventDefault();

        setHighlightedMentionIndex(
          (currentIndex) =>
            (
              currentIndex
              - 1
              + filteredMentionUsers.length
            ) % filteredMentionUsers.length,
        );

        return;
      }

      if (
        event.key === 'Enter'
        && !event.shiftKey
        && !event.nativeEvent.isComposing
      ) {
        event.preventDefault();
        event.stopPropagation();

        selectMention(
          filteredMentionUsers[
            highlightedMentionIndex
          ],
        );

        return;
      }
    }

    if (event.key === 'Escape' && mentionSearch) {
      event.preventDefault();
      setMentionSearch(null);
      return;
    }

    if (
      event.key !== 'Enter'
      || event.shiftKey
      || event.nativeEvent.isComposing
    ) {
      return;
    }

    event.preventDefault();
    event.stopPropagation();

    if (canSubmit) {
      onSubmit();
    }
  }

  function handlePublishClick(event) {
    event.preventDefault();
    event.stopPropagation();

    if (canSubmit) {
      onSubmit();
    }
  }

  return (
    <div
      className={
        dragActive
          ? 'activity-composer activity-composer-drag'
          : 'activity-composer'
      }
      onClick={(event) => event.stopPropagation()}
      onDragEnter={handleDragEnter}
      onDragLeave={handleDragLeave}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
    >
      {dragActive && (
        <div className="activity-drop-overlay">
          <Paperclip
            aria-hidden="true"
            size={34}
          />

          <strong>
            Suelta los archivos aquí
          </strong>

          <span>
            Puedes agregar uno o varios archivos.
          </span>
        </div>
      )}

      <div className="activity-composer-input-wrap">
        <textarea
          aria-label="Comentario interno"
          className="activity-composer-textarea"
          disabled={busy}
          onChange={handleBodyChange}
          onClick={handleTextareaClick}
          onKeyDown={handleKeyDown}
          onSelect={handleTextareaSelect}
          placeholder="Escribe un comentario interno... Usa @ para mencionar"
          ref={textareaRef}
          rows={3}
          value={body}
        />

        {mentionSearch ? (
          <div
            aria-label="Usuarios disponibles para mencionar"
            className="activity-mention-menu"
            role="listbox"
          >
            <div className="activity-mention-menu-header">
              <AtSign
                aria-hidden="true"
                size={15}
              />

              <span>
                {mentionSearch.query.trim()
                  ? 'Usuarios encontrados'
                  : 'Mencionar a un usuario'}
              </span>
            </div>

            {filteredMentionUsers.length > 0 ? (
              <div className="activity-mention-options">
                {filteredMentionUsers.map((user, index) => {
                  const userName = getUserName(user);

                  return (
                    <button
                      aria-selected={
                        index === highlightedMentionIndex
                      }
                      className={
                        index === highlightedMentionIndex
                          ? 'activity-mention-option is-active'
                          : 'activity-mention-option'
                      }
                      key={user.id}
                      onMouseDown={(event) => {
                        event.preventDefault();
                        selectMention(user);
                      }}
                      onMouseEnter={() =>
                        setHighlightedMentionIndex(index)
                      }
                      role="option"
                      type="button"
                    >
                      <span className="activity-mention-avatar">
                        {userName
                          .split(/\s+/)
                          .slice(0, 2)
                          .map((part) => part[0])
                          .join('')
                          .toUpperCase()}
                      </span>

                      <span className="activity-mention-user">
                        <strong>{userName}</strong>

                        {user.email ? (
                          <small>{user.email}</small>
                        ) : null}
                      </span>
                    </button>
                  );
                })}
              </div>
            ) : (
              <div className="activity-mention-empty">
                No se encontraron usuarios activos.
              </div>
            )}
          </div>
        ) : null}
      </div>

      {mentionedUsers.length > 0 ? (
        <div className="activity-selected-mentions">
          {mentionedUsers.map((user) => (
            <span key={user.id}>
              <AtSign
                aria-hidden="true"
                size={12}
              />

              {getUserName(user)}
            </span>
          ))}
        </div>
      ) : null}

      {selectedFiles.length > 0 && (
        <div className="activity-composer-files">
          {selectedFiles.map((file, index) => (
            <div
              className="activity-composer-file"
              key={`${file.name}-${file.size}-${file.lastModified}-${index}`}
            >
              <Paperclip
                aria-hidden="true"
                size={15}
              />

              <span className="activity-composer-file-info">
                <strong>{file.name}</strong>

                <small>
                  {formatBytes(file.size)}
                </small>
              </span>

              <button
                aria-label={`Quitar ${file.name}`}
                disabled={busy}
                onClick={() => onRemoveFile(index)}
                type="button"
              >
                <X
                  aria-hidden="true"
                  size={15}
                />
              </button>
            </div>
          ))}
        </div>
      )}

      <div className="activity-composer-actions">
        <input
          hidden
          multiple
          onChange={handleFileChange}
          ref={fileInputRef}
          type="file"
        />

        <button
          className="activity-attach-button"
          disabled={busy}
          onClick={() => fileInputRef.current?.click()}
          type="button"
        >
          {selectedFiles.length > 0 ? (
            <FilePlus2
              aria-hidden="true"
              size={16}
            />
          ) : (
            <Paperclip
              aria-hidden="true"
              size={16}
            />
          )}

          {selectedFiles.length > 0
            ? 'Agregar otro'
            : 'Adjuntar'}
        </button>

        <span className="activity-composer-hint">
          @ para mencionar · Enter para publicar · Shift + Enter para nueva línea
        </span>

        <button
          className="activity-publish-button"
          disabled={!canSubmit}
          onClick={handlePublishClick}
          type="button"
        >
          <Send
            aria-hidden="true"
            size={16}
          />

          {busy
            ? 'Publicando...'
            : 'Publicar'}
        </button>
      </div>
    </div>
  );
}