import { useState } from 'react';
import SignatureMorphButton from '../components/signatures/SignatureMorphButton';
import SignatureSaveAnimation from '../components/signatures/SignatureSaveAnimation';
import '../components/signatures/signature.css';

export default function SignatureLabPage() {
  const [open, setOpen] = useState(false);
  const [step, setStep] = useState('client');
  const [savingStep, setSavingStep] = useState(null);
  const [isClosing, setIsClosing] = useState(false);
  const [isReturning, setIsReturning] = useState(false);

  function handleOpen() {
    setIsReturning(false);
    setOpen(true);
  }

  function closeModal() {
    setIsClosing(true);

    window.setTimeout(() => {
      setOpen(false);
      setStep('client');
      setSavingStep(null);
      setIsClosing(false);
      setIsReturning(true);

      window.setTimeout(() => {
        setIsReturning(false);
      }, 220);
    }, 900);
  }

  function handleSaveClient() {
    setSavingStep('client');

    window.setTimeout(() => {
      setSavingStep(null);
      setStep('technician');
    }, 900);
  }

  function handleSaveTechnician() {
    setSavingStep('technician');

    window.setTimeout(() => {
      setSavingStep(null);
      closeModal();
    }, 900);
  }

  const isSaving = Boolean(savingStep);

  return (
    <div
      style={{
        minHeight: '100vh',
        background: '#0b1120',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
      }}
    >
      <div
        className={`signature-morph-shell ${open ? 'is-open' : ''} ${
          isClosing ? 'is-closing' : ''
        }`}
      >
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

                      <div className="signature-modal-canvas-placeholder">
                        {step === 'client'
                          ? 'Canvas firma cliente'
                          : 'Canvas firma técnico'}
                      </div>

                      <div className="signature-modal-actions">
                        <button type="button">Limpiar</button>

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
    </div>
  );
}