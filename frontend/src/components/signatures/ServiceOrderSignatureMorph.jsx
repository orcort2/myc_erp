import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import SignatureMorphButton from './SignatureMorphButton';
import SignatureSaveAnimation from './SignatureSaveAnimation';
import SignaturePad from './SignaturePad';
import {
  createGenieSpringKeyframes,
  SIGNATURE_CLOSE_DURATION,
  SIGNATURE_ICON_FADE_DURATION,
} from './signatureMorphAnimation';
import './signature.css';

const SAVE_ANIMATION_DURATION = 850;

export default function ServiceOrderSignatureMorph({
  serviceOrder,
  signatureForm,
  updateSignatureForm,
  saveSignatures,
  isSaving: isSavingExternal = false,
  onLifecycleChange,
}) {
  const [open, setOpen] = useState(false);
  const [step, setStep] = useState('client');
  const [savingStep, setSavingStep] = useState(null);
  const [isClosing, setIsClosing] = useState(false);
  const [isResettingClose, setIsResettingClose] = useState(false);
  const shellRef = useRef(null);
  const modalRef = useRef(null);
  const closeMetricsRef = useRef(null);
  const closeAnimationRef = useRef(null);
  const stepTimerRef = useRef(null);
  const closeTimerRef = useRef(null);
  const resetTransitionFrameRef = useRef(null);

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

  useEffect(() => {
    return () => {
      window.clearTimeout(stepTimerRef.current);
      window.clearTimeout(closeTimerRef.current);
      window.cancelAnimationFrame(resetTransitionFrameRef.current);
      closeAnimationRef.current?.cancel();
    };
  }, []);

  useLayoutEffect(() => {
    if (!isClosing || !modalRef.current || !closeMetricsRef.current) {
      return undefined;
    }

    const modal = modalRef.current;
    const animation = modal.animate(
      createGenieSpringKeyframes(closeMetricsRef.current),
      {
        duration: SIGNATURE_CLOSE_DURATION,
        easing: 'linear',
        fill: 'forwards',
      },
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

  function handleOpen() {
    window.clearTimeout(closeTimerRef.current);
    closeAnimationRef.current?.cancel();
    onLifecycleChange?.(true);
    setIsResettingClose(false);
    setIsClosing(false);
    setOpen(true);
  }

  function resetState() {
    window.clearTimeout(closeTimerRef.current);
    setIsResettingClose(true);
    setOpen(false);
    setStep('client');
    setSavingStep(null);
    setIsClosing(false);
    onLifecycleChange?.(false);

    resetTransitionFrameRef.current = window.requestAnimationFrame(() => {
      resetTransitionFrameRef.current = window.requestAnimationFrame(() => {
        setIsResettingClose(false);
      });
    });
  }

  function setCloseDestination() {
    const shell = shellRef.current;
    const modal = shell?.querySelector('.signature-morph-modal');

    closeMetricsRef.current = null;
    if (!shell || !modal) return;

    const modalRect = modal.getBoundingClientRect();

    shell.classList.add('is-measuring-close-target');
    shell.getBoundingClientRect();
    shell.classList.remove('is-open');

    const targetRect = shell.getBoundingClientRect();

    shell.classList.add('is-open', 'is-closing');
    const closingShellRect = shell.getBoundingClientRect();
    shell.classList.remove('is-closing');
    shell.getBoundingClientRect();
    shell.classList.remove('is-measuring-close-target');

    const closeX =
      targetRect.left + targetRect.width / 2 -
      (closingShellRect.left + closingShellRect.width / 2);
    const closeY =
      targetRect.top + targetRect.height / 2 -
      (closingShellRect.top + closingShellRect.height / 2);
    const finalScaleX = targetRect.width / modalRect.width;
    const finalScaleY = targetRect.height / modalRect.height;

    closeMetricsRef.current = {
      closeX,
      closeY,
      finalScaleX,
      finalScaleY,
    };

    shell.style.setProperty('--signature-close-duration', `${SIGNATURE_CLOSE_DURATION}ms`);
    shell.style.setProperty(
      '--signature-icon-fade-duration',
      `${SIGNATURE_ICON_FADE_DURATION}ms`,
    );
    shell.style.setProperty('--signature-close-width', `${modalRect.width}px`);
    shell.style.setProperty('--signature-close-height', `${modalRect.height}px`);
    shell.style.setProperty('--signature-close-x', `${closeX}px`);
    shell.style.setProperty('--signature-close-y', `${closeY}px`);
    shell.style.setProperty('--signature-close-scale-x', finalScaleX);
    shell.style.setProperty('--signature-close-scale-y', finalScaleY);
  }

  function beginClose() {
    if (isClosing) return;

    setCloseDestination();
    setIsClosing(true);
    closeTimerRef.current = window.setTimeout(
      resetState,
      SIGNATURE_CLOSE_DURATION + SIGNATURE_ICON_FADE_DURATION,
    );
  }

  function closeModal() {
    if (isSaving) return;

    beginClose();
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

    stepTimerRef.current = window.setTimeout(() => {
      setSavingStep(null);
      setStep('technician');
    }, SAVE_ANIMATION_DURATION);
  }

  async function handleSaveTechnician() {
    setSavingStep('technician');
    onLifecycleChange?.(true);

    try {
      await saveSignatures();

      stepTimerRef.current = window.setTimeout(
        beginClose,
        SAVE_ANIMATION_DURATION,
      );
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
      } ${isResettingClose ? 'is-resetting-close' : ''}`}
      ref={shellRef}
    >
      
        <div
          className={`signature-final-button ${
            isClosing ? 'is-entering' : ''
          } ${open && !isClosing ? 'is-hidden' : ''}`}
          aria-hidden={open && !isClosing}
        >
          <SignatureMorphButton
            disabled={isSaving || isClosing}
            onOpen={handleOpen}
          />
        </div>

      {open && (
        <div
          className={`signature-morph-modal ${isClosing ? 'closing' : ''}`}
          ref={modalRef}
        >
          <div className={`signature-modal-content ${isClosing ? 'closing' : ''}`}>
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
          </div>
        </div>
      )}
    </div>
  );
}
