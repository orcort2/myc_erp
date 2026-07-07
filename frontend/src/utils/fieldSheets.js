import { emptyFieldSheetForm } from '../constants/forms.js';
import { fieldSheetTemplates, templateNameByKey } from '../constants/fieldSheetTemplates.js';

function safeArray(value) {
  return Array.isArray(value) ? value : [];
}

function safeObject(value) {
  return value && typeof value === 'object' && !Array.isArray(value) ? value : {};
}

function uniqueStrings(values = []) {
  return safeArray(values)
    .map((value) => String(value ?? '').trim())
    .filter(Boolean)
    .filter((value, index, array) => array.indexOf(value) === index);
}

function normalizeColumn(column, index = 0) {
  const source = safeObject(column);
  const key = String(source.key ?? source.source ?? `column_${index + 1}`);
  return {
    key,
    label: String(source.label ?? key),
    source: String(source.source ?? key),
    width: source.width ?? null,
    unit: source.unit ?? source.suggested_unit ?? null,
    editable: source.editable !== false,
    required: Boolean(source.required),
    data_type: String(source.data_type ?? source.type ?? 'text'),
    suggested_unit: source.suggested_unit ?? source.unit ?? null,
    metadata: safeObject(source.metadata),
  };
}

function normalizeSection(section, fallback = {}, index = 0) {
  const source = safeObject(section);
  const fallbackSource = safeObject(fallback);
  const columns = safeArray(source.columns).length
    ? safeArray(source.columns).map(normalizeColumn)
    : safeArray(fallbackSource.columns).map(normalizeColumn);
  return {
    key: String(source.key ?? fallbackSource.key ?? `section_${index + 1}`),
    title: String(source.title ?? fallbackSource.title ?? `Sección ${index + 1}`),
    rows: Math.max(0, Number(source.rows ?? fallbackSource.rows ?? 0) || 0),
    columns,
    min_rows: Math.max(0, Number(source.min_rows ?? fallbackSource.min_rows ?? source.rows ?? fallbackSource.rows ?? 0) || 0),
    max_rows: Math.max(0, Number(source.max_rows ?? fallbackSource.max_rows ?? source.rows ?? fallbackSource.rows ?? 0) || 0),
    allow_add_rows: source.allow_add_rows ?? fallbackSource.allow_add_rows ?? false,
    allow_remove_rows: source.allow_remove_rows ?? fallbackSource.allow_remove_rows ?? false,
    metadata: safeObject(source.metadata ?? fallbackSource.metadata),
  };
}

function normalizeField(field, index = 0) {
  const source = safeObject(field);
  const key = String(source.key ?? `field_${index + 1}`);
  return {
    key,
    label: String(source.label ?? key),
    field_type: String(source.field_type ?? source.type ?? 'text'),
    required: Boolean(source.required),
    visible: source.visible !== false,
    order: Number(source.order ?? index + 1) || index + 1,
    placeholder: source.placeholder ?? null,
    help_text: source.help_text ?? source.help ?? null,
    options: safeArray(source.options).map((option) => String(option)),
    metadata: safeObject(source.metadata),
  };
}

function normalizeBlock(block, index = 0) {
  const source = safeObject(block);
  const blockType = String(source.block_type ?? source.blockType ?? 'CustomFieldsBlock');
  const blockKey = String(source.block_key ?? source.key ?? `${blockType}_${index + 1}`);
  const columns = safeArray(source.columns).map(normalizeColumn);
  const sections = safeArray(source.sections).map((section, sectionIndex) =>
    normalizeSection(section, { columns, rows: source.rows, min_rows: source.min_rows, max_rows: source.max_rows }, sectionIndex)
  );
  return {
    key: blockKey,
    block_key: blockKey,
    block_type: blockType,
    title: String(source.title ?? blockType),
    order: Number(source.order ?? source.capture_order ?? source.print_order ?? index + 1) || index + 1,
    visible: source.visible !== false,
    visible_fields: uniqueStrings(source.visible_fields),
    fields: safeArray(source.fields).map(normalizeField).sort((left, right) => left.order - right.order),
    columns,
    sections,
    table_config: safeObject(source.table_config),
    suggested_unit: source.suggested_unit ?? null,
    rows: source.rows === null || source.rows === undefined ? null : Math.max(0, Number(source.rows) || 0),
    min_rows: source.min_rows === null || source.min_rows === undefined ? null : Math.max(0, Number(source.min_rows) || 0),
    max_rows: source.max_rows === null || source.max_rows === undefined ? null : Math.max(0, Number(source.max_rows) || 0),
    allow_add_rows: Boolean(source.allow_add_rows),
    allow_remove_rows: Boolean(source.allow_remove_rows),
    required: Boolean(source.required),
    print_order: Number(source.print_order ?? source.order ?? index + 1) || index + 1,
    capture_order: Number(source.capture_order ?? source.order ?? index + 1) || index + 1,
    print_visible: source.print_visible !== false,
    capture_visible: source.capture_visible !== false,
    pdf_visible: source.pdf_visible !== false,
    metadata: safeObject(source.metadata),
  };
}

