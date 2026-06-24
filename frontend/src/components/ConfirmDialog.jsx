import React, { useEffect } from 'react';

function ConfirmDialog({
  cancelText = 'Cancelar',
  confirmText = 'Confirmar',
  isLoading = false,
  isOpen = false,
  message,
  onClose,
  onConfirm,
  title,
  variant = 'normal'
}) {
  useEffect(() => {
    if (!isOpen) {
      return undefined;
    }

    function handleKeyDown(event) {
      if (event.key === 'Escape' && !isLoading) {
        onClose?.();
      }
    }

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isLoading, isOpen, onClose]);

  if (!isOpen) {
    return null;
  }

  return (
    <div
      className="modal-backdrop"
      onClick={() => {
        if (!isLoading) {
          onClose?.();
        }
      }}
      role="presentation"
    >
      <section
        aria-modal="true"
        className={`client-modal confirm-dialog ${variant === 'danger' ? 'confirm-dialog--danger' : ''}`}
        onClick={(event) => event.stopPropagation()}
        role="dialog"
      >
        <div className="section-heading confirm-dialog__header">
          <div>
            <p>{variant === 'danger' ? 'Confirmacion requerida' : 'Confirmar accion'}</p>
            <h2>{title}</h2>
          </div>
        </div>

        <div className="confirm-dialog__body">
          <p>{message}</p>
        </div>

        <div className="confirm-dialog__actions">
  <button
    className="confirm-dialog__cancel"
    disabled={isLoading}
    onClick={onClose}
    type="button"
  >
    {cancelText}
  </button>

  <button
    className={
      variant === 'danger'
        ? 'confirm-dialog__confirm confirm-dialog__confirm--danger'
        : 'confirm-dialog__confirm'
    }
    disabled={isLoading}
    onClick={onConfirm}
    type="button"
  >
    {isLoading ? 'Procesando...' : confirmText}
  </button>
</div>
      </section>
    </div>
  );
}

export default ConfirmDialog;
