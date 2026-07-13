import {
  Braces,
  ChevronDown,
  ChevronRight,
  Code2,
  FileText,
  Minus,
  Plus,
  Printer,
  RotateCcw,
  Workflow,
  X,
} from 'lucide-react';
import React, { useEffect, useMemo, useState } from 'react';

import FieldSheetLayout from '../../components/field-sheets/FieldSheetLayout.jsx';
import {
  officialFieldSheetTemplateKeys,
  officialFieldSheetTemplates,
} from '../../constants/officialFieldSheetTemplates.js';
import {
  buildDefaultResultsRows,
  buildFieldSheetResultSections,
  getFieldSheetTemplate,
  normalizeTemplate,
  updateFieldSheetResultCell,
} from '../../utils/fieldSheets.js';
import { getInstitutionalConfiguration } from '../../services/api.js';

import './FieldSheetLabPage.css';

const LAB_TEMPLATE_KEYS = officialFieldSheetTemplateKeys;

const LAB_USERS = Object.freeze([
  { id: 101, full_name: 'Técnico Demo', email: 'tecnico@example.com' },
  { id: 102, full_name: 'Calidad Demo', email: 'calidad@example.com' },
  { id: 103, full_name: 'Captura Demo', email: 'captura@example.com' },
]);

const INITIAL_VALUES = Object.freeze({
  work_order_number: 'LAB-0001',
  reserved_certificate_folio: 'CERT-DEMO-001',
  attention: 'Responsable de laboratorio',
  company: 'Empresa Demo',
  address: 'Av. Industria 100, Guadalajara, Jalisco',
  instrument: 'Fluke 87V',
  scope: '0 a 1000',
  minimum_division: '0.01',
  brand: 'Fluke',
  model: '87V',
  serial_number: '123456',
  internal_id: 'EQ-DEMO-01',
  location: 'Laboratorio principal',
  calibration_place: 'Laboratorio MYC',
  reception_date: '2026-07-13',
  calibration_date: '2026-07-13',
  next_calibration_date: '2027-07-13',
  humidity_start: '45 %',
  humidity_end: '46 %',
  temperature_start: '23 °C',
  temperature_end: '24 °C',
  environment_humidity_start: '45 %',
  environment_humidity_end: '46 %',
  environment_temperature_start: '23 °C',
  environment_temperature_end: '24 °C',
  units: 'Unidad de la magnitud',
  initial_condition: 'Equipo recibido en condición operativa.',
  final_condition: 'Equipo entregado en condición operativa.',
  observations: 'Documento de laboratorio. Todos los valores son manuales.',
  evidence_notes: 'Sin conexión a ETS, equipos, certificados o base de datos.',
});