function isTableBlock(block) {
  const blockType = String(block?.block_type ?? '');
  return blockType.includes('TableBlock') || blockType === 'ResultsTableBlock';
}

function buildSectionsFromBlocks(blocks = []) {
  return safeArray(blocks)
    .filter(isTableBlock)
    .flatMap((block) => {
      if (safeArray(block.sections).length) {
        return block.sections.map((section, index) => normalizeSection(section, block, index));
      }
      return [
        normalizeSection(
          {
            key: block.key,
            title: block.title,
            rows: block.rows ?? 0,
            columns: block.columns ?? [],
            min_rows: block.min_rows,
            max_rows: block.max_rows,
            allow_add_rows: block.allow_add_rows,
            allow_remove_rows: block.allow_remove_rows,
          },
          block,
          0,
        ),
      ];
    });
}

function buildVisibleFields(blocks = []) {
  return uniqueStrings(
    safeArray(blocks).flatMap((block) => uniqueStrings(block.visible_fields))
  );
}

function buildFallbackTemplate(templateKey = 'general') {
  const fallback = fieldSheetTemplates[templateKey] ?? fieldSheetTemplates.general;
  return safeObject(fallback);
}

function unwrapTemplateSource(template) {
  const source = safeObject(template);
  return {
    root: source,
    definition:
      safeObject(source.definition).template_key || safeObject(source.definition).key || safeArray(source.definition?.blocks).length
        ? safeObject(source.definition)
        : safeObject(source.definition_json).template_key || safeObject(source.definition_json).key || safeArray(source.definition_json?.blocks).length
          ? safeObject(source.definition_json)
          : source,
  };
}

