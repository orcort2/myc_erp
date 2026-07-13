const standardFields = {
  customer: ['attention', 'company', 'address'],
  equipment: ['instrument', 'scope', 'minimum_division', 'brand', 'serial_number', 'model', 'internal_id', 'location'],
  calibration: ['calibration_place', 'reception_date', 'calibration_date', 'next_calibration_date', 'units', 'method'],
  environment: ['humidity_start', 'temperature_start', 'humidity_end', 'temperature_end'],
  observations: ['initial_condition', 'final_condition', 'observations', 'evidence_notes'],
};

function column(key, label, extra = {}) {
  return { key, label, source: key, editable: true, data_type: 'text', ...extra };
}

function section(key, title, rows, columns, metadata = {}) {
  return {
    key,
    title,
    rows,
    min_rows: rows,
    max_rows: Math.max(rows, 30),
    allow_add_rows: !metadata.fixed_rows,
    allow_remove_rows: !metadata.fixed_rows,
    columns,
    metadata,
  };
}

function block(blockType, order, options = {}) {
  return {
    key: options.key || `${blockType}_${order}`,
    block_key: options.key || `${blockType}_${order}`,
    block_type: blockType,
    title: options.title || '',
    visible_fields: options.visible_fields || [],
    fields: options.fields || [],
    sections: options.sections || [],
    columns: options.columns || [],
    metadata: options.metadata || {},
    capture_order: order,
    print_order: order,
    order,
    visible: true,
    capture_visible: true,
    print_visible: true,
    pdf_visible: true,
  };
}

const commonColumns = {
  replicated3: [column('pattern_value', 'Patrón'), column('ibc_1', 'IBC 1'), column('ibc_2', 'IBC 2'), column('ibc_3', 'IBC 3')],
  ordinal3: [column('pattern_value', 'Patrón'), column('ibc_1', 'Primera IBC'), column('ibc_2', 'Segunda IBC'), column('ibc_3', 'Tercera IBC')],
  inverse3: [column('ibc_value', 'IBC'), column('pattern_1', 'Patrón 1'), column('pattern_2', 'Patrón 2'), column('pattern_3', 'Patrón 3')],
};

function commonBlocks(tableType, sections, options = {}) {
  const equipmentFields = options.equipment_fields || standardFields.equipment;
  return [
    block('HeaderBlock', 1, { title: 'Encabezado' }),
    block('ClientBlock', 2, { title: options.customer_title || 'Cliente', visible_fields: standardFields.customer }),
    block('EquipmentBlock', 3, {
      title: options.equipment_title || 'Equipo',
      visible_fields: equipmentFields,
      fields: options.extra_equipment_fields || [],
    }),
    block('CalibrationDataBlock', 4, { title: 'Datos de calibración', visible_fields: standardFields.calibration }),
    block('EnvironmentalBlock', 5, { title: 'Condiciones ambientales', visible_fields: standardFields.environment }),
    block(tableType, 6, { key: options.table_key || 'measurements', title: 'Resultados de la calibración', sections }),
    ...(options.extra_blocks || []),
    block('ObservationsBlock', 8, { title: options.observations_title || 'Observaciones', visible_fields: standardFields.observations }),
    block('SignaturesBlock', 9, { title: 'Firmas' }),
    block('FooterBlock', 10, { title: 'Pie', visible_fields: ['purchase_order_or_quotation'] }),
  ];
}

function signatureLayout(slots = null, layout = 'three_columns') {
  return {
    layout,
    slots: slots || [
      { role: 'calibrated_by', display_label: 'Calibró' },
      { role: 'reviewed_by', display_label: 'Revisó' },
      { role: 'report_made_by', display_label: 'Elaboró informe' },
    ],
  };
}

function template(key, name, family, blocks, expectedPages = 1, extra = {}) {
  const resultSections = blocks.flatMap((item) => item.sections || []);
  return {
    key,
    template_key: key,
    name: `Hoja de Campo ${name}`,
    subtitle: extra.subtitle || '',
    version: extra.version || 1,
    code: 'FCA-30',
    revision: 'R1',
    document_code: 'FCA-30',
    document_revision: 'R1',
    status: 'active',
    is_active: true,
    source: 'official-lab',
    table_family: family,
    pages: expectedPages,
    blocks,
    result_sections: resultSections,
    signature_layout: extra.signature_layout || signatureLayout(),
    pagination: { mode: 'dynamic', repeat_header: true, repeat_table_header: true, expected_pages: expectedPages },
    automation: { mode: 'manual_only', calculations: [] },
    metadata: { official_reference: true, expected_pages: expectedPages, ambiguous_labels: extra.ambiguous_labels || false },
  };
}

