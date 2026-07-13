import React, { useEffect, useMemo, useRef, useState } from 'react';

import mycLogo from '../../assets/myc-logo.png';
import { fieldSheetFieldCatalog } from '../../constants/fieldSheetTemplates.js';
import { normalizeTemplate } from '../../utils/fieldSheets.js';
import { getInstitutionalConfiguration } from '../../services/api.js';
import { paginateFieldSheet } from './fieldSheetPagination.js';

import './FieldSheetLayout.css';

function FieldInput({ value = '', onChange, type = 'text', className = '', placeholder = '', ...inputProps }) {
  if (type === 'textarea') {
    return (
      <textarea
        className={`field-sheet-textarea ${className}`}
        value={value}
        onChange={(event) => onChange?.(event.target.value)}
        placeholder={placeholder}
        {...inputProps}
      />
    );
  }

  return (
    <input
      className={`field-sheet-input ${className}`}
      type={type}
      value={value}
      onChange={(event) => onChange?.(event.target.value)}
      placeholder={placeholder}
      {...inputProps}
    />
  );
}

function SignatureCanvas({ label, value, onChange }) {
  const canvasRef = useRef(null);
  const drawingRef = useRef(false);

  useEffect(() => {
    const canvas = canvasRef.current;
    const context = canvas?.getContext('2d');
    if (!canvas || !context) return;
    context.clearRect(0, 0, canvas.width, canvas.height);
    if (!value) return;
    const image = new Image();
    image.onload = () => context.drawImage(image, 0, 0, canvas.width, canvas.height);
    image.src = value;
  }, [value]);

  function point(event) {
    const canvas = canvasRef.current;
    const bounds = canvas.getBoundingClientRect();
    return {
      x: (event.clientX - bounds.left) * (canvas.width / bounds.width),
      y: (event.clientY - bounds.top) * (canvas.height / bounds.height),
    };
  }

  function begin(event) {
    const context = canvasRef.current.getContext('2d');
    const start = point(event);
    drawingRef.current = true;
    event.currentTarget.setPointerCapture?.(event.pointerId);
    context.strokeStyle = '#0f172a';
    context.lineWidth = 2;
    context.lineCap = 'round';
    context.lineJoin = 'round';
    context.beginPath();
    context.moveTo(start.x, start.y);
  }

  function draw(event) {
    if (!drawingRef.current) return;
    const next = point(event);
    const context = canvasRef.current.getContext('2d');
    context.lineTo(next.x, next.y);
    context.stroke();
  }

  function end() {
    if (!drawingRef.current) return;
    drawingRef.current = false;
    onChange?.(canvasRef.current.toDataURL('image/png'));
  }

  function clear() {
    const canvas = canvasRef.current;
    canvas.getContext('2d').clearRect(0, 0, canvas.width, canvas.height);
    onChange?.('');
  }

  return (
    <div className="field-sheet-signature-capture">
      <canvas aria-label={`Firma ${label}`} height="70" onPointerDown={begin} onPointerMove={draw} onPointerUp={end} onPointerCancel={end} ref={canvasRef} width="320" />
      <button onClick={clear} type="button">Limpiar firma</button>
    </div>
  );
}

function navigateTableInput(event) {
  if (!['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', 'Enter'].includes(event.key)) return;

  const cell = event.currentTarget.closest('td');
  const row = cell?.parentElement;
  const body = row?.parentElement;
  if (!cell || !row || !body) return;

  const rows = Array.from(body.querySelectorAll(':scope > tr'));
  const cells = Array.from(row.children);
  const rowIndex = rows.indexOf(row);
  const cellIndex = cells.indexOf(cell);

  let targetRow = rowIndex;
  let targetCell = cellIndex;

  if (event.key === 'ArrowLeft') targetCell -= 1;
  if (event.key === 'ArrowRight') targetCell += 1;
  if (event.key === 'ArrowUp') targetRow -= 1;
  if (event.key === 'ArrowDown' || event.key === 'Enter') targetRow += 1;

  const target = rows[targetRow]?.children[targetCell]?.querySelector('input, textarea, select');
  if (!target) return;

  event.preventDefault();
  target.focus();
  target.select?.();
}

function mapFormKey(fieldKey) {
  const aliases = {
    calibrated_by: 'calibrated_by',
    reviewed_by: 'reviewed_by',
    report_made_by: 'report_made_by',
  };

  return aliases[fieldKey] || fieldKey;
}