export function normalizeTemplate(template, templateKey = null, templatesByKey = null) {
  const source = safeObject(template);
  const fallbackKey = String(
    templateKey
    ?? source.template_key
    ?? source.key
    ?? safeObject(source.definition).template_key
    ?? safeObject(source.definition_json).template_key
    ?? 'general'
  );
  const fallback = buildFallbackTemplate(fallbackKey);
  const mappedSource = templatesByKey?.[fallbackKey];
  const normalizedMapped = mappedSource && mappedSource !== template
    ? normalizeTemplate(mappedSource, fallbackKey, null)
    : null;
  const { root, definition } = unwrapTemplateSource(source);
  const base = normalizedMapped || normalizeTemplateInternal(fallback, fallbackKey, null, true);

  const rawBlocks =
    safeArray(root.blocks).length ? root.blocks
      : safeArray(definition.blocks).length ? definition.blocks
        : safeArray(base.blocks);

  const blocks = rawBlocks.map(normalizeBlock).sort((left, right) => left.capture_order - right.capture_order || left.print_order - right.print_order);
  const rawSections =
    safeArray(root.result_sections).length ? root.result_sections
      : safeArray(root.resultSections).length ? root.resultSections
        : safeArray(definition.result_sections).length ? definition.result_sections
          : safeArray(definition.resultSections).length ? definition.resultSections
            : [];
  const resultSections = (rawSections.length ? rawSections : buildSectionsFromBlocks(blocks)).map((section, index) => normalizeSection(section, {}, index));

  return {
    ...(base || {}),
    ...safeObject(definition),
    ...root,
    key: String(root.key ?? root.template_key ?? definition.key ?? definition.template_key ?? base?.key ?? fallbackKey),
    template_key: String(root.template_key ?? root.key ?? definition.template_key ?? definition.key ?? base?.template_key ?? fallbackKey),
    name: String(root.name ?? definition.name ?? base?.name ?? templateNameByKey[fallbackKey] ?? 'Hoja de Campo'),
    description: root.description ?? definition.description ?? base?.description ?? '',
    type: String(root.type ?? definition.type ?? base?.type ?? fallbackKey),
    source: root.source ?? definition.source ?? base?.source ?? 'fallback',
    status: String(root.status ?? definition.status ?? base?.status ?? 'draft'),
    version: Number(root.version ?? definition.version ?? base?.version ?? 1) || 1,
    is_active: root.is_active ?? definition.is_active ?? base?.is_active ?? true,
    code: String(root.code ?? definition.code ?? base?.code ?? 'FCA-30'),
    revision: String(root.revision ?? definition.revision ?? base?.revision ?? 'R1'),
    document_code: String(root.document_code ?? definition.document_code ?? root.code ?? definition.code ?? base?.document_code ?? base?.code ?? 'FCA-30'),
    document_revision: String(root.document_revision ?? definition.document_revision ?? root.revision ?? definition.revision ?? base?.document_revision ?? base?.revision ?? 'R1'),
    pages: Math.max(1, Number(root.pages ?? definition.pages ?? base?.pages ?? 1) || 1),
    pdf_template: root.pdf_template ?? definition.pdf_template ?? base?.pdf_template ?? 'field_sheet_general_pdf.html',
    table_family: root.table_family ?? definition.table_family ?? base?.table_family ?? 'custom',
    blocks,
    result_sections: resultSections,
    resultSections,
    visible_fields: uniqueStrings(
      safeArray(root.visible_fields).length ? root.visible_fields
        : safeArray(definition.visible_fields).length ? definition.visible_fields
          : safeArray(base?.visible_fields).length ? base.visible_fields
            : buildVisibleFields(blocks)
    ),
    validations: safeObject(root.validations ?? definition.validations ?? base?.validations),
    print_config: safeObject(root.print_config ?? definition.print_config ?? base?.print_config),
    pdf_config: safeObject(root.pdf_config ?? definition.pdf_config ?? base?.pdf_config),
    permissions_config: safeObject(root.permissions_config ?? definition.permissions_config ?? base?.permissions_config),
    metadata: safeObject(root.metadata ?? definition.metadata ?? base?.metadata),
    definition,
    definition_json: definition,
  };
}

function normalizeTemplateInternal(template, templateKey = null, templatesByKey = null, bypassFallbackMap = false) {
  if (bypassFallbackMap) {
    const source = safeObject(template);
    const fallbackKey = String(templateKey ?? source.template_key ?? source.key ?? 'general');
    const { root, definition } = unwrapTemplateSource(source);
    const rawBlocks = safeArray(root.blocks).length ? root.blocks : safeArray(definition.blocks);
    const blocks = rawBlocks.map(normalizeBlock).sort((left, right) => left.capture_order - right.capture_order || left.print_order - right.print_order);
    const rawSections =
      safeArray(root.result_sections).length ? root.result_sections
        : safeArray(root.resultSections).length ? root.resultSections
          : safeArray(definition.result_sections).length ? definition.result_sections
            : safeArray(definition.resultSections).length ? definition.resultSections
              : [];
    const resultSections = (rawSections.length ? rawSections : buildSectionsFromBlocks(blocks)).map((section, index) => normalizeSection(section, {}, index));
    return {
      ...source,
      key: String(root.key ?? root.template_key ?? fallbackKey),
      template_key: String(root.template_key ?? root.key ?? fallbackKey),
      name: String(root.name ?? templateNameByKey[fallbackKey] ?? 'Hoja de Campo'),
      type: String(root.type ?? fallbackKey),
      source: root.source ?? 'fallback',
      status: String(root.status ?? 'active'),
      version: Number(root.version ?? 1) || 1,
      is_active: root.is_active ?? true,
      code: String(root.code ?? 'FCA-30'),
      revision: String(root.revision ?? 'R1'),
      document_code: String(root.document_code ?? root.code ?? 'FCA-30'),
      document_revision: String(root.document_revision ?? root.revision ?? 'R1'),
      pages: Math.max(1, Number(root.pages ?? 1) || 1),
      pdf_template: root.pdf_template ?? 'field_sheet_general_pdf.html',
      table_family: root.table_family ?? 'custom',
      blocks,
      result_sections: resultSections,
      resultSections,
      visible_fields: uniqueStrings(safeArray(root.visible_fields).length ? root.visible_fields : buildVisibleFields(blocks)),
      validations: safeObject(root.validations),
      print_config: safeObject(root.print_config),
      pdf_config: safeObject(root.pdf_config),
      permissions_config: safeObject(root.permissions_config),
      metadata: safeObject(root.metadata),
      definition: safeObject(definition),
      definition_json: safeObject(definition),
    };
  }
  return normalizeTemplate(template, templateKey, templatesByKey);
}

