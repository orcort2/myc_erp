import React from 'react';

import mycLogo from '../../assets/myc-logo.png';
import { fieldSheetFieldCatalog } from '../../constants/fieldSheetTemplates.js';
import { normalizeTemplate } from '../../utils/fieldSheets.js';

import './FieldSheetLayout.css';

function FieldInput({ value = '', onChange, type = 'text', className = '', placeholder = '' }) {
  if (type === 'textarea') {
    return (
      <textarea
        className={`field-sheet-textarea ${className}`}
        value={value}
        onChange={(event) => onChange?.(event.target.value)}
        placeholder={placeholder}
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
    />
  );
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
  const explicitFields = Array.isArray(block.fields) && block.fields.length
    ? block.fields
    : (block.visible_fields || []).map((key, index) => ({
        key,
        label: fieldSheetFieldCatalog[key]?.label || key,
        field_type: fieldSheetFieldCatalog[key]?.field_type || 'text',
        required: false,
        visible: true,
        order: index + 1,
      }));
  return explicitFields
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

export default function FieldSheetLayout({ template, values, resultSections, onValueChange, onResultChange }) {
  const normalizedTemplate = normalizeTemplate(template);
  const sheetTitle = normalizedTemplate.name || 'Hoja de Campo';
  const code = normalizedTemplate.document_code || normalizedTemplate.code || 'FCA-30';
  const revision = normalizedTemplate.document_revision || normalizedTemplate.revision || 'R1';
  const blocks = [...(Array.isArray(normalizedTemplate.blocks) ? normalizedTemplate.blocks : [])].sort((left, right) => (left.capture_order || 0) - (right.capture_order || 0));

  function value(key) {
    return values?.[mapFormKey(key)] ?? values?.[key] ?? '';
  }

  function renderField(field) {
    const fieldType = field.field_type || 'text';
    const inputType = fieldType === 'date' ? 'date' : fieldType === 'textarea' ? 'textarea' : 'text';
    return (
      <label key={field.key}>
        {field.label}
        <FieldInput
          type={inputType}
          value={value(field.key)}
          placeholder={field.placeholder || ''}
          onChange={(nextValue) => onValueChange?.(field.key, nextValue)}
        />
      </label>
    );
  }

  return (
    <section className="field-sheet-page">
      <header className="field-sheet-header">
        <div className="field-sheet-logo-box">
          <img src={mycLogo} alt="MYC" className="field-sheet-logo" />
        </div>
        <div className="field-sheet-company">
          <strong>METROLOGIA Y SERVICIOS MYC</strong>
          <span>Islas martinica # 2710, Col. Jardines de la Cruz, C.P. 44950 Guadalajara, Jalisco</span>
          <span>Tel. 3350092659 smm@serviciosmetrologicosmundiales.com</span>
        </div>
        <div className="field-sheet-code">
          <strong>{code}</strong>
          <span>{revision}</span>
        </div>
      </header>

      <h1 className="field-sheet-title">{sheetTitle}</h1>

      {blocks.map((block) => {
        if (block.capture_visible === false || block.visible === false) {
          return null;
        }
        const blockFields = buildFieldDescriptors(block);
        const blockSections = rowsForBlock(block, resultSections || []);
        const isTableBlock = String(block.block_type || '').includes('TableBlock') || block.block_type === 'ResultsTableBlock';

        if (isTableBlock) {
          return (
            <section key={block.key}>
              {blockSections.map((section) => (
                <React.Fragment key={section.key}>
                  <div className="field-sheet-results-title">{section.title || block.title}</div>
                  <table className="field-sheet-results-table">
                    <thead>
                      <tr>
                        <th>No.</th>
                        {(section.columns || []).map((column) => (
                          <th key={column.key}>{column.label}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {(section.rows || []).map((row, rowIndex) => (
                        <tr key={`${section.key}-${rowIndex}`}>
                          <td>{row.rowNumber ?? rowIndex + 1}</td>
                          {(section.columns || []).map((column) => (
                            <td key={column.key}>
                              <FieldInput
                                value={row[column.key] ?? ''}
                                onChange={(nextValue) => onResultChange?.(section.key, row.rowNumber ?? rowIndex + 1, column.key, nextValue)}
                              />
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </React.Fragment>
              ))}
            </section>
          );
        }

        if (block.block_type === 'SignaturesBlock') {
          return (
            <footer className="field-sheet-footer" key={block.key}>
              {blockFields.map(renderField)}
            </footer>
          );
        }

        return (
          <section key={block.key}>
            <div className="field-sheet-block-title">{block.title}</div>
            <div className="field-sheet-user-grid field-sheet-dynamic-grid">
              {blockFields.length ? blockFields.map(renderField) : <span className="field-sheet-empty-block">Bloque sin campos visibles</span>}
            </div>
          </section>
        );
      })}
    </section>
  );
}
