function column(key, label, width = null, extra = {}) {
  return { key, label, source: key, width, unit: null, editable: true, required: false, data_type: 'text', ...extra };
}

export const fieldSheetFieldCatalog = {
  work_order_number: { label: 'Orden de trabajo', field_type: 'text' },
  reserved_certificate_folio: { label: 'Folio reservado del certificado', field_type: 'text' },
  certificate_number: { label: 'Certificado No.', field_type: 'text' },
  attention: { label: 'Atención', field_type: 'text' },
  company: { label: 'Empresa', field_type: 'text' },
  address: { label: 'Dirección', field_type: 'textarea' },
  instrument: { label: 'Instrumento', field_type: 'text' },
  scope: { label: 'Alcance', field_type: 'text' },
  minimum_division: { label: 'División mínima', field_type: 'text' },
  brand: { label: 'Marca', field_type: 'text' },
  serial_number: { label: 'No. serie', field_type: 'text' },
  model: { label: 'Modelo', field_type: 'text' },
  internal_id: { label: 'Identificación interna', field_type: 'text' },
  location: { label: 'Ubicación', field_type: 'text' },
  calibration_place: { label: 'Lugar de calibración', field_type: 'text' },
  reception_date: { label: 'Fecha de recepción', field_type: 'date' },
  calibration_date: { label: 'Fecha de calibración', field_type: 'date' },
  next_calibration_date: { label: 'Próxima calibración', field_type: 'date' },
  humidity_start: { label: 'Humedad inicial', field_type: 'decimal' },
  humidity_end: { label: 'Humedad final', field_type: 'decimal' },
  temperature_start: { label: 'Temperatura inicial', field_type: 'decimal' },
  temperature_end: { label: 'Temperatura final', field_type: 'decimal' },
  initial_condition: { label: 'Condición inicial', field_type: 'textarea' },
  final_condition: { label: 'Condición final', field_type: 'textarea' },
  method: { label: 'Método', field_type: 'text' },
  units: { label: 'Unidades', field_type: 'text' },
  observations: { label: 'Observaciones', field_type: 'textarea' },
  evidence_notes: { label: 'Evidencia / notas', field_type: 'textarea' },
  pattern_used: { label: 'Patrón usado', field_type: 'textarea' },
  calibrated_by: { label: 'Calibró', field_type: 'text' },
  reviewed_by: { label: 'Revisó', field_type: 'text' },
  report_made_by: { label: 'Elaboró reporte', field_type: 'text' },
  purchase_order_or_quotation: { label: 'Orden de compra / cotización', field_type: 'text' },
};

export const tableFamilyDefinitions = {
  direct_comparison: { family_key: 'direct_comparison', name: 'Comparación directa', description: 'Patrón contra indicación', default_rows: 10, min_rows: 3, max_rows: 20, allow_add_rows: true, allow_remove_rows: true, allow_sections: false },
  multipoint: { family_key: 'multipoint', name: 'Multipunto', description: 'Puntos nominales o de prueba', default_rows: 10, min_rows: 3, max_rows: 20, allow_add_rows: true, allow_remove_rows: true, allow_sections: true },
  pressure: { family_key: 'pressure', name: 'Presión', description: 'Ascendente y descendente', default_rows: 10, min_rows: 3, max_rows: 20, allow_add_rows: true, allow_remove_rows: true, allow_sections: false },
  dimensional: { family_key: 'dimensional', name: 'Dimensional', description: 'Longitud y dimensión', default_rows: 10, min_rows: 3, max_rows: 20, allow_add_rows: true, allow_remove_rows: true, allow_sections: true },
  mass: { family_key: 'mass', name: 'Masa', description: 'Carga y repetibilidad', default_rows: 10, min_rows: 3, max_rows: 20, allow_add_rows: true, allow_remove_rows: true, allow_sections: true },
  electrical: { family_key: 'electrical', name: 'Eléctrica', description: 'Múltiples magnitudes', default_rows: 5, min_rows: 3, max_rows: 10, allow_add_rows: true, allow_remove_rows: true, allow_sections: true },
  repeatability: { family_key: 'repeatability', name: 'Repetibilidad', description: 'Lecturas repetidas', default_rows: 5, min_rows: 3, max_rows: 10, allow_add_rows: true, allow_remove_rows: true, allow_sections: false },
  custom: { family_key: 'custom', name: 'Libre', description: 'Columnas configurables', default_rows: 5, min_rows: 1, max_rows: 50, allow_add_rows: true, allow_remove_rows: true, allow_sections: true },
};

