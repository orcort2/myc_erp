import React, { useState } from 'react';

import { requestServiceOrderMobileCorrection } from '../../services/api.js';
import EtsMobileModal from './EtsMobileModal.jsx';

// "Enviar a corrección en MYC Mobile": el ERP NO edita la hoja. El dominio
// LAB conserva la revisión N (y su PDF final) y abre N+1 editable en Mobile.
// Único diálogo de la acción: lo usan la vista de ejecución y el detalle.
export default function EtsMobileCorrectionDialog({ serviceOrderId, target, onDone, onCancel }) {
  const [reason, setReason] = useState('');
  const [signaturePolicy, setSignaturePolicy] = useState('preserve');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const closedWorkOrder = target.mode === 'work_order_reopen';

  async function submit() {
    if (!reason.trim()) {
      setError('El motivo es obligatorio.');
      return;
    }
    setBusy(true);
    setError('');
    try {
      const projection = await requestServiceOrderMobileCorrection(serviceOrderId, target.equipment.id, {
        reason: reason.trim(),
        signature_policy: signaturePolicy,
      });
      onDone(projection);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <EtsMobileModal
      eyebrow="Acción administrativa"
      onClose={onCancel}
      subtitle={`OT ${target.workOrderFolio} · ${target.equipment.instrument} · ${target.equipment.certificate_folio || 'Sin folio'}`}
      title="Enviar a corrección en MYC Mobile"
    >
      <p className="muted">
        La revisión actual y su PDF final se conservan como históricos. MYC Mobile recibirá una nueva revisión editable;
        la corrección técnica se realiza exclusivamente en MYC Mobile.
        {closedWorkOrder ? ' La OT está cerrada: se reabrirá conforme a la política de firmas elegida.' : ''}
      </p>
      <label className="quotation-client-search">
        <span>Motivo (obligatorio)</span>
        <textarea autoFocus onChange={(event) => setReason(event.target.value)} rows={3} value={reason} />
      </label>
      {closedWorkOrder ? (
        <label className="quotation-client-search">
          <span>Firmas de la OT</span>
          <select onChange={(event) => setSignaturePolicy(event.target.value)} value={signaturePolicy}>
            <option value="preserve">Conservar firmas</option>
            <option value="invalidate">Invalidar firmas (requiere nueva firma)</option>
          </select>
        </label>
      ) : null}
      {error ? <div className="form-error" role="alert">{error}</div> : null}
      <div className="toolbar-actions">
        <button className="table-button" onClick={onCancel} type="button">Cancelar</button>
        <button className="table-button table-button--primary" disabled={busy || !reason.trim()} onClick={submit} type="button">
          Enviar a corrección
        </button>
      </div>
    </EtsMobileModal>
  );
}