function buildFieldDescriptors(block) {
  const catalogFields = (block.visible_fields || []).map((key, index) => ({
        key,
        label: fieldSheetFieldCatalog[key]?.label || key,
        field_type: fieldSheetFieldCatalog[key]?.field_type || 'text',
        required: false,
        visible: true,
        order: index + 1,
      }));
  const explicitFields = Array.isArray(block.fields) ? block.fields : [];
  const fieldsByKey = new Map(catalogFields.map((field) => [field.key, field]));
  explicitFields.forEach((field) => fieldsByKey.set(field.key, { ...fieldsByKey.get(field.key), ...field }));

  return [...fieldsByKey.values()]
    .filter((field) => field.visible !== false)
    .sort((left, right) => (left.order || 0) - (right.order || 0));
}

function rowsForBlock(block, resultSections) {
  const safeResultSections = Array.isArray(resultSections) ? resultSections : [];

  if (Array.isArray(block?.sections) && block.sections.length) {
    return block.sections.map((section) => ({
      ...section,
      rows: safeResultSections.find((item) => item?.key === section.key)?.rows ?? [],
    }));
  }

  const section = safeResultSections.find((item) => item?.key === block?.key);
  return section ? [{ ...section, rows: section.rows ?? [] }] : [];
}

function normalizeBlockType(blockType = '') {
  return String(blockType).toLowerCase();
}

function isBlock(block, ...types) {
  const normalized = normalizeBlockType(block?.block_type);
  return types.some((type) => normalized.includes(type.toLowerCase()));
}

const DEFAULT_INSTITUTION = {
  legal_name: '',
  document_code: '',
  initial_revision: '',
  address: '',
  phone: '',
  email: '',
  logo_path: '',
};

