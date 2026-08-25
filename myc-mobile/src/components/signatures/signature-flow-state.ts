export type NormalizedPoint = {
  x: number;
  y: number;
};

export type SignatureCapture = {
  dataUrl: string;
  hasDrawing: boolean;
  strokes: NormalizedPoint[][];
};

export type SignaturePayload = {
  client: {
    signer_name: string;
    signature_data_url: string;
  };
  technician: {
    signer_name: string;
    signature_data_url: string;
  };
};

export type SignatureFlowStep = 'client' | 'technician';

export type SignatureFlowState = {
  clientCapture: SignatureCapture;
  clientName: string;
  rootWorkOrderId: number;
  step: SignatureFlowStep;
  technicianCapture: SignatureCapture;
  technicianName: string;
};

export const SIGNATURE_MIN_STROKE_DISTANCE = 0.01;

export const emptySignatureCapture = (): SignatureCapture => ({
  dataUrl: '',
  hasDrawing: false,
  strokes: [],
});

export function signatureStrokeDistance(stroke: NormalizedPoint[]): number {
  let distance = 0;
  for (let index = 1; index < stroke.length; index += 1) {
    distance += Math.hypot(
      stroke[index].x - stroke[index - 1].x,
      stroke[index].y - stroke[index - 1].y,
    );
  }
  return distance;
}

export function isSignificantSignatureStroke(stroke: NormalizedPoint[]): boolean {
  return stroke.length >= 2 && signatureStrokeDistance(stroke) >= SIGNATURE_MIN_STROKE_DISTANCE;
}

export function hasSignificantSignatureCapture(capture: SignatureCapture): boolean {
  return capture.hasDrawing
    && capture.dataUrl.length > 0
    && capture.strokes.some(isSignificantSignatureStroke);
}

export function createSignatureFlowState({
  clientName,
  rootWorkOrderId,
  technicianName,
}: {
  clientName: string;
  rootWorkOrderId: number;
  technicianName: string;
}): SignatureFlowState {
  return {
    clientCapture: emptySignatureCapture(),
    clientName,
    rootWorkOrderId,
    step: 'client',
    technicianCapture: emptySignatureCapture(),
    technicianName,
  };
}

export function reconcileSignatureFlowState(
  current: SignatureFlowState | null,
  nextContext: {
    clientName: string;
    rootWorkOrderId: number;
    technicianName: string;
  },
): SignatureFlowState {
  if (current?.rootWorkOrderId === nextContext.rootWorkOrderId) return current;
  return createSignatureFlowState(nextContext);
}

export function isValidSignerName(value: string): boolean {
  return value.trim().length > 0;
}

export function canContinueSignature(name: string, capture: SignatureCapture): boolean {
  return isValidSignerName(name) && hasSignificantSignatureCapture(capture);
}

export function validateSignatureSubmission({
  capturedContextId,
  clientCapture,
  clientName,
  currentContextId,
  isSubmitting,
  technicianCapture,
  technicianName,
}: {
  capturedContextId: number | null;
  clientCapture: SignatureCapture;
  clientName: string;
  currentContextId: number | null;
  isSubmitting: boolean;
  technicianCapture: SignatureCapture;
  technicianName: string;
}): string | null {
  if (isSubmitting) return 'Las firmas ya se están guardando.';
  if (capturedContextId == null || capturedContextId !== currentContextId) {
    return 'El grupo activo cambió. Captura nuevamente las firmas.';
  }
  if (!isValidSignerName(clientName)) return 'Escribe el nombre del cliente.';
  if (!hasSignificantSignatureCapture(clientCapture)) return 'Captura la firma del cliente.';
  if (!isValidSignerName(technicianName)) return 'Escribe el nombre del técnico.';
  if (!hasSignificantSignatureCapture(technicianCapture)) return 'Captura la firma del técnico.';
  return null;
}

export function createSignaturePayload(
  clientName: string,
  clientCapture: SignatureCapture,
  technicianName: string,
  technicianCapture: SignatureCapture,
): SignaturePayload {
  return {
    client: {
      signer_name: clientName.trim(),
      signature_data_url: clientCapture.dataUrl,
    },
    technician: {
      signer_name: technicianName.trim(),
      signature_data_url: technicianCapture.dataUrl,
    },
  };
}

export class SignatureSubmissionLock {
  private submitting = false;

  get isSubmitting(): boolean {
    return this.submitting;
  }

  begin(): boolean {
    if (this.submitting) return false;
    this.submitting = true;
    return true;
  }

  finish(): void {
    this.submitting = false;
  }
}