export const fieldSheetBlockFamilies = {
  HeaderBlock: { title: 'Encabezado', visible_fields: ['work_order_number', 'reserved_certificate_folio'] },
  ClientBlock: { title: 'Cliente', visible_fields: ['attention', 'company', 'address'] },
  ServiceOrderBlock: { title: 'Orden de servicio', visible_fields: ['work_order_number', 'purchase_order_or_quotation'] },
  EquipmentBlock: { title: 'Equipo', visible_fields: ['instrument', 'scope', 'minimum_division', 'brand', 'serial_number', 'model', 'internal_id', 'location'] },
  CalibrationDataBlock: { title: 'Datos de calibración', visible_fields: ['calibration_place', 'reception_date', 'calibration_date', 'next_calibration_date', 'units', 'method'] },
  EnvironmentalBlock: { title: 'Condiciones ambientales', visible_fields: ['humidity_start', 'temperature_start', 'humidity_end', 'temperature_end'] },
  StandardsBlock: { title: 'Patrones', visible_fields: ['pattern_used'] },
  ObservationsBlock: { title: 'Datos técnicos', visible_fields: ['initial_condition', 'final_condition', 'observations', 'evidence_notes'] },
  SignaturesBlock: { title: 'Firmas', visible_fields: ['calibrated_by', 'reviewed_by', 'report_made_by'] },
  FooterBlock: { title: 'Pie', visible_fields: ['purchase_order_or_quotation'] },
  CustomFieldsBlock: { title: 'Campos libres', visible_fields: [] },
  SectionBlock: { title: 'Sección', visible_fields: [] },
  AttachmentPlaceholderBlock: { title: 'Adjuntos', visible_fields: [] },
  GeneralDataBlock: { title: 'Datos generales', visible_fields: ['work_order_number', 'reserved_certificate_folio', 'attention', 'company', 'address'] },
  EquipmentDataBlock: { title: 'Datos del equipo', visible_fields: ['instrument', 'brand', 'model', 'serial_number', 'internal_id', 'location', 'minimum_division'] },
};

const simpleComparisonColumns = [
  column('pattern_value', 'Patrón', '18%'),
  column('instrument_reading', 'Indicación instrumento'),
  column('error_value', 'Error'),
  column('unit', 'Unidad', '12%'),
  column('notes', 'Observaciones', '18%'),
];
const multiPointColumns = [
  column('nominal_point', 'Punto nominal'),
  column('pattern_value', 'Patrón'),
  column('instrument_reading', 'Indicación instrumento'),
  column('result_value', 'Resultado'),
  column('unit', 'Unidad', '12%'),
  column('notes', 'Observaciones', '18%'),
];
const repeatabilityColumns = [
  column('point_label', 'Punto'),
  column('reading_1', 'Lectura 1'),
  column('reading_2', 'Lectura 2'),
  column('reading_3', 'Lectura 3'),
  column('average_value', 'Resultado manual'),
  column('unit', 'Unidad', '12%'),
  column('notes', 'Observaciones', '18%'),
];
const dimensionalColumns = [
  column('nominal_length', 'Longitud nominal'),
  column('pattern_reading', 'Lectura patrón'),
  column('instrument_reading', 'Lectura instrumento'),
  column('error_value', 'Error'),
  column('unit', 'Unidad', '12%'),
  column('notes', 'Observaciones', '18%'),
];
const pressureColumns = [
  column('nominal_point', 'Punto nominal'),
  column('ascending_pattern', 'Asc. patrón'),
  column('ascending_instrument', 'Asc. instrumento'),
  column('descending_pattern', 'Desc. patrón'),
  column('descending_instrument', 'Desc. instrumento'),
  column('error_value', 'Error'),
  column('unit', 'Unidad', '12%'),
  column('notes', 'Observaciones', '18%'),
];
const massColumns = [
  column('applied_load', 'Carga aplicada'),
  column('instrument_reading', 'Indicación'),
  column('error_value', 'Error'),
  column('eccentricity_value', 'Excentricidad'),
  column('repeatability_value', 'Repetibilidad'),
  column('unit', 'Unidad', '12%'),
  column('notes', 'Observaciones', '18%'),
];
const electricalColumns = [
  column('nominal_point', 'Punto nominal'),
  column('pattern_value', 'Patrón'),
  column('instrument_reading', 'Indicación instrumento'),
  column('error_value', 'Error'),
  column('unit', 'Unidad', '12%'),
  column('notes', 'Observaciones', '18%'),
];