export default function FieldSheetLayout({
  template,
  values,
  resultSections,
  institution: institutionProp,
  signatures = [],
  users = [],
  onValueChange,
  onResultChange,
  onSignatureChange,
  validationErrors = {},
}) {
  const normalizedTemplate = normalizeTemplate(template);
  const [institutionState, setInstitutionState] = useState(institutionProp || null);

  useEffect(() => {
    if (institutionProp) {
      setInstitutionState(institutionProp);
      return;
    }

    let active = true;

    getInstitutionalConfiguration()
      .then((configuration) => {
        if (active) setInstitutionState(configuration);
      })
      .catch(() => {
        if (active) setInstitutionState(null);
      });

    return () => {
      active = false;
    };
  }, [institutionProp]);

  const institution = { ...DEFAULT_INSTITUTION, ...(institutionState || {}) };
  const logoSource = institution.logo_path
    ? (/^(data:|https?:|\/)/.test(institution.logo_path) ? institution.logo_path : mycLogo)
    : mycLogo;

  const sheetTitle = normalizedTemplate.name || 'Hoja de Campo';
  const sheetSubtitle = normalizedTemplate.subtitle || normalizedTemplate.document_subtitle || '';
  const code = institution.document_code;
  const revision = institution.initial_revision;

  const blocks = [...(Array.isArray(normalizedTemplate.blocks) ? normalizedTemplate.blocks : [])]
    .sort((left, right) => (left.capture_order || 0) - (right.capture_order || 0));

  function value(key) {
    return values?.[mapFormKey(key)] ?? values?.[key] ?? '';
  }

  const signatureSlots = useMemo(() => {
    if (signatures.length) return signatures;

    const slots = normalizedTemplate.signature_layout?.slots || [];
    return slots.map((slot, index) => ({
      role: slot.role,
      displayLabel: slot.display_label || slot.role,
      name: value(slot.role),
      signatureData: '',
      signedAt: '',
      userId: '',
      position: index,
    }));
  }, [signatures, normalizedTemplate.signature_layout, values]);

  function renderField(field, className = '') {
    const fieldType = field.field_type || 'text';
    const inputType = fieldType === 'date'
      ? 'date'
      : fieldType === 'textarea'
        ? 'textarea'
        : fieldType === 'boolean'
          ? 'checkbox'
          : 'text';

    if (inputType === 'checkbox') {
      const error = validationErrors[field.key];
      return (
        <label className={`field-sheet-check-field ${className} ${error ? 'has-validation-error' : ''}`} data-field-key={field.key} data-validation-error={error ? 'true' : undefined} key={field.key}>
          <span>{field.label}</span>
          <input
            className="field-sheet-checkbox"
            type="checkbox"
            checked={Boolean(value(field.key))}
            onChange={(event) => onValueChange?.(field.key, event.target.checked)}
          />
          {error ? <small className="field-sheet-validation-message">{error}</small> : null}
        </label>
      );
    }

    const error = validationErrors[field.key];
    return (
      <label className={`field-sheet-line-field ${className} ${error ? 'has-validation-error' : ''}`} data-field-key={field.key} data-validation-error={error ? 'true' : undefined} key={field.key}>
        <span>{field.label}</span>
        <FieldInput
          type={inputType}
          value={value(field.key)}
          placeholder={field.placeholder || ''}
          aria-invalid={error ? 'true' : undefined}
          onChange={(nextValue) => onValueChange?.(field.key, nextValue)}
        />
        {error ? <small className="field-sheet-validation-message">{error}</small> : null}
      </label>
    );
  }

  function renderGenericBlock(block, blockFields) {
    const type = normalizeBlockType(block.block_type);

    if (type.includes('headerblock')) return null;

    if (type.includes('clientblock') || type.includes('generaldatablock')) {
      return (
        <section className="field-sheet-common-section field-sheet-customer-section" key={block.key}>
          <h2 className="field-sheet-section-heading">{block.title || 'Datos del Usuario'}</h2>
          <div className="field-sheet-customer-grid">
            {blockFields.map((field) => renderField(field, 'field-sheet-customer-field'))}
          </div>
        </section>
      );
    }

    if (type.includes('equipmentblock') || type.includes('equipmentdatablock')) {
      return (
        <section className="field-sheet-common-section field-sheet-instrument-section" key={block.key}>
          <h2 className="field-sheet-section-heading field-sheet-section-heading--blue">
            {block.title || 'Datos del Instrumento a Calibrar'}
          </h2>
          <div className="field-sheet-instrument-grid">
            {blockFields.map((field) => renderField(field))}
          </div>
        </section>
      );
    }

    if (type.includes('calibrationdatablock')) {
      return (
        <section className="field-sheet-common-section field-sheet-calibration-section" key={block.key}>
          <div className="field-sheet-calibration-grid">
            {blockFields.map((field) => renderField(field))}
          </div>
        </section>
      );
    }

    if (type.includes('environmentalblock')) {
      return (
        <section className="field-sheet-common-section field-sheet-environment-section" key={block.key}>
          <div className="field-sheet-environment-grid">
            {blockFields.map((field) => renderField(field))}
          </div>
        </section>
      );
    }

    if (type.includes('observationsblock')) {
      return (
        <section className="field-sheet-common-section field-sheet-observation-section" key={block.key}>
          <div className="field-sheet-condition-column">
            {blockFields
              .filter((field) => field.field_type === 'boolean')
              .map((field) => renderField(field))}
          </div>

          <div className="field-sheet-observation-column">
            <strong className="field-sheet-observation-title">{block.title || 'OBSERVACIONES:'}</strong>
            {blockFields
              .filter((field) => field.field_type !== 'boolean' && field.field_type !== 'textarea')
              .map((field) => renderField(field))}
            {blockFields
              .filter((field) => field.field_type === 'textarea')
              .map((field) => (
                <label className={`field-sheet-observation-box ${validationErrors[field.key] ? 'has-validation-error' : ''}`} data-field-key={field.key} data-validation-error={validationErrors[field.key] ? 'true' : undefined} key={field.key}>
                  <span>{field.label || 'Otros:'}</span>
                  <FieldInput
                    type="textarea"
                    value={value(field.key)}
                    aria-invalid={validationErrors[field.key] ? 'true' : undefined}
                    onChange={(nextValue) => onValueChange?.(field.key, nextValue)}
                  />
                  {validationErrors[field.key] ? <small className="field-sheet-validation-message">{validationErrors[field.key]}</small> : null}
                </label>
              ))}
          </div>
        </section>
      );
    }

    if (type.includes('controlleddiagramblock')) {
      return (
        <section className="field-sheet-cup-diagram" key={block.key} aria-label={block.title}>
          <div>
            <strong>{block.title}</strong>
            <small>Activo controlado: {block.metadata?.asset_key || 'diagrama técnico'}</small>
          </div>
          <svg aria-label="Diagrama técnico de copa Ford" role="img" viewBox="0 0 260 118">
            <path d="M78 14h104l-13 72H91z" fill="none" stroke="currentColor" strokeWidth="2" />
            <path d="M118 86h24l-5 20h-14z" fill="none" stroke="currentColor" strokeWidth="2" />
            <path d="M130 4v108M56 14h18M56 86h30M48 18v64M45 18l3-6 3 6M45 82l3 6 3-6" fill="none" stroke="currentColor" strokeWidth="1" />
            <text x="8" y="53" fontSize="10">Altura</text>
            <text x="188" y="52" fontSize="10">Copa Ford</text>
            <text x="181" y="68" fontSize="9">orificio calibrado</text>
          </svg>
        </section>
      );
    }

    return (
      <section className="field-sheet-common-section" key={block.key}>
        {block.title ? <h2 className="field-sheet-section-heading">{block.title}</h2> : null}
        <div className="field-sheet-dynamic-grid">
          {blockFields.length
            ? blockFields.map((field) => renderField(field))
            : <span className="field-sheet-empty-block">Bloque sin campos visibles</span>}
        </div>
      </section>
    );
  }

  function renderSignatures(block) {
    return (
      <section className={`field-sheet-signatures field-sheet-signatures--${normalizedTemplate.signature_layout?.layout || 'three_columns'}`} key={block.key}>
        {signatureSlots.map((signature, index) => (
          <div className="field-sheet-signature-slot" data-signature-role={signature.role} key={signature.role}>
            <div className="field-sheet-signature-line">
              <SignatureCanvas label={signature.displayLabel || signature.display_label || signature.role} value={signature.signatureData || signature.signature_data || ''} onChange={(signatureData) => onSignatureChange?.(index, { signatureData })} />
            </div>
            <strong>{signature.displayLabel || signature.display_label || signature.role}</strong>
            <div className="field-sheet-signature-meta">
              <FieldInput value={signature.name || ''} placeholder="Nombre" onChange={(nextValue) => onSignatureChange?.(index, { name: nextValue })} />
              <select className="field-sheet-input" value={signature.userId || signature.user_id || ''} onChange={(event) => onSignatureChange?.(index, { userId: event.target.value })}>
                <option value="">Sin asociar</option>
                {users.map((user) => <option key={user.id} value={user.id}>{user.full_name || user.email}</option>)}
              </select>
              <FieldInput type="date" value={(signature.signedAt || signature.signed_at || '').slice(0, 10)} onChange={(nextValue) => onSignatureChange?.(index, { signedAt: nextValue || '' })} />
            </div>
          </div>
        ))}
      </section>
    );
  }

  function renderTable(unit) {
    const { section, continuation } = unit;
    const grouped = section.metadata?.column_groups || [];
    const hideRowNumbers = section.metadata?.hide_row_numbers;
    const hideRowValues = section.metadata?.hide_row_values;
    return (
      <section className={`field-sheet-results-section field-sheet-results-section--${section.key} ${validationErrors.results_rows ? 'has-validation-error' : ''}`} data-section-key={section.key} data-validation-error={validationErrors.results_rows ? 'true' : undefined} key={`${section.key}-${section.rows?.[0]?.rowNumber || 0}`}>
        <div className="field-sheet-table-group">
          <div className="field-sheet-table-section-title">
            {section.title || unit.block.title}{continuation ? ' - continuación' : ''}
            {section.metadata?.unit_field ? <FieldInput aria-label={`Unidades ${section.title}`} value={value(section.metadata.unit_field)} placeholder="Unidades" onChange={(nextValue) => onValueChange?.(section.metadata.unit_field, nextValue)} /> : null}
          </div>
          {section.metadata?.instruction ? <div className="field-sheet-table-note">{section.metadata.instruction}</div> : null}
          <table className="field-sheet-results-table">
            <thead>
              {grouped.length ? (
                <tr className="field-sheet-grouped-header">
                  <th rowSpan="2">No.</th>
                  <th rowSpan="2">{section.columns?.[0]?.label}</th>
                  {grouped.map((group) => <th colSpan={group.span} key={group.label}>{group.label}</th>)}
                </tr>
              ) : null}
              <tr>
                {!grouped.length ? <th>{hideRowNumbers ? '' : 'No.'}</th> : null}
                {(section.columns || []).slice(grouped.length ? 1 : 0).map((column) => <th key={column.key}>{column.label}</th>)}
              </tr>
            </thead>
            <tbody>
              {(section.rows || []).map((row, rowIndex) => (
                <tr key={`${section.key}-${row.rowNumber ?? rowIndex + 1}`}>
                  <td>{hideRowNumbers || hideRowValues ? '' : row.rowNumber ?? rowIndex + 1}</td>
                  {(section.columns || []).map((column) => (
                    <td key={column.key}>
                      {column.data_type === 'boolean' ? (
                        <input className="field-sheet-table-checkbox" type="checkbox" aria-label={`${section.title}, fila ${row.rowNumber ?? rowIndex + 1}, ${column.label}`} checked={Boolean(row[column.key])} onChange={(event) => onResultChange?.(section.key, row.rowNumber ?? rowIndex + 1, column.key, event.target.checked)} />
                      ) : (
                        <FieldInput aria-label={`${section.title}, fila ${row.rowNumber ?? rowIndex + 1}, ${column.label}`} data-grid-input="true" onKeyDown={navigateTableInput} value={row[column.key] ?? ''} onChange={(nextValue) => onResultChange?.(section.key, row.rowNumber ?? rowIndex + 1, column.key, nextValue)} />
                      )}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
          {section.metadata?.note ? <div className="field-sheet-table-note">{section.metadata.note}</div> : null}
          {validationErrors.results_rows ? <div className="field-sheet-validation-message">{validationErrors.results_rows}</div> : null}
        </div>
      </section>
    );
  }

  const pages = paginateFieldSheet(blocks, resultSections || []);
  // `reserved_certificate_folio` is the canonical operational key. Keep the
  // former renderer alias so historical snapshots still display their folio.
  const reservedCertificateFolio =
    value('reserved_certificate_folio') || value('certificate_number');

  return (
    <div className="field-sheet-document" data-page-count={pages.length} data-template-key={normalizedTemplate.template_key}>
      {pages.map((page) => (
        <section className="field-sheet-page" data-page-number={page.pageNumber} key={page.pageNumber}>
          <header className="field-sheet-document-header">
            {page.pageNumber === 1 ? (
              <>
                <div className="field-sheet-logo-box">{logoSource ? <img src={logoSource} alt="MYC" className="field-sheet-logo" /> : null}</div>
                <div className="field-sheet-company">
                  <strong>{institution.legal_name}</strong>
                  {institution.address ? <span>{institution.address}</span> : null}
                  {institution.phone || institution.email ? <span>{[institution.phone, institution.email].filter(Boolean).join('   ')}</span> : null}
                </div>
                <div className="field-sheet-document-meta"><strong>{code}</strong><span>{revision}</span></div>
                <div className="field-sheet-heading-band">
                  <h1 className="field-sheet-title">{sheetTitle}</h1>
                  {sheetSubtitle ? <div className="field-sheet-subtitle">{sheetSubtitle}</div> : null}
                </div>
              </>
            ) : (
              <div className="field-sheet-continuation-header">
                <strong>{institution.legal_name}</strong>
                <h1 className="field-sheet-title">{sheetTitle}</h1>
                <span>{code} · {revision} · Continuación</span>
              </div>
            )}
          </header>

          <div className="field-sheet-reference-row">
            <label className="field-sheet-line-field"><span>Orden de trabajo:</span><FieldInput value={value('work_order_number')} readOnly aria-readonly="true" title="Orden de trabajo asociada por el ERP" /></label>
            <label className="field-sheet-line-field"><span>Certificado No.:</span><FieldInput value={reservedCertificateFolio} readOnly aria-readonly="true" title="Folio reservado automáticamente para el certificado" /></label>
          </div>

          <div className="field-sheet-page-content">
            {page.units.map((unit) => {
              if (unit.kind === 'table') return renderTable(unit);
              if (unit.block.block_type === 'SignaturesBlock') return renderSignatures(unit.block);
              return renderGenericBlock(unit.block, buildFieldDescriptors(unit.block));
            })}
          </div>

          <footer className="field-sheet-document-footer">
            <label><span>Orden de compra / cotización</span><FieldInput value={value('purchase_order_or_quotation')} onChange={(nextValue) => onValueChange?.('purchase_order_or_quotation', nextValue)} /></label>
            <span>{code} · {revision}</span>
            <span>Página {page.pageNumber} de {pages.length}</span>
          </footer>
        </section>
      ))}
    </div>
  );
}