function getNormalizedTemplate(templateKey = 'general', templatesByKey = null) {
  const external = templatesByKey?.[templateKey];
  if (external) {
    return normalizeTemplate(external, templateKey, null);
  }
  return normalizeTemplate(fieldSheetTemplates[templateKey] ?? fieldSheetTemplates.general, templateKey, null);
}

function getNormalizedSections(template, templateKey = 'general', templatesByKey = null) {
  return normalizeTemplate(template, templateKey, templatesByKey).result_sections;
}

function getAllTemplateColumns(template, templateKey = 'general', templatesByKey = null) {
  return getNormalizedSections(template, templateKey, templatesByKey).flatMap((section) => safeArray(section.columns));
}

export function buildDefaultResultsRows(templateOrKey = 'general', templatesByKey = null) {
  const template = typeof templateOrKey === 'string'
    ? getNormalizedTemplate(templateOrKey, templatesByKey)
    : normalizeTemplate(templateOrKey, null, templatesByKey);

  return safeArray(template.result_sections).flatMap((section) =>
    Array.from({ length: Math.max(0, Number(section.rows) || 0) }, (_, index) => ({
      id: null,
      sectionKey: section.key,
      rowNumber: index + 1,
      ...Object.fromEntries(safeArray(section.columns).map((column) => [column.key, ''])),
    }))
  );
}

export function buildFieldSheetResultSections(rowsOrTemplateKey = [], maybeTemplateKey = 'general', maybeTemplatesByKey = null) {
  const usingLegacyOrder = Array.isArray(rowsOrTemplateKey);
  const rows = usingLegacyOrder ? rowsOrTemplateKey : [];
  const templateKey = usingLegacyOrder ? maybeTemplateKey : rowsOrTemplateKey;
  const templatesByKey = usingLegacyOrder ? maybeTemplatesByKey : maybeTemplateKey;
  const template = getNormalizedTemplate(templateKey, templatesByKey);
  const normalizedRows = normalizeResultsRows(rows, template, templatesByKey);

  return safeArray(template.result_sections).map((section) => ({
    ...section,
    columns: safeArray(section.columns),
    rows: normalizedRows.filter((row) => row.sectionKey === section.key),
  }));
}

export function normalizeResultsRows(rows = [], templateOrKey = 'general', templatesByKey = null) {
  const template = typeof templateOrKey === 'string'
    ? getNormalizedTemplate(templateOrKey, templatesByKey)
    : normalizeTemplate(templateOrKey, null, templatesByKey);
  const columns = getAllTemplateColumns(template, null, null);
  if (!safeArray(rows).length) {
    return buildDefaultResultsRows(template);
  }
  return safeArray(rows).map((row, index) => {
    const source = safeObject(row);
    return {
      id: source.id ?? null,
      sectionKey: source.section_key ?? source.sectionKey ?? template.result_sections?.[0]?.key ?? 'main',
      rowNumber: Number(source.row_number ?? source.rowNumber ?? index + 1) || index + 1,
      ...Object.fromEntries(
        columns.map((column) => [
          column.key,
          source[column.key]
            ?? safeObject(source.row_data)[column.key]
            ?? safeObject(source.row_data)[column.source]
            ?? source[column.source]
            ?? '',
        ])
      ),
    };
  });
}

export function getFieldSheetTemplate(templateKey = 'general', templatesByKey = null) {
  return getNormalizedTemplate(templateKey, templatesByKey);
}

export function getFieldSheetTemplateLabel(templateKey = 'general', templatesByKey = null) {
  return getNormalizedTemplate(templateKey, templatesByKey).name;
}

