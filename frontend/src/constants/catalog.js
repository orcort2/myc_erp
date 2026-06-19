export const catalogCommodityOptions = [
  { value: 'calibration', label: 'Calibracion' },
  { value: 'maintenance', label: 'Mantenimiento' },
  { value: 'repair', label: 'Reparacion' },
  { value: 'sale', label: 'Venta' },
  { value: 'general_service', label: 'Servicio general' }
];

export const calibrationScopeOptions = [
  { value: 'accredited_iso_17025', label: 'Acreditado ISO/IEC 17025:2017' },
  { value: 'traceable', label: 'Trazable' },
  { value: 'accredited_linked_lab', label: 'Acreditado laboratorio vinculado' }
];

export const internalUnitOptions = [
  { value: 'service', label: 'Servicio' },
  { value: 'piece', label: 'Pieza' },
  { value: 'equipment', label: 'Equipo' },
  { value: 'hour', label: 'Hora' },
  { value: 'day', label: 'Dia' },
  { value: 'package', label: 'Paquete' },
  { value: 'lot', label: 'Lote' },
  { value: 'meter', label: 'Metro' },
  { value: 'kilogram', label: 'Kilogramo' },
  { value: 'liter', label: 'Litro' },
  { value: 'other', label: 'Otra' }
];

export const taxObjectOptions = [
  { value: 'iva_16', label: 'IVA 16%' },
  { value: 'iva_0', label: 'IVA 0%' },
  { value: 'exempt', label: 'Exento' },
  { value: 'not_subject', label: 'No sujeto' }
];

export const serviceCategories = [
  'Calibracion',
  'Mantenimiento',
  'Calificacion',
  'Validacion',
  'Capacitacion',
  'Consultoria'
];

export const productCategories = [
  'Patrones',
  'Equipos',
  'Accesorios',
  'Consumibles'
];

export const validCatalogCurrencies = new Set(['MXN', 'USD', 'EUR']);

export const catalogTypeToApi = {
  Producto: 'product',
  Servicio: 'service'
};

export const catalogTypeFromApi = {
  product: 'Producto',
  service: 'Servicio'
};