import React from 'react';

import mycLogo from '../../assets/myc-logo.png';

import './FieldSheetLayout.css';

function FieldInput({ value = '', onChange, type = 'text', className = '' }) {
  return (
    <input
      className={`field-sheet-input ${className}`}
      type={type}
      value={value}
      onChange={(event) => onChange?.(event.target.value)}
    />
  );
}

function FieldCheckbox({ checked = false, onChange }) {
  return (
    <input
      className="field-sheet-checkbox"
      type="checkbox"
      checked={checked}
      onChange={(event) => onChange?.(event.target.checked)}
    />
  );
}

export default function ({
  template,
  values,
  resultSections,
  onValueChange,
  onResultChange,
}) {
  const sheetTitle = template?.name || 'Hoja de Campo';
  const code = template?.code || 'FCA-30';
  const revision = template?.revision || 'R1';

  function value(key) {
    return values?.[key] ?? '';
  }

  function checked(key) {
    return Boolean(values?.[key]);
  }

  return (
    <section className="field-sheet-page">
      <header className="field-sheet-header">
        <div className="field-sheet-logo-box">
          <img src={mycLogo} alt="MYC" className="field-sheet-logo" />
        </div>

        <div className="field-sheet-company">
          <strong>METROLOGIA Y SERVICIOS MYC</strong>
          <span>
            Islas martinica # 2710, Col. Jardines de la Cruz, C.P. 44950
            Guadalajara, Jalisco
          </span>
          <span>Tel. 3350092659 smm@serviciosmetrologicosmundiales.com</span>
        </div>

        <div className="field-sheet-code">
          <strong>{code}</strong>
          <span>{revision}</span>
        </div>
      </header>

      <h1 className="field-sheet-title">{sheetTitle}</h1>

      <div className="field-sheet-top-row">
        <label>
          Orden de trabajo:
          <FieldInput
            value={value('work_order_number')}
            onChange={(nextValue) => onValueChange?.('work_order_number', nextValue)}
          />
        </label>

        <label>
          Certificado No.:
          <FieldInput
            value={value('certificate_number')}
            onChange={(nextValue) => onValueChange?.('certificate_number', nextValue)}
          />
        </label>
      </div>

      <div className="field-sheet-block-title">Datos del Usuario</div>

      <div className="field-sheet-user-grid">
        <label>
          Atencion:
          <FieldInput
            value={value('attention')}
            onChange={(nextValue) => onValueChange?.('attention', nextValue)}
          />
        </label>

        <label>
          Empresa:
          <FieldInput
            value={value('company')}
            onChange={(nextValue) => onValueChange?.('company', nextValue)}
          />
        </label>

        <label>
          Dirección:
          <FieldInput
            value={value('address')}
            onChange={(nextValue) => onValueChange?.('address', nextValue)}
          />
        </label>
      </div>

      <div className="field-sheet-block-title">Datos del Instrumento a Calibrar</div>

      <div className="field-sheet-instrument-grid">
        <label>
          Instrumento:
          <FieldInput
            value={value('instrument')}
            onChange={(nextValue) => onValueChange?.('instrument', nextValue)}
          />
        </label>

        <label>
          Alcance:
          <FieldInput
            value={value('scope')}
            onChange={(nextValue) => onValueChange?.('scope', nextValue)}
          />
        </label>

        <label>
          Div Minima:
          <FieldInput
            value={value('minimum_division')}
            onChange={(nextValue) => onValueChange?.('minimum_division', nextValue)}
          />
        </label>

        <label>
          Marca:
          <FieldInput
            value={value('brand')}
            onChange={(nextValue) => onValueChange?.('brand', nextValue)}
          />
        </label>

        <label>
          No. Serie:
          <FieldInput
            value={value('serial_number')}
            onChange={(nextValue) => onValueChange?.('serial_number', nextValue)}
          />
        </label>

        <label>
          Modelo:
          <FieldInput
            value={value('model')}
            onChange={(nextValue) => onValueChange?.('model', nextValue)}
          />
        </label>

        <label>
          Identificación:
          <FieldInput
            value={value('internal_id')}
            onChange={(nextValue) => onValueChange?.('internal_id', nextValue)}
          />
        </label>

        <label>
          Ubicación:
          <FieldInput
            value={value('location')}
            onChange={(nextValue) => onValueChange?.('location', nextValue)}
          />
        </label>

        <label>
          Lugar de calibración:
          <FieldInput
            value={value('calibration_place')}
            onChange={(nextValue) => onValueChange?.('calibration_place', nextValue)}
          />
        </label>
      </div>

      <div className="field-sheet-date-grid">
        <label>
          Fecha de recepción:
          <FieldInput
            type="date"
            value={value('reception_date')}
            onChange={(nextValue) => onValueChange?.('reception_date', nextValue)}
          />
        </label>

        <label>
          Fecha de calibración:
          <FieldInput
            type="date"
            value={value('calibration_date')}
            onChange={(nextValue) => onValueChange?.('calibration_date', nextValue)}
          />
        </label>

        <label>
          Proxima calibración:
          <FieldInput
            type="date"
            value={value('next_calibration_date')}
            onChange={(nextValue) =>
              onValueChange?.('next_calibration_date', nextValue)
            }
          />
        </label>
      </div>

      <div className="field-sheet-env-grid">
        <label>
          Humedad Relativa Inicio:
          <FieldInput
            value={value('humidity_start')}
            onChange={(nextValue) => onValueChange?.('humidity_start', nextValue)}
          />
          %
        </label>

        <label>
          Temperatura Inicio:
          <FieldInput
            value={value('temperature_start')}
            onChange={(nextValue) => onValueChange?.('temperature_start', nextValue)}
          />
          °C
        </label>

        <label>
          Humedad Relativa Final:
          <FieldInput
            value={value('humidity_end')}
            onChange={(nextValue) => onValueChange?.('humidity_end', nextValue)}
          />
          %
        </label>

        <label>
          Temperatura Final:
          <FieldInput
            value={value('temperature_end')}
            onChange={(nextValue) => onValueChange?.('temperature_end', nextValue)}
          />
          °C
        </label>
      </div>

      <div className="field-sheet-check-row">
        <label>
          <FieldCheckbox
            checked={checked('equipment_good_condition')}
            onChange={(nextValue) =>
              onValueChange?.('equipment_good_condition', nextValue)
            }
          />
          Equipo en buen estado general
        </label>

        <label>
          <FieldCheckbox
            checked={checked('consider_deviations')}
            onChange={(nextValue) => onValueChange?.('consider_deviations', nextValue)}
          />
          Considerar desviaciones del equipo
        </label>

        <label>
          Otros:
          <FieldInput
            value={value('others')}
            onChange={(nextValue) => onValueChange?.('others', nextValue)}
          />
        </label>
      </div>

      <div className="field-sheet-units-row">
        <label>
          Unidades:
          <FieldInput
            value={value('units')}
            onChange={(nextValue) => onValueChange?.('units', nextValue)}
          />
        </label>
      </div>

      <div className="field-sheet-results-title">Resultados de la Calibración</div>

      {resultSections?.map((section) => (
        <table className="field-sheet-results-table" key={section.key}>
          <thead>
            <tr>
              <th>No.</th>
              {section.columns.map((column) => (
                <th key={column.key}>{column.label}</th>
              ))}
            </tr>
          </thead>

          <tbody>
            {section.rows.map((row, rowIndex) => (
              <tr key={`${section.key}-${rowIndex}`}>
                <td>{rowIndex + 1}</td>

                {section.columns.map((column) => (
                  <td key={column.key}>
                    <FieldInput
                      value={row[column.key] ?? ''}
                      onChange={(nextValue) =>
                        onResultChange?.(
                          section.key,
                          rowIndex,
                          column.key,
                          nextValue,
                        )
                      }
                    />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      ))}

      <label className="field-sheet-observations">
        OBSERVACIONES:
        <textarea
          value={value('observations')}
          onChange={(event) => onValueChange?.('observations', event.target.value)}
        />
      </label>

      <footer className="field-sheet-footer">
        <label>
          CALIBRÓ
          <FieldInput
            value={value('calibrated_by')}
            onChange={(nextValue) => onValueChange?.('calibrated_by', nextValue)}
          />
        </label>

        <label>
          REVISÓ
          <FieldInput
            value={value('reviewed_by')}
            onChange={(nextValue) => onValueChange?.('reviewed_by', nextValue)}
          />
        </label>

        <label>
          REALIZÓ INFORME (SMM)
          <FieldInput
            value={value('report_made_by')}
            onChange={(nextValue) => onValueChange?.('report_made_by', nextValue)}
          />
        </label>

        <label>
          ORDEN DE COMPRA/COTIZACIÓN
          <FieldInput
            value={value('purchase_order_or_quotation')}
            onChange={(nextValue) =>
              onValueChange?.('purchase_order_or_quotation', nextValue)
            }
          />
        </label>
      </footer>
    </section>
  );
}