export function fieldSheetToForm(fieldSheet) {
  const normalizedTemplate = normalizeTemplate(
    fieldSheet?.template_definition ?? fieldSheet?.template_definition_json ?? { template_key: fieldSheet?.template_key ?? 'general' },
    fieldSheet?.template_key ?? 'general',
    fieldSheet?.template_definition ? { [fieldSheet.template_key]: fieldSheet.template_definition } : null,
  );

  return {
    ...emptyFieldSheetForm,
    templateKey: fieldSheet?.template_key ?? normalizedTemplate.template_key ?? 'general',
    calibrationProcedureId: fieldSheet?.calibration_procedure_id ? String(fieldSheet.calibration_procedure_id) : '',
    calibrationPlace: fieldSheet?.calibration_place ?? '',
    minimumDivision: fieldSheet?.minimum_division ?? '',
    location: fieldSheet?.location ?? '',
    attention: fieldSheet?.attention ?? '',
    company: fieldSheet?.company ?? '',
    address: fieldSheet?.address ?? '',
    receptionDate: fieldSheet?.reception_date ?? '',
    calibrationDate: fieldSheet?.calibration_date ?? '',
    nextCalibrationDate: fieldSheet?.next_calibration_date ?? '',
    environmentHumidityStart: fieldSheet?.environment_humidity_start ?? '',
    environmentHumidityEnd: fieldSheet?.environment_humidity_end ?? '',
    environmentTemperatureStart: fieldSheet?.environment_temperature_start ?? '',
    environmentTemperatureEnd: fieldSheet?.environment_temperature_end ?? '',
    equipmentGeneralCondition:
      fieldSheet?.equipment_general_condition === null || fieldSheet?.equipment_general_condition === undefined
        ? ''
        : fieldSheet.equipment_general_condition
          ? 'ok'
          : 'not_ok',
    considerEquipmentDeviations: Boolean(fieldSheet?.consider_equipment_deviations),
    units: fieldSheet?.units ?? '',
    calibratedBy: fieldSheet?.calibrated_by ?? '',
    reviewedBy: fieldSheet?.reviewed_by ?? '',
    reportMadeBy: fieldSheet?.report_made_by ?? '',
    purchaseOrderOrQuotation: fieldSheet?.purchase_order_or_quotation ?? '',
    initialCondition: fieldSheet?.initial_condition ?? '',
    finalCondition: fieldSheet?.final_condition ?? '',
    resultsSummary: fieldSheet?.results ?? '',
    patternUsed: fieldSheet?.pattern_used ?? '',
    observations: fieldSheet?.observations ?? '',
    evidenceNotes: fieldSheet?.evidence_notes ?? '',
    method: fieldSheet?.method ?? '',
    environmentalConditions: fieldSheet?.environmental_conditions ?? '',
    technicianNotes: fieldSheet?.technician_notes ?? '',
    reservedCertificateFolio: fieldSheet?.reserved_certificate_folio ?? '',
    certificateClientMode: fieldSheet?.certificate_client_mode ?? 'billing',
    certificateClientCompany: fieldSheet?.certificate_client_company ?? '',
    certificateClientAttention: fieldSheet?.certificate_client_attention ?? '',
    certificateClientAddress: fieldSheet?.certificate_client_address ?? '',
    applyCertificateClientToOrder: Boolean(fieldSheet?.apply_certificate_client_to_order),
    resultsRows: normalizeResultsRows(fieldSheet?.results_rows, normalizedTemplate),
    referenceStandards: safeArray(fieldSheet?.reference_standards).map((item) => ({
      referenceStandardId: String(item.reference_standard_id),
      usageRole: item.usage_role ?? 'primary',
      measurementSection: item.measurement_section ?? '',
      notes: item.notes ?? '',
      referenceStandard: item.reference_standard ?? null,
    })),
  };
}

