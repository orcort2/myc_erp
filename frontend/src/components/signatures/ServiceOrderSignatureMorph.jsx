import { useState } from 'react';
import SignatureMorphButton from './SignatureMorphButton';
import SignatureSaveAnimation from './SignatureSaveAnimation';
import { updateServiceOrder } from '../../services/api';
import './signature.css';

export default function ServiceOrderSignatureMorph({ serviceOrder, onSigned }) {
  const [open, setOpen] = useState(false);
  const [step, setStep] = useState('client');
  const [savingStep, setSavingStep] = useState(null);
  const [isClosing, setIsClosing] = useState(false);
  const [isReturning, setIsReturning] = useState(false);

  const [clientName, setClientName] = useState(
    serviceOrder?.client_received_signed_name ?? ''
  );
  const [technicianName, setTechnicianName] = useState(
    serviceOrder?.technician_signed_name ?? serviceOrder?.technician_name ?? ''
  );

  // Temporal: luego esto se reemplaza por el canvas real.
  const [clientSignatureDataUrl] = useState('data:image/svg+xml;base64,');
  const [technicianSignatureDataUrl] = useState('data:image/svg+xml;base64,');

  const isSaving = Boolean(savingStep);

  function handleOpen() {
    setIsReturning(false);
    setOpen(true);
  }

  function resetState() {
    setOpen(false);
    setStep('client');
    setSavingStep(null);
    setIsClosing(false);
    setIsReturning(true);

    window.setTimeout(() => {
      setIsReturning(false);
    }, 220);
  }

  function closeModal() {
    setIsClosing(true);
    window.setTimeout(resetState, 900);
  }

  function handleSaveClient() {
    setSavingStep('client');

    window.setTimeout(() => {
      setSavingStep(null);
      setStep('technician');
    }, 900);
  }

  async function handleSaveTechnician() {
    setSavingStep('technician');

    const payload = {
      client_received_signature_data_url: clientSignatureDataUrl,
      client_received_signed_name: clientName || 'Cliente',

      client_acceptance_signature_data_url: clientSignatureDataUrl,
      client_acceptance_signed_name: clientName || 'Cliente',

      technician_signature_data_url: technicianSignatureDataUrl,
      technician_signed_name: technicianName || serviceOrder?.technician_name || 'Técnico',
    };

    try {
      const updatedOrder = await updateServiceOrder(serviceOrder.id, payload);

      window.setTimeout(() => {
        setSavingStep(null);
        closeModal();
        onSigned?.(updatedOrder);
      }, 900);
    } catch (error) {
      setSavingStep(null);
      window.alert(error.message || 'No se pudieron guardar las firmas');
    }
  }

  return (
    <div className={`signature-morph-shell ${open ? 'is-open' : ''} ${isClosing ? 'is-closing' : ''}`}>
      {!open && (
        <div className={isReturning ? 'signature-button-returning' : ''}>
          <SignatureMorphButton onOpen={handleOpen} />
        </div>
      )}

      {open && (
        <div className={`signature-morph-modal ${isClosing ? 'closing' : ''}`}>
          <div className={`signature-modal-content ${isClosing ? 'closing' : ''}`}>
            {!isClosing && (
              <>
                <button
                  type="button"
                  className="signature-modal-close"
                  onClick={closeModal}
                  disabled={isSaving}
                >
                  ×
                </button>

                {isSaving ? (
                  <SignatureSaveAnimation
                    label={
                      savingStep === 'client'
                        ? 'Guardando firma del cliente...'
                        : 'Guardando firmas...'
                    }
                  />
                ) : (
                  <>
                    <div className="signature-modal-header">
                      <p>Orden de trabajo</p>
                      <h2>
                        {step === 'client'
                          ? 'Firma del cliente'
                          : 'Firma del técnico'}
                      </h2>
                      <span>
                        {step === 'client'
                          ? 'Esta firma se usará para recepción y aceptación.'
                          : 'Firma interna del técnico responsable.'}
                      </span>
                    </div>

                    <label className="form-field">
                      <span>Nombre del firmante</span>
                      <input
                        type="text"
                        value={step === 'client' ? clientName : technicianName}
                        onChange={(event) => {
                          if (step === 'client') {
                            setClientName(event.target.value);
                          } else {
                            setTechnicianName(event.target.value);
                          }
                        }}
                        placeholder={step === 'client' ? 'Nombre del cliente' : 'Nombre del técnico'}
                      />
                    </label>

                    <div className="signature-modal-canvas-placeholder">
                      {step === 'client'
                        ? 'Aquí irá el canvas real de firma cliente'
                        : 'Aquí irá el canvas real de firma técnico'}
                    </div>

                    <div className="signature-modal-actions">
                      <button type="button">
                        Limpiar
                      </button>

                      <button
                        type="button"
                        onClick={
                          step === 'client'
                            ? handleSaveClient
                            : handleSaveTechnician
                        }
                      >
                        {step === 'client'
                          ? 'Guardar firma cliente'
                          : 'Guardar firma técnico'}
                      </button>
                    </div>
                  </>
                )}
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}