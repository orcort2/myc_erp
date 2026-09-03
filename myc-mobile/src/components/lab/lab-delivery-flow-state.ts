import {
  emptySignatureCapture,
  hasSignificantSignatureCapture,
  isValidSignerName,
  type SignatureCapture,
} from '@/src/components/signatures/signature-flow-state';
import type { LabDeliveryCreatePayload, LabDeliveryMethod } from '@/src/types/lab-work-order';

/**
 * Estado y política PURA del wizard de Delivery (LabDeliveryFlow) --
 * separado del componente para poder probar la política de pasos/
 * validación sin renderizar React Native. Mismo espíritu que
 * signature-flow-state.ts, pero con entidades propias (quien entrega/quien
 * recibe, no cliente/técnico) -- por eso no se reutiliza SignatureFlowState
 * ni sus validadores con forma cliente/técnico, sólo las piezas realmente
 * agnósticas (SignatureCapture, hasSignificantSignatureCapture,
 * isValidSignerName, emptySignatureCapture, SignatureSubmissionLock desde
 * el propio signature-flow-state.ts).
 */
export type DeliveryStep = 'review' | 'recipient' | 'delivered_by_signature' | 'recipient_signature' | 'success';

export type DeliveryWizardState = {
  step: DeliveryStep;
  deliveryMethod: LabDeliveryMethod;
  recipientName: string;
  notes: string;
  deliveredByCapture: SignatureCapture;
  recipientCapture: SignatureCapture;
};

export function createDeliveryWizardState(defaultRecipientName: string): DeliveryWizardState {
  return {
    step: 'review',
    deliveryMethod: 'direct',
    recipientName: defaultRecipientName,
    notes: '',
    deliveredByCapture: emptySignatureCapture(),
    recipientCapture: emptySignatureCapture(),
  };
}

export function goToStep(state: DeliveryWizardState, step: DeliveryStep): DeliveryWizardState {
  return { ...state, step };
}

/** review -> recipient nunca requiere validación (método ya trae un default). */
export function validateContinueFromReview(_state: DeliveryWizardState): string | null {
  return null;
}

export function validateContinueFromRecipient(state: DeliveryWizardState): string | null {
  if (!isValidSignerName(state.recipientName)) return 'Escribe el nombre de quien recibe.';
  return null;
}

export function validateContinueFromDeliveredBySignature(state: DeliveryWizardState): string | null {
  if (!hasSignificantSignatureCapture(state.deliveredByCapture)) return 'Captura la firma de quien entrega.';
  return null;
}

/** Sólo se puede confirmar desde el último paso, con la firma del receptor capturada. */
export function validateSubmitDelivery(state: DeliveryWizardState): string | null {
  if (state.step !== 'recipient_signature') return 'Completa los pasos anteriores antes de confirmar.';
  if (!hasSignificantSignatureCapture(state.recipientCapture)) return 'Captura la firma de quien recibe.';
  return null;
}

export function buildDeliveryPayload(state: DeliveryWizardState): LabDeliveryCreatePayload {
  return {
    delivery_method: state.deliveryMethod,
    delivered_by_signature_data_url: state.deliveredByCapture.dataUrl,
    recipient_name: state.recipientName.trim(),
    recipient_signature_data_url: state.recipientCapture.dataUrl,
    notes: state.notes.trim() || null,
  };
}