export function buildFieldSheetPayload(form, templatesByKey = null) {
  const normalizedTemplate = getNormalizedTemplate(form.templateKey || 'general', templatesByKey);
  return {
    template_key: normalizedTemplate.template_key,
    calibration_procedure_id: form.calibrationProcedureId ? Number(form.calibrationProcedureId) : null,
    calibration_place: form.calibrationPlace.trim() || null,
    minimum_division: form.minimumDivision.trim() || null,
    location: form.location.trim() || null,
    attention: form.attention.trim() || null,
    company: form.company.trim() || null,
    address: form.address.trim() || null,
    reception_date: form.receptionDate || null,
    calibration_date: form.calibrationDate || null,
    next_calibration_date: form.nextCalibrationDate || null,
    environment_humidity_start: form.environmentHumidityStart.trim() || null,
    environment_humidity_end: form.environmentHumidityEnd.trim() || null,
    environment_temperature_start: form.environmentTemperatureStart.trim() || null,
    environment_temperature_end: form.environmentTemperatureEnd.trim() || null,
    equipment_general_condition: form.equipmentGeneralCondition === '' ? null : form.equipmentGeneralCondition === 'ok',
    consider_equipment_deviations: Boolean(form.considerEquipmentDeviations),
    units: form.units.trim() || null,
    calibrated_by: form.calibratedBy.trim() || null,
    reviewed_by: form.reviewedBy.trim() || null,
    report_made_by: form.reportMadeBy.trim() || null,
    purchase_order_or_quotation: form.purchaseOrderOrQuotation.trim() || null,
    initial_condition: form.initialCondition.trim() || null,
    final_condition: form.finalCondition.trim() || null,
    pattern_used: form.patternUsed.trim() || null,
    results: form.resultsSummary.trim() || null,
    observations: form.observations.trim() || null,
    evidence_notes: form.evidenceNotes.trim() || null,
    method: form.method.trim() || null,
    environmental_conditions: form.environmentalConditions.trim() || null,
    technician_notes: form.technicianNotes.trim() || null,
    certificate_client_mode: form.certificateClientMode || 'billing',
    certificate_client_company: form.certificateClientCompany.trim() || null,
    certificate_client_attention: form.certificateClientAttention.trim() || null,
    certificate_client_address: form.certificateClientAddress.trim() || null,
    apply_certificate_client_to_order: Boolean(form.applyCertificateClientToOrder),
    reference_standards: [],
    results_rows: normalizeResultsRows(form.resultsRows, normalizedTemplate).map((row) => ({
      id: row.id ?? undefined,
      section_key: row.sectionKey,
      row_number: row.rowNumber,
      pattern_value: String(row.pattern_value ?? '').trim() || null,
      ibc_value_1: String(row.ibc_value_1 ?? '').trim() || null,
      ibc_value_2: String(row.ibc_value_2 ?? '').trim() || null,
      ibc_value_3: String(row.ibc_value_3 ?? '').trim() || null,
      unit: String(row.unit ?? '').trim() || null,
      notes: String(row.notes ?? '').trim() || null,
      row_data: Object.fromEntries(
        Object.entries(row).filter(([key, value]) =>
          !['id', 'sectionKey', 'rowNumber'].includes(key) && String(value ?? '').trim() !== ''
        )
      ),
    })),
  };
}

export function updateFieldSheetResultsRowsForTemplate(form, templateKey, templatesByKey = null) {
  return {
    ...form,
    templateKey,
    resultsRows: buildDefaultResultsRows(templateKey, templatesByKey),
  };
}

export function updateFieldSheetResultCell(rows, sectionKey, rowNumber, field, value) {
  return safeArray(rows).map((row) =>
    row.sectionKey === sectionKey && Number(row.rowNumber) === Number(rowNumber)
      ? { ...row, [field]: value }
      : row
  );
}

export function hasStructuredFieldSheetResults(form, templatesByKey = null) {
  return normalizeResultsRows(form.resultsRows, form.templateKey, templatesByKey).some((row) =>
    Object.entries(row).some(([key, value]) =>
      !['id', 'sectionKey', 'rowNumber'].includes(key) && String(value ?? '').trim()
    )
  );
}

export function getFieldSheetCompletionErrors(form, templatesByKey = null) {
  const errors = [];
  if (!String(form.initialCondition ?? '').trim()) errors.push('Condicion inicial');
  if (!String(form.finalCondition ?? '').trim()) errors.push('Condicion final');
  if (!hasStructuredFieldSheetResults(form, templatesByKey)) errors.push('Resultados estructurados');
  if (!String(form.observations ?? '').trim() && !String(form.evidenceNotes ?? '').trim()) {
    errors.push('Observaciones o evidencia');
  }
  return errors;
}