export const templateNameByKey = {
  general: 'Hoja de Campo General',
  temperatura: 'Hoja de Campo Temperatura',
  termometro: 'Hoja de Campo Termómetro',
  termohigrometro: 'Hoja de Campo Termohigrómetro',
  cronometro: 'Hoja de Campo Cronómetro',
  tacometro: 'Hoja de Campo Tacómetro',
  anemometro: 'Hoja de Campo Anemómetro',
  manometro: 'Hoja de Campo Manómetro',
  transductor_presion: 'Hoja de Campo Transductor de Presión',
  valvula: 'Hoja de Campo Válvula',
  dimensional: 'Hoja de Campo Dimensional',
  regla: 'Hoja de Campo Regla',
  vernier: 'Hoja de Campo Vernier',
  micrometro: 'Hoja de Campo Micrómetro',
  flexometro: 'Hoja de Campo Flexómetro',
  masa: 'Hoja de Campo Masa',
  balanza: 'Hoja de Campo Balanza',
  bascula: 'Hoja de Campo Báscula',
  peso_patron: 'Hoja de Campo Peso Patrón',
  electrica: 'Hoja de Campo Eléctrica',
  multimetro: 'Hoja de Campo Multímetro',
  luxometro: 'Hoja de Campo Luxómetro',
  sonido: 'Hoja de Campo Sonido',
  sonometro: 'Hoja de Campo Sonómetro',
  torquimetro: 'Hoja de Campo Torquímetro',
  dinamometro: 'Hoja de Campo Dinamómetro',
  durometro: 'Hoja de Campo Durómetro',
  volumen: 'Hoja de Campo Volumen',
};