function makeSignatureData(label) {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="280" height="70"><path d="M12 48 C42 10 62 62 92 29 S142 50 172 22 S218 53 264 20" fill="none" stroke="#175cd3" stroke-width="3"/><text x="14" y="66" font-size="12" fill="#344054">${label}</text></svg>`;
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
}

function createSignatures(template) {
  const slots = template.signature_layout?.slots || [
    { role: 'calibrated_by', display_label: 'Calibró' },
    { role: 'reviewed_by', display_label: 'Revisó' },
    { role: 'report_made_by', display_label: 'Elaboró informe' },
  ];
  return slots.map((slot, index) => ({
    role: slot.role,
    displayLabel: slot.display_label,
    name: LAB_USERS[index]?.full_name || '',
    signatureData: makeSignatureData(LAB_USERS[index]?.full_name || slot.display_label),
    signedAt: '2026-07-13',
    userId: String(LAB_USERS[index]?.id || ''),
    position: index,
  }));
}

function createRows(template) {
  const sections = Object.fromEntries(template.result_sections.map((section) => [section.key, section]));
  return buildDefaultResultsRows(template).map((row) => {
    const section = sections[row.sectionKey];
    const fixedLabel = section?.metadata?.fixed_rows?.[row.rowNumber - 1];
    const firstColumn = section?.columns?.[0]?.key;
    return {
      ...row,
      ...Object.fromEntries(
        Object.keys(row)
          .filter((key) => !['id', 'sectionKey', 'rowNumber'].includes(key))
          .map((key, columnIndex) => [key, key === firstColumn && fixedLabel ? fixedLabel : `${row.rowNumber}.${columnIndex + 1}`]),
      ),
    };
  });
}

function createLabDocument(templateKey) {
  const template = normalizeTemplate(officialFieldSheetTemplates[templateKey] || getFieldSheetTemplate(templateKey));
  return {
    template,
    values: { ...INITIAL_VALUES },
    rows: createRows(template),
    signatures: createSignatures(template),
    snapshot: JSON.parse(JSON.stringify(template)),
  };
}

const BLOCK_LABELS = {
  HeaderBlock: 'DocumentHeader',
  ClientBlock: 'CustomerBlock',
  GeneralDataBlock: 'CustomerBlock',
  EquipmentBlock: 'InstrumentBlock',
  EquipmentDataBlock: 'InstrumentBlock',
  CalibrationDataBlock: 'CalibrationBlock',
  EnvironmentalBlock: 'EnvironmentalBlock',
  ObservationsBlock: 'ObservationsBlock',
  SimpleComparisonTableBlock: 'ComparisonTable',
  MultiPointTableBlock: 'ComparisonTable',
  SectionedTableBlock: 'SectionedTable',
  PressureTableBlock: 'PressureTable',
  MassBalanceTableBlock: 'MassBalanceTable',
  SignaturesBlock: 'SignatureBlock',
  FooterBlock: 'DocumentFooter',
};

function InspectorSection({ icon: Icon, title, open, onToggle, children }) {
  return (
    <section className="field-sheet-lab-inspector__section">
      <button aria-expanded={open} onClick={onToggle} type="button">
        <span><Icon size={15} />{title}</span>
        {open ? <ChevronDown size={15} /> : <ChevronRight size={15} />}
      </button>
      {open ? <div className="field-sheet-lab-inspector__body">{children}</div> : null}
    </section>
  );
}

export default function FieldSheetLabPage() {
  const requestedTemplate = new URLSearchParams(window.location.search).get('template');
  const initialTemplateKey = LAB_TEMPLATE_KEYS.includes(requestedTemplate) ? requestedTemplate : 'anemometro';
  const [templateKey, setTemplateKey] = useState(initialTemplateKey);
  const [document, setDocument] = useState(() => createLabDocument(initialTemplateKey));
  const [isInspectorOpen, setIsInspectorOpen] = useState(true);
  const [isStructureOpen, setIsStructureOpen] = useState(false);
  const [isPrintPreviewOpen, setIsPrintPreviewOpen] = useState(() => new URLSearchParams(window.location.search).get('print') === '1');
  const [activeSectionKey, setActiveSectionKey] = useState(document.template.result_sections[0]?.key || '');
  const [openPanels, setOpenPanels] = useState({ summary: true, blocks: true, table: true, snapshot: false, json: false });
  const [institution, setInstitution] = useState(null);
  const [institutionError, setInstitutionError] = useState('');

  useEffect(() => {
    let active = true;
    getInstitutionalConfiguration()
      .then((configuration) => {
        if (active) setInstitution(configuration);
      })
      .catch((requestError) => {
        if (active) setInstitutionError(requestError.message || 'No se pudo cargar la identidad institucional.');
      });
    return () => { active = false; };
  }, []);

  const templatesByKey = useMemo(
    () => officialFieldSheetTemplates,
    [],
  );
  const resultSections = useMemo(
    () => buildFieldSheetResultSections(document.rows, templateKey, templatesByKey),
    [document.rows, templateKey, templatesByKey],
  );
  const currentJson = useMemo(() => ({
    template_key: templateKey,
    template_version: document.template.version,
    institution,
    values: document.values,
    results_rows: document.rows,
    signatures: document.signatures,
  }), [document, institution, templateKey]);
  const activeSection = resultSections.find((section) => section.key === activeSectionKey) || resultSections[0];

  function changeTemplate(nextKey) {
    const nextDocument = createLabDocument(nextKey);
    setTemplateKey(nextKey);
    setDocument(nextDocument);
    setActiveSectionKey(nextDocument.template.result_sections[0]?.key || '');
  }

  function resetDocument() {
    changeTemplate(templateKey);
  }

  function updateSignature(index, updates) {
    setDocument((current) => ({
      ...current,
      signatures: current.signatures.map((signature, signatureIndex) =>
        signatureIndex === index ? { ...signature, ...updates } : signature
      ),
    }));
  }

  function addRow() {
    if (!activeSection) return;
    const sectionRows = document.rows.filter((row) => row.sectionKey === activeSection.key);
    const nextRowNumber = Math.max(0, ...sectionRows.map((row) => Number(row.rowNumber) || 0)) + 1;
    const row = {
      id: null,
      sectionKey: activeSection.key,
      rowNumber: nextRowNumber,
      ...Object.fromEntries((activeSection.columns || []).map((column) => [column.key, ''])),
    };
    setDocument((current) => ({ ...current, rows: [...current.rows, row] }));
  }

  function removeRow() {
    if (!activeSection) return;
    const candidates = document.rows.filter((row) => row.sectionKey === activeSection.key);
    if (candidates.length <= 1) return;
    const lastRow = candidates[candidates.length - 1];
    setDocument((current) => ({
      ...current,
      rows: current.rows.filter((row) => row !== lastRow),
    }));
  }

  function togglePanel(key) {
    setOpenPanels((current) => ({ ...current, [key]: !current[key] }));
  }

  const renderer = (
    <FieldSheetLayout
      institution={institution}
      onResultChange={(sectionKey, rowNumber, columnKey, value) => {
        setDocument((current) => ({
          ...current,
          rows: updateFieldSheetResultCell(current.rows, sectionKey, rowNumber, columnKey, value),
        }));
      }}
      onSignatureChange={updateSignature}
      onValueChange={(key, value) => {
        setDocument((current) => ({ ...current, values: { ...current.values, [key]: value } }));
      }}
      resultSections={resultSections}
      signatures={document.signatures}
      template={document.template}
      users={LAB_USERS}
      values={document.values}
    />
  );

  return (
    <main className="field-sheet-lab">
      <header className="field-sheet-lab-toolbar">
        <div>
          <span className="field-sheet-lab-eyebrow">Sandbox documental</span>
          <h1>Laboratorio de Hojas de Campo</h1>
          <p>Estado local · sin ETS, equipos, certificados ni base de datos</p>
        </div>
        <div className="field-sheet-lab-toolbar__actions">
          <label>
            Plantilla
            <select aria-label="Seleccionar plantilla" value={templateKey} onChange={(event) => changeTemplate(event.target.value)}>
              {LAB_TEMPLATE_KEYS.map((key) => <option key={key} value={key}>{officialFieldSheetTemplates[key].name}</option>)}
            </select>
          </label>
          <button onClick={() => setIsStructureOpen((current) => !current)} type="button"><Workflow size={17} />Mostrar estructura</button>
          <button onClick={() => setIsPrintPreviewOpen(true)} type="button"><FileText size={17} />Vista PDF</button>
          <button aria-pressed={isInspectorOpen} onClick={() => setIsInspectorOpen((current) => !current)} type="button"><Code2 size={17} />Inspector</button>
          <button onClick={resetDocument} type="button"><RotateCcw size={17} />Reiniciar</button>
        </div>
      </header>

      {institutionError ? <div className="form-error dashboard-error">Identidad institucional: {institutionError}</div> : null}
      {!institution && !institutionError ? <div className="field-sheet-lab-loading">Cargando identidad institucional del ERP…</div> : null}

      {isStructureOpen ? (
        <section className="field-sheet-lab-structure" aria-label="Estructura ensamblada">
          <div className="field-sheet-lab-structure__node is-root">{document.template.name}</div>
          {document.template.blocks.filter((block) => block.visible !== false).map((block) => (
            <React.Fragment key={block.key}>
              <span className="field-sheet-lab-structure__arrow">↓</span>
              <div className="field-sheet-lab-structure__node">
                <strong>{BLOCK_LABELS[block.block_type] || block.block_type}</strong>
                <small>{block.key}</small>
              </div>
            </React.Fragment>
          ))}
        </section>
      ) : null}

      <section className={`field-sheet-lab-workspace ${isInspectorOpen ? 'has-inspector' : ''}`}>
        <div className="field-sheet-lab-canvas">
          <div className="field-sheet-lab-table-tools">
            <label>
              Sección de tabla
              <select value={activeSection?.key || ''} onChange={(event) => setActiveSectionKey(event.target.value)}>
                {resultSections.map((section) => <option key={section.key} value={section.key}>{section.title}</option>)}
              </select>
            </label>
            <span>{activeSection?.rows.length || 0} filas · {activeSection?.columns.length || 0} columnas</span>
            <button onClick={addRow} type="button"><Plus size={15} />Agregar fila</button>
            <button onClick={removeRow} type="button"><Minus size={15} />Quitar última</button>
          </div>
          <div className="field-sheet-lab-paper" data-testid="field-sheet-lab-renderer">{renderer}</div>
        </div>

        {isInspectorOpen ? (
          <aside className="field-sheet-lab-inspector">
            <div className="field-sheet-lab-inspector__header"><div><span>Desarrollo</span><strong>Inspector del motor</strong></div><button aria-label="Cerrar inspector" onClick={() => setIsInspectorOpen(false)} type="button"><X size={17} /></button></div>
            <InspectorSection icon={FileText} title="Plantilla" open={openPanels.summary} onToggle={() => togglePanel('summary')}>
              <dl><dt>Plantilla</dt><dd>{document.template.name}</dd><dt>Clave</dt><dd>{templateKey}</dd><dt>Versión</dt><dd>{document.template.version}</dd><dt>Familia</dt><dd>{document.template.table_family}</dd><dt>Bloques</dt><dd>{document.template.blocks.length}</dd></dl>
            </InspectorSection>
            <InspectorSection icon={Workflow} title="Bloques" open={openPanels.blocks} onToggle={() => togglePanel('blocks')}>
              <ol className="field-sheet-lab-block-list">{document.template.blocks.map((block) => <li key={block.key}><strong>{BLOCK_LABELS[block.block_type] || block.block_type}</strong><small>{block.key}</small></li>)}</ol>
            </InspectorSection>
            <InspectorSection icon={Braces} title="Tabla" open={openPanels.table} onToggle={() => togglePanel('table')}>
              <label>Sección<select value={activeSection?.key || ''} onChange={(event) => setActiveSectionKey(event.target.value)}>{resultSections.map((section) => <option key={section.key} value={section.key}>{section.title}</option>)}</select></label>
              <dl><dt>Filas actuales</dt><dd>{activeSection?.rows.length || 0}</dd><dt>Columnas</dt><dd>{activeSection?.columns.map((column) => column.label).join(', ')}</dd></dl>
              <div className="field-sheet-lab-signature-tools">
                <strong>Firmas simuladas</strong>
                {document.signatures.map((signature, index) => <button key={signature.role} onClick={() => updateSignature(index, { signatureData: signature.signatureData ? '' : makeSignatureData(signature.name || signature.displayLabel) })} type="button">{signature.signatureData ? `Limpiar ${signature.displayLabel}` : `Firmar ${signature.displayLabel}`}</button>)}
              </div>
            </InspectorSection>
            <InspectorSection icon={Code2} title="Snapshot generado" open={openPanels.snapshot} onToggle={() => togglePanel('snapshot')}><pre>{JSON.stringify(document.snapshot, null, 2)}</pre></InspectorSection>
            <InspectorSection icon={Braces} title="JSON actual" open={openPanels.json} onToggle={() => togglePanel('json')}><pre>{JSON.stringify(currentJson, null, 2)}</pre></InspectorSection>
          </aside>
        ) : null}
      </section>

      {isPrintPreviewOpen ? (
        <div className="field-sheet-lab-print-modal" role="dialog" aria-modal="true" aria-label="Vista PDF">
          <div className="field-sheet-lab-print-modal__bar"><div><span>Mismo renderer</span><strong>Vista PDF · {document.template.name}</strong></div><div><button onClick={() => window.print()} type="button"><Printer size={17} />Imprimir</button><button aria-label="Cerrar vista PDF" onClick={() => setIsPrintPreviewOpen(false)} type="button"><X size={18} /></button></div></div>
          <div className="field-sheet-lab-print-document">{renderer}</div>
        </div>
      ) : null}
    </main>
  );
}
