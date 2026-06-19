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
  initialCondition: '',
  finalCondition: '',
  patternUsed: '',
  results: '',
  observations: '',
  evidenceNotes: '',
  method: '',
  environmentalConditions: '',
  technicianNotes: ''
};

export const emptyCertificateForm = {
  certificateType: 'trazable',
  notes: ''
};