const templateAssignments = {
  general: ['HeaderBlock', 'ClientBlock', 'EquipmentBlock', 'CalibrationDataBlock', 'EnvironmentalBlock', 'SimpleComparisonTableBlock', 'ObservationsBlock', 'SignaturesBlock', 'FooterBlock'],
  temperatura: ['HeaderBlock', 'ClientBlock', 'EquipmentBlock', 'CalibrationDataBlock', 'EnvironmentalBlock', 'SimpleComparisonTableBlock', 'ObservationsBlock', 'SignaturesBlock', 'FooterBlock'],
  termometro: ['HeaderBlock', 'ClientBlock', 'EquipmentBlock', 'CalibrationDataBlock', 'EnvironmentalBlock', 'SimpleComparisonTableBlock', 'ObservationsBlock', 'SignaturesBlock', 'FooterBlock'],
  termohigrometro: ['HeaderBlock', 'ClientBlock', 'EquipmentBlock', 'CalibrationDataBlock', 'EnvironmentalBlock', 'SimpleComparisonTableBlock', 'ObservationsBlock', 'SignaturesBlock', 'FooterBlock'],
  cronometro: ['HeaderBlock', 'ClientBlock', 'EquipmentBlock', 'CalibrationDataBlock', 'EnvironmentalBlock', 'SimpleComparisonTableBlock', 'RepeatabilityTableBlock', 'ObservationsBlock', 'SignaturesBlock', 'FooterBlock'],
  tacometro: ['HeaderBlock', 'ClientBlock', 'EquipmentBlock', 'CalibrationDataBlock', 'EnvironmentalBlock', 'SimpleComparisonTableBlock', 'RepeatabilityTableBlock', 'ObservationsBlock', 'SignaturesBlock', 'FooterBlock'],
  anemometro: ['HeaderBlock', 'ClientBlock', 'EquipmentBlock', 'CalibrationDataBlock', 'EnvironmentalBlock', 'MultiPointTableBlock', 'ObservationsBlock', 'SignaturesBlock', 'FooterBlock'],
  manometro: ['HeaderBlock', 'ClientBlock', 'EquipmentBlock', 'CalibrationDataBlock', 'EnvironmentalBlock', 'PressureTableBlock', 'ObservationsBlock', 'SignaturesBlock', 'FooterBlock'],
  transductor_presion: ['HeaderBlock', 'ClientBlock', 'EquipmentBlock', 'CalibrationDataBlock', 'EnvironmentalBlock', 'PressureTableBlock', 'ObservationsBlock', 'SignaturesBlock', 'FooterBlock'],
  valvula: ['HeaderBlock', 'ClientBlock', 'EquipmentBlock', 'CalibrationDataBlock', 'EnvironmentalBlock', 'PressureTableBlock', 'ObservationsBlock', 'SignaturesBlock', 'FooterBlock'],
  dimensional: ['HeaderBlock', 'ClientBlock', 'EquipmentBlock', 'CalibrationDataBlock', 'EnvironmentalBlock', 'DimensionalTableBlock', 'ObservationsBlock', 'SignaturesBlock', 'FooterBlock'],
  regla: ['HeaderBlock', 'ClientBlock', 'EquipmentBlock', 'CalibrationDataBlock', 'EnvironmentalBlock', 'DimensionalTableBlock', 'ObservationsBlock', 'SignaturesBlock', 'FooterBlock'],
  vernier: ['HeaderBlock', 'ClientBlock', 'EquipmentBlock', 'CalibrationDataBlock', 'EnvironmentalBlock', 'DimensionalTableBlock', 'ObservationsBlock', 'SignaturesBlock', 'FooterBlock'],
  micrometro: ['HeaderBlock', 'ClientBlock', 'EquipmentBlock', 'CalibrationDataBlock', 'EnvironmentalBlock', 'DimensionalTableBlock', 'RepeatabilityTableBlock', 'ObservationsBlock', 'SignaturesBlock', 'FooterBlock'],
  flexometro: ['HeaderBlock', 'ClientBlock', 'EquipmentBlock', 'CalibrationDataBlock', 'EnvironmentalBlock', 'DimensionalTableBlock', 'ObservationsBlock', 'SignaturesBlock', 'FooterBlock'],
  masa: ['HeaderBlock', 'ClientBlock', 'EquipmentBlock', 'CalibrationDataBlock', 'EnvironmentalBlock', 'MassBalanceTableBlock', 'ObservationsBlock', 'SignaturesBlock', 'FooterBlock'],
  balanza: ['HeaderBlock', 'ClientBlock', 'EquipmentBlock', 'CalibrationDataBlock', 'EnvironmentalBlock', 'MassBalanceTableBlock', 'RepeatabilityTableBlock', 'ObservationsBlock', 'SignaturesBlock', 'FooterBlock'],
  bascula: ['HeaderBlock', 'ClientBlock', 'EquipmentBlock', 'CalibrationDataBlock', 'EnvironmentalBlock', 'MassBalanceTableBlock', 'RepeatabilityTableBlock', 'ObservationsBlock', 'SignaturesBlock', 'FooterBlock'],
  peso_patron: ['HeaderBlock', 'ClientBlock', 'EquipmentBlock', 'CalibrationDataBlock', 'EnvironmentalBlock', 'MassBalanceTableBlock', 'ObservationsBlock', 'SignaturesBlock', 'FooterBlock'],
  electrica: ['HeaderBlock', 'ClientBlock', 'EquipmentBlock', 'CalibrationDataBlock', 'EnvironmentalBlock', 'ElectricalTableBlock', 'SectionedTableBlock', 'ObservationsBlock', 'SignaturesBlock', 'FooterBlock'],
  multimetro: ['HeaderBlock', 'ClientBlock', 'EquipmentBlock', 'CalibrationDataBlock', 'EnvironmentalBlock', 'ElectricalTableBlock', 'SectionedTableBlock', 'ObservationsBlock', 'SignaturesBlock', 'FooterBlock'],
  luxometro: ['HeaderBlock', 'ClientBlock', 'EquipmentBlock', 'CalibrationDataBlock', 'EnvironmentalBlock', 'MultiPointTableBlock', 'ObservationsBlock', 'SignaturesBlock', 'FooterBlock'],
  sonido: ['HeaderBlock', 'ClientBlock', 'EquipmentBlock', 'CalibrationDataBlock', 'EnvironmentalBlock', 'MultiPointTableBlock', 'ObservationsBlock', 'SignaturesBlock', 'FooterBlock'],
  sonometro: ['HeaderBlock', 'ClientBlock', 'EquipmentBlock', 'CalibrationDataBlock', 'EnvironmentalBlock', 'MultiPointTableBlock', 'ObservationsBlock', 'SignaturesBlock', 'FooterBlock'],
  torquimetro: ['HeaderBlock', 'ClientBlock', 'EquipmentBlock', 'CalibrationDataBlock', 'EnvironmentalBlock', 'MultiPointTableBlock', 'RepeatabilityTableBlock', 'ObservationsBlock', 'SignaturesBlock', 'FooterBlock'],
  dinamometro: ['HeaderBlock', 'ClientBlock', 'EquipmentBlock', 'CalibrationDataBlock', 'EnvironmentalBlock', 'MultiPointTableBlock', 'RepeatabilityTableBlock', 'ObservationsBlock', 'SignaturesBlock', 'FooterBlock'],
  durometro: ['HeaderBlock', 'ClientBlock', 'EquipmentBlock', 'CalibrationDataBlock', 'EnvironmentalBlock', 'MultiPointTableBlock', 'ObservationsBlock', 'SignaturesBlock', 'FooterBlock'],
  volumen: ['HeaderBlock', 'ClientBlock', 'EquipmentBlock', 'CalibrationDataBlock', 'EnvironmentalBlock', 'MultiPointTableBlock', 'RepeatabilityTableBlock', 'ObservationsBlock', 'SignaturesBlock', 'FooterBlock'],
};

