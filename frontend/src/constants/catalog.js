export const calibrationScopeOptions = [
  { value: 'accredited_iso_17025', label: 'Acreditado ISO/IEC 17025' },
  { value: 'traceable', label: 'Trazable' },
  { value: 'accredited_linked_lab', label: 'Laboratorio vinculado' }
];

export const scopeOptionsByCategory = {
  Calibracion: calibrationScopeOptions,
  Mantenimiento: [
    { value: 'preventive', label: 'Preventivo' },
    { value: 'corrective', label: 'Correctivo' }
  ],
  Capacitacion: [
    { value: 'onsite', label: 'Presencial' },
    { value: 'online', label: 'En linea' },
    { value: 'hybrid', label: 'Mixta' }
  ],
  Validacion: [
    { value: 'documentary', label: 'Documental' },
    { value: 'onsite', label: 'En sitio' },
    { value: 'protocol', label: 'Protocolo' }
  ],
  Calificacion: [
    { value: 'installation', label: 'Instalacion' },
    { value: 'operation', label: 'Operacion' },
    { value: 'performance', label: 'Desempeno' }
  ],
  Consultoria: [
    { value: 'technical', label: 'Tecnica' },
    { value: 'regulatory', label: 'Normativa' },
    { value: 'implementation', label: 'Implementacion' }
  ]
};

export const catalogKindByCategory = {
  Calibracion: 'calibration',
  Mantenimiento: 'maintenance',
  Reparacion: 'repair',
  Venta: 'sale',
  'Servicio general': 'general_service'
};

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
  'Reparacion',
  'Calificacion',
  'Validacion',
  'Capacitacion',
  'Consultoria',
  'Servicio general'
];

export const productCategories = [
  'Venta',
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
