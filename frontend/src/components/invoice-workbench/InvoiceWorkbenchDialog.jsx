import { X } from 'lucide-react';
import { createPortal } from 'react-dom';
import { useEffect, useRef, useState } from 'react';

import {
  createGenieSpringKeyframes,
  SIGNATURE_CLOSE_DURATION,
  SIGNATURE_ICON_FADE_DURATION,
} from '../signatures/signatureMorphAnimation.js';
import InvoiceDraftView from './InvoiceDraftView.jsx';

import './invoice-workbench.css';

export default function InvoiceWorkbenchDialog({
  open,
  quotation,
  invoice = null,
  client,
  draft,
  catalogByCode,
  isSaving = false,
  canIssue = false,
  originElement = null,
  onConceptChange,
  onDraftChange,
  onSaveDraft,
  onIssue,
  onClose,
}) {
  const [isClosing, setIsClosing] = useState(false);

  const closeTimerRef = useRef(null);
  const closeAnimationRef = useRef(null);
  const closeMetricsRef = useRef(null);
  const modalRef = useRef(null);

  useEffect(() => {
    if (!open || isClosing) return undefined;

    modalRef.current?.focus();

    function handleKeyDown(event) {
      if (event.key === 'Escape') {
        event.preventDefault();
        beginClose();
      }
    }

    window.addEventListener('keydown', handleKeyDown);

    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isClosing, open]);

  useEffect(() => {
    if (!isClosing || !modalRef.current) return undefined;

    const animation = modalRef.current.animate(
      createGenieSpringKeyframes(closeMetricsRef.current),
      {
        duration: SIGNATURE_CLOSE_DURATION,
        easing: 'linear',
        fill: 'forwards',
      }
    );

    closeAnimationRef.current = animation;
    animation.finished.catch(() => {});

    return () => {
      animation.cancel();

      if (closeAnimationRef.current === animation) {
        closeAnimationRef.current = null;
      }
    };
  }, [isClosing]);

  useEffect(
    () => () => {
      window.clearTimeout(closeTimerRef.current);
      closeAnimationRef.current?.cancel();
    },
    []
  );

  useEffect(() => {
    if (open) {
      setIsClosing(false);
    }
  }, [open]);

  if (!open || !quotation) {
    return null;
  }

  function beginClose() {
    if (isClosing || isSaving) return;

    const modalRect = modalRef.current?.getBoundingClientRect();
    const originRect = originElement?.getBoundingClientRect?.();

    closeMetricsRef.current = {
      closeX:
        originRect && modalRect
          ? originRect.left +
            originRect.width / 2 -
            (modalRect.left + modalRect.width / 2)
          : 0,
      closeY:
        originRect && modalRect
          ? originRect.top +
            originRect.height / 2 -
            (modalRect.top + modalRect.height / 2)
          : 14,
      finalScaleX: 1,
      finalScaleY: 1,
    };

    setIsClosing(true);

    closeTimerRef.current = window.setTimeout(() => {
      setIsClosing(false);
      onClose?.();
      window.setTimeout(() => originElement?.focus?.(), 0);
    }, SIGNATURE_CLOSE_DURATION + SIGNATURE_ICON_FADE_DURATION);
  }

  const title = quotation.folio || 'Cotización sin folio';
  const headerLabel = invoice
    ? 'Borrador de facturación'
    : 'Precomprobante CFDI';

  return createPortal(
    <div
      className={
        isClosing
          ? 'invoice-draft-modal-layer is-closing'
          : 'invoice-draft-modal-layer'
      }
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) {
          beginClose();
        }
      }}
    >
      <section
        aria-labelledby="invoice-draft-modal-title"
        aria-modal="true"
        className={
          isClosing
            ? 'invoice-draft-modal closing'
            : 'invoice-draft-modal'
        }
        ref={modalRef}
        role="dialog"
        tabIndex={-1}
      >
        <header className="invoice-draft-modal__header">
          <div>
            <p>{headerLabel}</p>
            <h2 id="invoice-draft-modal-title">{title}</h2>
          </div>

          <button
            aria-label="Cerrar precomprobante"
            className="invoice-draft-modal__close"
            disabled={isClosing || isSaving}
            onClick={beginClose}
            type="button"
          >
            <X size={20} />
          </button>
        </header>

        <div className="invoice-draft-modal__content">
          <InvoiceDraftView
            canIssue={canIssue}
            catalogByCode={catalogByCode}
            client={client}
            draft={draft}
            invoice={invoice}
            isSaving={isSaving}
            onConceptChange={onConceptChange}
            onDraftChange={onDraftChange}
            onIssue={onIssue}
            onSaveDraft={onSaveDraft}
            quotation={quotation}
          />
        </div>
      </section>
    </div>,
    document.body
  );
}