const templateTableFamily = {
  general: 'direct_comparison',
  temperatura: 'direct_comparison',
  termometro: 'direct_comparison',
  termohigrometro: 'direct_comparison',
  cronometro: 'direct_comparison',
  tacometro: 'direct_comparison',
  anemometro: 'multipoint',
  luxometro: 'multipoint',
  sonido: 'multipoint',
  sonometro: 'multipoint',
  torquimetro: 'multipoint',
  dinamometro: 'multipoint',
  durometro: 'multipoint',
  volumen: 'multipoint',
  manometro: 'pressure',
  transductor_presion: 'pressure',
  valvula: 'pressure',
  dimensional: 'dimensional',
  regla: 'dimensional',
  vernier: 'dimensional',
  micrometro: 'dimensional',
  flexometro: 'dimensional',
  masa: 'mass',
  balanza: 'mass',
  bascula: 'mass',
  peso_patron: 'mass',
  electrica: 'electrical',
  multimetro: 'electrical',
};

function buildBlock(blockType, order) {
  const common = {
    title: fieldSheetBlockFamilies[blockType]?.title ?? blockType,
    visible_fields: fieldSheetBlockFamilies[blockType]?.visible_fields ?? [],
    fields: [],
    required: ['HeaderBlock', 'ClientBlock', 'EquipmentBlock', 'ObservationsBlock', 'SignaturesBlock'].includes(blockType),
    print_order: order,
    capture_order: order,
    order,
    allow_add_rows: false,
    allow_remove_rows: false,
    rows: null,
    min_rows: null,
    max_rows: null,
    columns: [],
    sections: [],
    table_config: {},
    suggested_unit: null,
    visible: true,
    print_visible: true,
    capture_visible: true,
    pdf_visible: true,
    metadata: {},
  };
  switch (blockType) {
    case 'SimpleComparisonTableBlock':
    case 'ResultsTableBlock':
      return { ...common, key: `simple_comparison_${order}`, block_key: `simple_comparison_${order}`, block_type: blockType, title: 'Tabla comparativa', allow_add_rows: true, allow_remove_rows: true, rows: 10, min_rows: 3, max_rows: 20, columns: simpleComparisonColumns };
    case 'MultiPointTableBlock':
      return { ...common, key: `multi_point_${order}`, block_key: `multi_point_${order}`, block_type: blockType, title: 'Tabla multipunto', allow_add_rows: true, allow_remove_rows: true, rows: 10, min_rows: 3, max_rows: 20, columns: multiPointColumns };
    case 'RepeatabilityTableBlock':
      return { ...common, key: `repeatability_${order}`, block_key: `repeatability_${order}`, block_type: blockType, title: 'Tabla de repetibilidad', allow_add_rows: true, allow_remove_rows: true, rows: 5, min_rows: 3, max_rows: 10, columns: repeatabilityColumns };
    case 'DimensionalTableBlock':
      return { ...common, key: `dimensional_${order}`, block_key: `dimensional_${order}`, block_type: blockType, title: 'Tabla dimensional', allow_add_rows: true, allow_remove_rows: true, rows: 10, min_rows: 3, max_rows: 20, columns: dimensionalColumns };
    case 'PressureTableBlock':
      return { ...common, key: `pressure_${order}`, block_key: `pressure_${order}`, block_type: blockType, title: 'Tabla de presión', allow_add_rows: true, allow_remove_rows: true, rows: 8, min_rows: 3, max_rows: 20, columns: pressureColumns };
    case 'MassBalanceTableBlock':
      return { ...common, key: `mass_balance_${order}`, block_key: `mass_balance_${order}`, block_type: blockType, title: 'Tabla masa / balanza', allow_add_rows: true, allow_remove_rows: true, rows: 8, min_rows: 3, max_rows: 20, columns: massColumns };
    case 'ElectricalTableBlock':
      return {
        ...common,
        key: `electrical_${order}`,
        block_key: `electrical_${order}`,
        block_type: blockType,
        title: 'Tabla eléctrica',
        allow_add_rows: true,
        allow_remove_rows: true,
        rows: 5,
        min_rows: 3,
        max_rows: 10,
        columns: electricalColumns,
        sections: [
          { key: 'voltage_ac', title: 'Voltaje AC', rows: 5, columns: electricalColumns },
          { key: 'voltage_dc', title: 'Voltaje DC', rows: 5, columns: electricalColumns },
          { key: 'current_ac', title: 'Corriente AC', rows: 5, columns: electricalColumns },
          { key: 'current_dc', title: 'Corriente DC', rows: 5, columns: electricalColumns },
          { key: 'resistance', title: 'Resistencia', rows: 5, columns: electricalColumns },
          { key: 'frequency', title: 'Frecuencia', rows: 5, columns: electricalColumns },
          { key: 'continuity', title: 'Continuidad', rows: 5, columns: electricalColumns },
        ],
      };
    case 'SectionedTableBlock':
      return {
        ...common,
        key: `sectioned_${order}`,
        block_key: `sectioned_${order}`,
        block_type: blockType,
        title: 'Secciones personalizadas',
        allow_add_rows: true,
        allow_remove_rows: true,
        rows: 5,
        min_rows: 1,
        max_rows: 20,
        columns: electricalColumns,
        sections: [{ key: 'custom_section', title: 'Sección personalizada', rows: 5, columns: electricalColumns }],
      };
    default:
      return { ...common, key: `${blockType}_${order}`, block_key: `${blockType}_${order}`, block_type: blockType };
  }
}