const templates = [
  template('anemometro', 'Anemómetro', 'replicated_comparison', commonBlocks('ReplicatedComparisonTableBlock', [section('measurements', 'Resultados de la calibración', 10, commonColumns.replicated3)])),
  template('angulimetro', 'Angulímetro', 'replicated_comparison', commonBlocks('ReplicatedComparisonTableBlock', [section('measurements', 'Resultados de la calibración', 5, commonColumns.ordinal3)])),
  template('bascula', 'Báscula y Balanza', 'mass_balance_composite', commonBlocks('CompositeTestTableBlock', [
    section('eccentricity_cycle', 'Excentricidad y ciclo', 6, [column('pattern_value', 'Patrón'), column('ibc_1', 'IBC 1'), column('ibc_2', 'IBC 2'), column('ibc_3', 'IBC 3')], { label_configurable: true }),
    section('repeatability_50', 'Repetibilidad al 50 %', 5, [column('pattern_value', 'Patrón'), column('indication', 'Indicación')]),
    section('repeatability_100', 'Repetibilidad al 100 %', 5, [column('pattern_value', 'Patrón'), column('indication', 'Indicación')]),
  ]), 1, { ambiguous_labels: true, version: 3 }),
  template('calibradores', 'Calibradores', 'replicated_comparison', commonBlocks('SectionedTableBlock', [
    section('exterior', 'Medición de exteriores', 7, commonColumns.replicated3),
    section('interior', 'Medición de interiores', 5, commonColumns.replicated3),
    section('depth', 'Medición de profundidades', 3, commonColumns.replicated3),
  ])),
  template('cronometro', 'Cronómetro', 'replicated_comparison', commonBlocks('ReplicatedComparisonTableBlock', [section('measurements', 'Resultados de la calibración', 5, [
    column('pattern_value', 'Patrón'), column('ibc_1', 'IBC 1'), column('ibc_2', 'IBC 2'), column('ibc_3', 'IBC 3'), column('ibc_4', 'IBC 4'), column('ibc_5', 'IBC 5'),
  ], { note: 'Fórmula conservada únicamente como nota técnica manual.' })])),
  template('detector_gases', 'Detector de Gases', 'before_after', commonBlocks('BeforeAfterTableBlock', [
    section('before_adjustment', 'Antes del ajuste', 4, [column('gas', 'Gas'), column('pattern_value', 'Patrón'), column('reading_1', 'Lectura 1'), column('reading_2', 'Lectura 2'), column('reading_3', 'Lectura 3'), column('reading_4', 'Lectura 4'), column('reading_5', 'Lectura 5')], { fixed_rows: ['H2S', 'CO', 'O2', '%LEL'], hide_row_numbers: true }),
    section('after_adjustment', 'Después del ajuste', 4, [column('gas', 'Gas'), column('pattern_value', 'Patrón'), column('reading_1', 'Lectura 1'), column('reading_2', 'Lectura 2'), column('reading_3', 'Lectura 3'), column('reading_4', 'Lectura 4'), column('reading_5', 'Lectura 5')], { fixed_rows: ['H2S', 'CO', 'O2', '%LEL'], hide_row_numbers: true }),
  ])),
  template('dimensional', 'Dimensional', 'replicated_comparison', commonBlocks('ReplicatedComparisonTableBlock', [section('measurements', 'Indicador de carátula, micrómetro y medidor de espesores', 10, commonColumns.replicated3)])),
  template('electrica', 'Eléctrica', 'replicated_comparison', commonBlocks('SectionedTableBlock', Array.from({ length: 6 }, (_, index) => section(
    `electrical_${index + 1}`,
    `Bloque eléctrico ${index + 1}`,
    5,
    commonColumns.replicated3,
    { label_configurable: true, unit_field: `electrical_unit_${index + 1}`, break_before: index === 1 },
  ))), 2, { ambiguous_labels: true }),
  template('flujo', 'Flujo', 'replicated_comparison', commonBlocks('ReplicatedComparisonTableBlock', [section('measurements', 'Resultados de la calibración', 10, commonColumns.inverse3)])),
  template('general', 'General', 'replicated_comparison', commonBlocks('ReplicatedComparisonTableBlock', [section('measurements', 'Resultados de la calibración', 10, [column('reference', 'Patrón / IBC'), column('reading_1', 'Repetición 1'), column('reading_2', 'Repetición 2'), column('reading_3', 'Repetición 3')], { label_configurable: true, instruction: 'Marcar con X el rol aplicable.' })]), 1, { ambiguous_labels: true }),
  template('maestro_altura', 'Maestro de Altura', 'direction_cycle', commonBlocks('DirectionalCycleTableBlock', [
    section('ascending', 'Ascendente', 10, [column('equipment', 'Equipo patrón'), column('reading_1', 'Lectura 1'), column('reading_2', 'Lectura 2'), column('reading_3', 'Lectura 3')]),
    section('descending', 'Descendente', 10, [column('equipment', 'Equipo patrón'), column('reading_1', 'Lectura 1'), column('reading_2', 'Lectura 2'), column('reading_3', 'Lectura 3')]),
  ])),
  template('par_torsional', 'Par Torsional', 'direction_cycle', commonBlocks('DirectionalCycleTableBlock', [
    section('clockwise', 'Sentido horario (CW)', 5, [column('equipment', 'Equipo'), column('pattern_1', 'Patrón 1'), column('pattern_2', 'Patrón 2'), column('pattern_3', 'Patrón 3'), column('pattern_4', 'Patrón 4'), column('pattern_5', 'Patrón 5')]),
    section('counterclockwise', 'Sentido antihorario (CCW)', 5, [column('equipment', 'Equipo'), column('pattern_1', 'Patrón 1'), column('pattern_2', 'Patrón 2'), column('pattern_3', 'Patrón 3'), column('pattern_4', 'Patrón 4'), column('pattern_5', 'Patrón 5')]),
  ])),
  template('pesas', 'Pesas', 'replicated_comparison', commonBlocks('ReplicatedComparisonTableBlock', [section('measurements', 'Resultados de la calibración', 10, [column('identification', 'ID'), column('pattern_value', 'Patrón'), column('ibc_1', 'IBC 1'), column('ibc_2', 'IBC 2'), column('ibc_3', 'IBC 3'), column('ibc_4', 'IBC 4')])])),
  template('presion', 'Presión', 'direction_cycle', commonBlocks('DirectionalCycleTableBlock', [section('pressure_cycle', 'Ciclo de presión', 11, [column('ibc', 'IBC'), column('ascending_1', 'Patrón ascendente'), column('descending', 'Patrón descendente'), column('ascending_2', 'Patrón ascendente')], { label_configurable: true })]), 1, { ambiguous_labels: true }),
  template('reglas', 'Reglas', 'replicated_comparison', commonBlocks('ReplicatedComparisonTableBlock', [section('measurements', 'Resultados de la calibración', 15, [column('equipment', 'Equipo'), column('pattern_1', 'Patrón 1'), column('pattern_2', 'Patrón 2'), column('pattern_3', 'Patrón 3'), column('pattern_4', 'Patrón 4'), column('pattern_5', 'Patrón 5')], { hide_row_values: true, label_configurable: true })]), 1, { ambiguous_labels: true }),
  template('sonido', 'Sonido', 'replicated_comparison', commonBlocks('ReplicatedComparisonTableBlock', [section('measurements', 'Resultados de la calibración', 10, commonColumns.replicated3)])),
  template('tacometro', 'Tacómetro', 'replicated_comparison', commonBlocks('ReplicatedComparisonTableBlock', [section('measurements', 'Resultados de la calibración', 5, commonColumns.ordinal3)])),
  template('temperatura', 'Temperatura', 'replicated_comparison', commonBlocks('ReplicatedComparisonTableBlock', [section('measurements', 'Resultados de la calibración', 10, commonColumns.inverse3)])),
  template('tld_6_canales', 'TLD 6 Canales', 'paired_multichannel', commonBlocks('PairedChannelMatrixTableBlock', Array.from({ length: 6 }, (_, index) => section(
    `channel_${index + 1}`,
    `Canal ${index + 1}`,
    5,
    [column('measured_value', 'Valor medido'), column('pattern_1', 'Patrón 1'), column('ibc_1', 'IBC 1'), column('pattern_2', 'Patrón 2'), column('ibc_2', 'IBC 2'), column('pattern_3', 'Patrón 3'), column('ibc_3', 'IBC 3')],
    { column_groups: [{ label: 'Par 1', span: 2 }, { label: 'Par 2', span: 2 }, { label: 'Par 3', span: 2 }], break_before: index === 2 },
  )), { extra_equipment_fields: [{ key: 'instrument_type', label: 'Tipo', field_type: 'text', order: 9 }] }), 2),
  template('tld', 'TLD', 'paired_multichannel', commonBlocks('PairedChannelMatrixTableBlock', [section('channel_1', 'Datos de medición', 5, [column('measured_value', 'Valor medido'), column('pattern_1', 'Patrón 1'), column('ibc_1', 'IBC 1'), column('pattern_2', 'Patrón 2'), column('ibc_2', 'IBC 2'), column('pattern_3', 'Patrón 3'), column('ibc_3', 'IBC 3')], { column_groups: [{ label: 'Par 1', span: 2 }, { label: 'Par 2', span: 2 }, { label: 'Par 3', span: 2 }] })], { extra_equipment_fields: [{ key: 'instrument_type', label: 'Tipo', field_type: 'text', order: 9 }] })),
  template('valvula_seguridad', 'Válvula de Seguridad', 'threshold_event', commonBlocks('ThresholdEventTableBlock', [section('events', 'Presiones de operación', 2, [column('event', 'Evento'), column('reference', 'Referencia'), column('pattern_1', 'Patrón 1'), column('pattern_2', 'Patrón 2'), column('pattern_3', 'Patrón 3')], { fixed_rows: ['Disparo', 'Cierre'], hide_row_numbers: true })])),
  template('verificacion_equipos', 'Verificación de Equipos', 'verification_compliance', commonBlocks('VerificationComplianceTableBlock', [section('verification', 'Verificación funcional', 6, [column('measured_unit', 'Unidad medida'), column('ibc_1', 'IBC 1'), column('ibc_2', 'IBC 2'), column('ibc_3', 'IBC 3'), column('compliance', 'Cumple con funcionamiento', { data_type: 'boolean' })], { label_configurable: true })]), 1, { ambiguous_labels: true }),
  template('copa', 'Copa', 'cup_specialized', commonBlocks('CupSpecializedTableBlock', [
    section('cup_diameter', 'Diámetro de salida', 1, [column('diameter', 'Diámetro'), column('unit', 'Unidad')]),
    section('flow_times', 'Tiempos de flujo', 5, [column('time', 'Tiempo'), column('temperature', 'Temperatura')]),
    section('standard_details', 'Patrón / Standard', 1, [column('standard_id', 'Identificación'), column('kinematic_viscosity', 'Viscosidad cinemática a 25 °C'), column('cup_designation', 'Designación'), column('cup_size', 'Tamaño de copa')]),
    section('average_temperature', 'Temperatura promedio de calibración', 1, [column('average_temperature', 'Temperatura promedio'), column('unit', 'Unidad')]),
  ], {
    customer_title: 'Cliente',
    observations_title: 'Observaciones / Observations',
    extra_blocks: [block('ControlledDiagramBlock', 7, { title: 'Diagrama técnico de copa Ford', metadata: { asset_key: 'ford_viscosity_cup_v1' } })],
  }), 1, {
    signature_layout: signatureLayout([
      { role: 'calibrated_by', display_label: 'Calibró técnico' },
      { role: 'authorized_by', display_label: 'Autorizó' },
      { role: 'client_by', display_label: 'Cliente' },
      { role: 'report_made_by', display_label: 'Realizó informe' },
    ], 'two_by_two'),
  }),
];

export const officialFieldSheetTemplateKeys = templates.map((item) => item.key);
export const officialFieldSheetTemplates = Object.fromEntries(templates.map((item) => [item.key, item]));
export const officialFieldSheetTemplateOptions = templates.map((item) => ({ value: item.key, label: item.name }));
