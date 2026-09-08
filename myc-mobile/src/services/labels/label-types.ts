/**
 * Contrato de datos de negocio de la etiqueta térmica LAB 50x30 -- ver
 * docs/architecture/lab-label-printing.md para el contrato completo.
 *
 * calibrationKind ('CALIBRADO'/'VERIFICADO') se eliminó deliberadamente: el
 * usuario confirmó que la etiqueta no necesita distinguirlo, y una auditoría
 * previa a este cambio no encontró ningún campo de dominio que lo respalde
 * (no existe en LabFieldSheet/LabEquipment ni en field-sheet-canonical-contract).
 */
export type LabLabelPayload = {
  /** LabFieldSheet.calibration_date (ISO YYYY-MM-DD). Requerido para
   * imprimir -- ver requireCalibrationDate en label-renderer.ts: es una
   * regla de PRESENTACIÓN introducida aquí (nada en el backend exige este
   * campo para completar una hoja), no una regla preexistente del dominio. */
  calibrationDate: string;
  /** LabFieldSheet.next_calibration_date. Puede ser null (no todo servicio
   * exige recalibración periódica) -- se imprime como "N/A", nunca bloquea. */
  nextCalibrationDate?: string | null;
  /** LabEquipment.identification -- el "ID interno"/"Identificación" que ya
   * usa el resto de la app como identificador legible del equipo (ver
   * field-sheet-canonical-contract.ts, internal_id). CODIGO en la etiqueta. */
  equipmentCode: string;
  /** String(LabWorkOrder.folio). O.T. en la etiqueta. */
  workOrderFolio: string;
  /** LabEquipment.certificate_folio. Puede ser null/pendiente (folio_status
   * === 'pending', p.ej. servicio "linked" a la espera de autorización) --
   * se imprime como "PENDIENTE", nunca bloquea la impresión. INFORME en la
   * etiqueta. */
  certificateFolio?: string | null;
};

/** Bitmap monocromático empaquetado: un bit por pixel, MSB primero, stride =
 * ceil(widthPx/8) bytes por fila. 1 = tinta/negro, 0 = blanco/sin tinta --
 * mismo convenio que usa el protocolo NIIMBOT (ver
 * printers/adapters/niimbot-b1/protocol.ts), pero este tipo no sabe nada de
 * NIIMBOT ni de ningún fabricante. */
export type MonochromeBitmap = {
  widthPx: number;
  heightPx: number;
  rows: Uint8Array[];
};

/** Salida canónica y determinista de LabelRenderer. El adaptador de
 * impresora (NIIMBOT, NELKO, o el que siga) NUNCA sabe qué significan
 * "FECHA DE CAL"/"PROX. CAL"/"CODIGO"/"O.T."/"INFORME": sólo recibe este
 * raster ya compuesto y lo transmite. */
export type RasterLabel = {
  widthPx: number;
  heightPx: number;
  bitmap: MonochromeBitmap;
  /** LabelProfile.id que produjo este raster -- trazabilidad para logs/tests,
   * nunca interpretado por el adaptador. */
  profileId: string;
};
