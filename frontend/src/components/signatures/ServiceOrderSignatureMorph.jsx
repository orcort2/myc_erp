import { useState } from 'react';
import SignatureMorphButton from './SignatureMorphButton';
import SignatureSaveAnimation from './SignatureSaveAnimation';
import SignaturePad from './SignaturePad';
import './signature.css';

export default function ServiceOrderSignatureMorph({
  serviceOrder,
  signatureForm,
  updateSignatureForm,
  saveSignatures,
  isSaving: isSavingExternal = false,
}) {
  const [open, setOpen] = useState(false);
  const [step, setStep] = useState('client');
  const [savingStep, setSavingStep] = useState(null);
  const [isClosing, setIsClosing] = useState(false);
  const [isReturning, setIsReturning] = useState(false);

  const clientName =
    signatureForm?.clientReceivedName ??
    serviceOrder?.client_received_signed_name ??
    '';

  const technicianName =
    signatureForm?.technicianName ??
    serviceOrder?.technician_signed_name ??
    serviceOrder?.technician_name ??
    '';

  const isSaving = isSavingExternal || Boolean(savingStep);

  function handleOpen() {
    setIsReturning(false);
    setIsClosing(false);
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
    if (isSaving) return;

    setIsClosing(true);
    window.setTimeout(resetState, 900);
  }

  function updateClientName(value) {
    updateSignatureForm('clientReceivedName', value);
    updateSignatureForm('clientAcceptanceName', value);
  }

  function updateClientSignature(value) {
    updateSignatureForm('clientReceivedSignature', value);
    updateSignatureForm('clientAcceptanceSignature', value);
  }

  function updateTechnicianName(value) {
    updateSignatureForm('technicianName', value);
  }

  function updateTechnicianSignature(value) {
    updateSignatureForm('technicianSignature', value);
  }

  function handleSaveClient() {
    setSavingStep('client');

    window.setTimeout(() => {
      setSavingStep(null);
      setStep('technician');
    }, 850);
  }

  async function handleSaveTechnician() {
    setSavingStep('technician');

    try {
      await saveSignatures();

      window.setTimeout(() => {
        setSavingStep(null);
        closeModal();
      }, 850);
    } catch (error) {
      setSavingStep(null);
      window.alert(error?.message || 'No se pudieron guardar las firmas');
    }
  }

  const currentSignaturePad =
    step === 'client'
      ? {
          label: 'Firma Cliente',
          name: clientName,
          dataUrl: signatureForm?.clientReceivedSignature ?? '',
          signedAt: serviceOrder?.client_received_signed_at,
          onNameChange: updateClientName,
          onSignatureChange: updateClientSignature,
        }
      : {
          label: 'Firma Técnico',
          name: technicianName,
          dataUrl: signatureForm?.technicianSignature ?? '',
          signedAt: serviceOrder?.technician_signed_at,
          onNameChange: updateTechnicianName,
          onSignatureChange: updateTechnicianSignature,
        };

  return (
    <div
      className={`signature-morph-shell ${open ? 'is-open' : ''} ${
        isClosing ? 'is-closing' : ''
      }`}
    >
      {!open && (
        <div className={isReturning ? 'signature-button-returning' : ''}>
          <SignatureMorphButton disabled={isSaving} onOpen={handleOpen} />
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
                  aria-label="Cerrar firmas"
                >
                  ×
                </button>

                {isSaving ? (
                  <SignatureSaveAnimation
                    label={
                      savingStep === 'client'
                        ? 'Preparando firma del técnico...'
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
                          ? 'Esta firma se usará para recepción y aceptación del servicio.'
                          : 'Firma interna del técnico responsable del ETS.'}
                      </span>
                    </div>

                    <div className="signature-modal-pad-area">
                      <SignaturePad
                        label={currentSignaturePad.label}
                        name={currentSignaturePad.name}
                        dataUrl={currentSignaturePad.dataUrl}
                        signedAt={currentSignaturePad.signedAt}
                        onNameChange={currentSignaturePad.onNameChange}
                        onSignatureChange={currentSignaturePad.onSignatureChange}
                      />
                    </div>

                    <div className="signature-modal-actions">
                      {step === 'technician' ? (
                        <button
                          type="button"
                          onClick={() => setStep('client')}
                          disabled={isSaving}
                        >
                          Volver a cliente
                        </button>
                      ) : null}

                      <button
                        type="button"
                        onClick={
                          step === 'client'
                            ? handleSaveClient
                            : handleSaveTechnician
                        }
                        disabled={isSaving}
                      >
                        {step === 'client'
                          ? 'Continuar a técnico'
                          : 'Guardar firmas'}
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