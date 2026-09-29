import React from 'react';
import { createPortal } from 'react-dom';

// Modal compartido de las vistas MYC Mobile del ETS. Se monta en un portal para
// no quedar dentro del formulario del Resumen ETS (Enter no debe enviarlo).
export default function EtsMobileModal({ children, onClose, title, subtitle, eyebrow = 'MYC Mobile' }) {
  return createPortal(
    <div className="modal-backdrop" role="presentation">
      <section aria-modal="true" className="client-modal quotation-detail-modal ets-mobile-execution-modal" role="dialog">
        <div className="quotation-detail-header">
          <div>
            <p>{eyebrow}</p>
            <h2>{title}</h2>
            {subtitle ? <span>{subtitle}</span> : null}
          </div>
          <button className="icon-text-button" onClick={onClose} type="button">Cerrar</button>
        </div>
        {children}
      </section>
    </div>,
    document.body
  );
}

export function openPdfBlob(blob) {
  const url = URL.createObjectURL(blob);
  window.open(url, '_blank', 'noopener');
  window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
}
