export const emptyClientForm = {
  commercialName: '',
  rfc: '',
  contactName: '',
  phone: '',
  email: '',
  status: 'Activo',
  street: '',
  exteriorNumber: '',
  interiorNumber: '',
  neighborhood: '',
  city: '',
  addressState: '',
  postalCode: '',
  country: 'Mexico',
  fiscalLegalName: '',
  fiscalRfc: '',
  fiscalPostalCode: '',
  taxRegime: '',
  cfdiUse: ''
};

export const emptyQuotationForm = {
  clientId: '',
  validUntil: '',
  notes: ''
};

export const emptyQuotationItemForm = {
  catalogItemId: '',
  description: '',
  quantity: '1',
  unit: 'Servicio',
  unitPrice: '',
  currency: 'MXN',
  discount: '0',
  observations: '',
  satKey: '',
  satUnit: '',
  internalUnit: '',
  commodity: null,
  calibrationScope: null,
  quotationLegend: '',
  taxObject: 'iva_16',
  taxRate: '16'
};

export const emptyProductForm = {
  category: '',
  internalKey: '',
  name: '',
  description: '',
  type: 'Servicio',
  commodity: 'calibration',
  calibrationScope: 'traceable',
  quotationLegend: '',
  satKey: '',
  satUnit: '',
  internalUnit: 'service',
  customInternalUnit: '',
  basePrice: '',
  sourceCurrency: 'MXN',
  exchangeRate: '1',
  internalCost: '',
  costCurrency: 'MXN',
  margin: '',
  taxObject: 'iva_16',
  status: 'Activo'
};

export const emptyServiceOrderForm = {
  agendaDate: '',
  serviceDate: '',
  technicianId: '',
  requiresPayment: true,
  notes: ''
};

export const emptyEquipmentForm = {
  serviceOrderItemId: '',
  certificateScope: 'traceable',
  name: '',
  brand: '',
  model: '',
  serialNumber: '',
  internalId: '',
  rangeOrCapacity: '',
  initialCondition: '',
  notes: ''
};

export const emptyFieldSheetForm = {
  templateKey: 'general',
  calibrationProcedureId: '',
  calibrationPlace: '',
  minimumDivision: '',
  location: '',
  attention: '',
  company: '',
  address: '',
  receptionDate: '',
  calibrationDate: '',
  nextCalibrationDate: '',
  environmentHumidityStart: '',
  environmentHumidityEnd: '',
  environmentTemperatureStart: '',
  environmentTemperatureEnd: '',
  equipmentGeneralCondition: '',
  considerEquipmentDeviations: false,
  units: '',
  calibratedBy: '',
  reviewedBy: '',
  reportMadeBy: '',
  purchaseOrderOrQuotation: '',
  initialCondition: '',
  finalCondition: '',
  resultsSummary: '',
  patternUsed: '',
  observations: '',
  evidenceNotes: '',
  method: '',
  environmentalConditions: '',
  technicianNotes: '',
  reservedCertificateFolio: '',
  certificateClientMode: 'billing',
  certificateClientCompany: '',
  certificateClientAttention: '',
  certificateClientAddress: '',
  applyCertificateClientToOrder: false,
  resultsRows: [],
  referenceStandards: [],
  newReferenceStandardId: '',
  newReferenceStandardUsageRole: 'primary',
  newReferenceStandardMeasurementSection: '',
  newReferenceStandardNotes: '',
};

export const emptyCertificateForm = {
  certificateType: 'trazable',
  notes: ''
};

export const emptyReferenceStandardForm = {
  internalCode: '',
  name: '',
  description: '',
  ownerCompany: 'MYC',
  magnitude: '',
  brand: '',
  model: '',
  serialNumber: '',
  identification: '',
  unit: '',
  rangeMin: '',
  rangeMax: '',
  resolution: '',
  coverageFactorK: '2',
  provider: '',
  calibrationLaboratory: '',
  certificateNumber: '',
  certificateFilePath: '',
  calibratedOn: '',
  nextCalibrationOn: '',
  status: 'active',
  notes: ''
};

export const emptyReferenceStandardUncertaintyForm = {
  rangeMin: '',
  rangeMax: '',
  unit: '',
  uncertaintyValue: '',
  coverageFactorK: '2',
  distribution: '',
  notes: ''
};

export const emptyCalibrationProcedureForm = {
  code: '',
  name: '',
  description: '',
  magnitude: '',
  profileKey: '',
  uncertaintyModelId: '',
  uncertaintyModelVersionId: '',
  version: '1.0',
  issuerCompany: 'MYC',
  certificateType: 'trazable',
  requiredReadings: '',
  decisionRule: '',
  acceptanceCriteria: '',
  notes: '',
  status: 'draft'
};