function buildResultSections(blocks = []) {
  return blocks
    .filter((block) => String(block.block_type || '').includes('TableBlock') || block.block_type === 'ResultsTableBlock')
    .flatMap((block) => {
      if (Array.isArray(block.sections) && block.sections.length) {
        return block.sections.map((section) => ({
          key: section.key,
          title: section.title,
          rows: section.rows,
          columns: section.columns,
          min_rows: section.min_rows ?? block.min_rows ?? block.rows ?? 1,
          max_rows: section.max_rows ?? block.max_rows ?? block.rows ?? 1,
          allow_add_rows: section.allow_add_rows ?? block.allow_add_rows ?? false,
          allow_remove_rows: section.allow_remove_rows ?? block.allow_remove_rows ?? false,
        }));
      }
      return [{
        key: block.key,
        title: block.title,
        rows: block.rows ?? 1,
        columns: block.columns ?? [],
        min_rows: block.min_rows ?? block.rows ?? 1,
        max_rows: block.max_rows ?? block.rows ?? 1,
        allow_add_rows: block.allow_add_rows ?? false,
        allow_remove_rows: block.allow_remove_rows ?? false,
      }];
    });
}

function buildVisibleFields(blocks = []) {
  return blocks.flatMap((block) => block.visible_fields ?? []).filter((value, index, array) => array.indexOf(value) === index);
}

