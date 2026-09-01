export type LabLabelPayload = {
  calibrationKind: 'CALIBRADO' | 'VERIFICADO';
  calibrationDate: string;
  nextCalibrationDate?: string | null;
  code: string;
  workOrderFolio: string;
  certificateFolio?: string | null;
};

export interface LabelPrintService {
  readonly available: boolean;
  print50x30(payload: LabLabelPayload): Promise<void>;
}

class DisabledLabelPrintService implements LabelPrintService {
  readonly available = false;

  async print50x30(_payload: LabLabelPayload): Promise<void> {
    throw new Error('La impresión BLE NIIMBOT está reservada para una fase posterior.');
  }
}

// Punto único de sustitución futura por el adaptador BLE de NIIMBOT B1.
// El diseño y los datos siguen bajo autoridad de MYC; no dependen de tokens de plantillas externas.
export const labelPrintService: LabelPrintService = new DisabledLabelPrintService();
