export const calibrationScopeOptions = [
  { value: 'accredited_iso_17025', label: 'Acreditación propia ISO/IEC 17025' },
  { value: 'traceable', label: 'Trazable / no acreditado' },
  { value: 'accredited_linked_lab', label: 'Acreditación por laboratorio vinculado' }
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
  Verificacion: 'verification',
  Calificacion: 'qualification',
  Validacion: 'validation',
  Capacitacion: 'training',
  Consultoria: 'consulting',
  Venta: 'sale',
  'Servicio general': 'general_service',
  Otro: 'other'
};

export const catalogOperationalCategoryOptions = [
  { value: 'calibration', label: 'Calibración', category: 'Calibracion' },
  { value: 'maintenance', label: 'Mantenimiento', category: 'Mantenimiento' },
  { value: 'repair', label: 'Reparación', category: 'Reparacion' },
  { value: 'verification', label: 'Verificación', category: 'Verificacion' },
  { value: 'qualification', label: 'Calificación', category: 'Calificacion' },
  { value: 'validation', label: 'Validación', category: 'Validacion' },
  { value: 'training', label: 'Capacitación', category: 'Capacitacion' },
  { value: 'consulting', label: 'Consultoría', category: 'Consultoria' },
  { value: 'general_service', label: 'Servicio general', category: 'Servicio general' },
  { value: 'sale', label: 'Venta', category: 'Venta' },
  { value: 'other', label: 'Otra', category: 'Otro' }
];

export function operationalCategoryFromCatalogCategory(category) {
  return catalogKindByCategory[category] ?? 'other';
}

export function catalogCategoryFromOperationalCategory(operationalCategory, fallback = '') {
  return catalogOperationalCategoryOptions.find((option) => option.value === operationalCategory)?.category ?? fallback;
}

export function operationalCategoryFromCatalogForm(form) {
  const value = form?.operationalCategory ?? '';
  return catalogOperationalCategoryOptions.some((option) => option.value === value) ? value : '';
}

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
  'Verificacion',
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