function buildFallbackTemplate(templateKey) {
  const blocks = (templateAssignments[templateKey] ?? templateAssignments.general).map((blockType, index) => buildBlock(blockType, index + 1));
  return {
    id: null,
    source: 'fallback',
    template_key: templateKey,
    key: templateKey,
    name: templateNameByKey[templateKey] ?? templateNameByKey.general,
    description: '',
    type: templateKey,
    status: 'active',
    version: 1,
    is_active: true,
    code: 'FCA-30',
    revision: 'R1',
    document_code: 'FCA-30',
    document_revision: 'R1',
    pages: templateKey === 'electrica' ? 2 : 1,
    pdf_template: templateKey === 'electrica' ? 'field_sheet_electrical_pdf.html' : templateKey === 'anemometro' ? 'field_sheet_anemometer_pdf.html' : 'field_sheet_general_pdf.html',
    table_family: templateTableFamily[templateKey] ?? 'custom',
    blocks,
    visible_fields: buildVisibleFields(blocks),
    result_sections: buildResultSections(blocks),
    validations: {},
    print_config: {},
    pdf_config: {},
    permissions_config: {},
    metadata: {},
  };
}

export const fieldSheetTemplates = Object.fromEntries(Object.keys(templateAssignments).map((key) => [key, buildFallbackTemplate(key)]));

export const fieldSheetTemplateOptions = Object.values(fieldSheetTemplates).map((template) => ({
  value: template.key,
  label: template.name,
}));

export function normalizeFieldSheetTemplate(template) {
  if (!template) return fieldSheetTemplates.general;
  const fallback = fieldSheetTemplates[template.template_key || template.key || 'general'] ?? fieldSheetTemplates.general;
  const blocks = Array.isArray(template.blocks) && template.blocks.length ? template.blocks : fallback.blocks;
  return {
    ...fallback,
    ...template,
    key: template.key || template.template_key,
    template_key: template.template_key || template.key,
    blocks,
    table_family: template.table_family || fallback.table_family || 'custom',
    visible_fields: template.visible_fields?.length ? template.visible_fields : buildVisibleFields(blocks),
    result_sections: template.result_sections?.length ? template.result_sections : buildResultSections(blocks),
    validations: template.validations ?? {},
    print_config: template.print_config ?? {},
    pdf_config: template.pdf_config ?? {},
    permissions_config: template.permissions_config ?? {},
    metadata: template.metadata ?? {},
  };
}

export function getFieldSheetTemplate(templateKey = 'general', templatesByKey = null) {
  const source = templatesByKey?.[templateKey];
  return normalizeFieldSheetTemplate(source ?? fieldSheetTemplates[templateKey] ?? fieldSheetTemplates.general);
}

export function getFieldSheetTemplateLabel(templateKey = 'general', templatesByKey = null) {
  return getFieldSheetTemplate(templateKey, templatesByKey).name;
}
