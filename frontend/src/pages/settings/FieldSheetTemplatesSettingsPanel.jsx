import React, { useEffect, useMemo, useState } from 'react';

import FieldSheetLayout from '../../components/field-sheets/FieldSheetLayout.jsx';
import {
  fieldSheetBlockFamilies,
  fieldSheetTemplates as fallbackTemplates,
  tableFamilyDefinitions,
  templateNameByKey,
} from '../../constants/fieldSheetTemplates.js';
import {
  activateFieldSheetTemplate,
  createFieldSheetTemplate,
  deleteFieldSheetTemplate,
  duplicateFieldSheetTemplate,
  exportFieldSheetTemplate,
  getFieldSheetTemplateCatalog,
  getInstitutionalConfiguration,
  importFieldSheetTemplate,
  listFieldSheetTemplates,
  updateFieldSheetTemplateDefinition,
  updateInstitutionalConfiguration,
} from '../../services/api.js';
import { buildFieldSheetResultSections, getFieldSheetTemplate, normalizeTemplate } from '../../utils/fieldSheets.js';

const TEMPLATE_KEYS = Object.keys(templateNameByKey);

function getRoleNames(user) {
  return (user?.roles ?? []).map((role) => (role.name || '').toLowerCase());
}

function canManageTemplates(user) {
  const roles = getRoleNames(user);
  return roles.some((role) =>
    ['admin', 'administrador', 'administrator', 'calidad', 'quality', 'desarrollador', 'developer'].includes(role)
  );
}

function cloneTemplate(template) {
  return JSON.parse(JSON.stringify(normalizeTemplate(template)));
}

function blankPreviewValues() {
  return {
    work_order_number: 'OT-0001',
    reserved_certificate_folio: 'MYC-CERT-0001',
    attention: 'Atención',
    company: 'Cliente ejemplo',
    address: 'Dirección ejemplo',
    instrument: 'Equipo ejemplo',
    scope: '0 a 100',
    minimum_division: '0.01',
    brand: 'Marca',
    serial_number: 'SER-001',
    model: 'Modelo',
    internal_id: 'INT-001',
    location: 'Laboratorio',
    calibration_place: 'En sitio',
    reception_date: '2026-07-03',
    calibration_date: '2026-07-03',
    next_calibration_date: '2027-07-03',
    humidity_start: '45',
    humidity_end: '46',
    temperature_start: '23',
    temperature_end: '24',
    units: 'Unidad',
    observations: 'Observaciones de ejemplo',
    evidence_notes: 'Notas de ejemplo',
    initial_condition: 'Equipo recibido en condición operativa',
    final_condition: 'Equipo entregado operativo',
    calibrated_by: 'Calibró',
    reviewed_by: 'Revisó',
    report_made_by: 'Reporte',
    purchase_order_or_quotation: 'OC-001',
  };
}

function createBlankTemplate(templateKey = 'general') {
  const base = cloneTemplate(getFieldSheetTemplate(templateKey));
  return {
    ...base,
    id: null,
    status: 'draft',
    source: 'fallback',
    name: `${base.name} nueva`,
  };
}

function downloadJson(filename, payload) {
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

function TableFamiliesPanel({ families }) {
  return (
    <section className="quotation-section">
      <div className="quotation-section__title">
        <p>Familias de tablas</p>
        <h3>{families.length} disponibles</h3>
      </div>
      <div className="field-sheet-prep-list">
        {families.map((family) => (
          <article className="glass-card-mini" key={family.family_key}>
            <strong>{family.name}</strong>
            <span>{family.family_key}</span>
            <small>{family.description}</small>
            <small>Filas: {family.default_rows} / min {family.min_rows} / max {family.max_rows}</small>
          </article>
        ))}
      </div>
    </section>
  );
}

function BlockCatalogPanel({ blockTypes }) {
  return (
    <section className="quotation-section">
      <div className="quotation-section__title">
        <p>Bloques</p>
        <h3>{blockTypes.length} disponibles</h3>
      </div>
      <div className="field-sheet-prep-list">
        {blockTypes.map((block) => (
          <article className="glass-card-mini" key={block.key}>
            <strong>{block.label}</strong>
            <span>{block.key}</span>
            <small>{block.is_table ? 'Bloque de tabla' : 'Bloque de formulario'}</small>
          </article>
        ))}
      </div>
    </section>
  );
}

function SettingsMasterPanel() {
  const sections = [
    'Usuarios',
    'Roles',
    'Permisos',
    'Auditoría',
    'Plantillas de hojas',
    'Familias de tablas',
    'Bloques',
    'Catálogos maestros',
    'Estados',
    'Flujos operativos',
    'Folios',
    'PDFs / documentos',
    'Empresa',
    'Parámetros generales',
  ];

  return (
    <section className="quotation-section">
      <div className="quotation-section__title">
        <p>Panel maestro</p>
        <h3>Configuración operativa preparada</h3>
      </div>
      <div className="field-sheet-prep-list">
        {sections.map((section) => (
          <article className="glass-card-mini" key={section}>
            <strong>{section}</strong>
            <small>Preparado dentro de Configuración sin cambiar el flujo ETS.</small>
          </article>
        ))}
      </div>
    </section>
  );
}

function FieldSheetTemplatesSettingsPanel({ user }) {
  const [templates, setTemplates] = useState([]);
  const [catalog, setCatalog] = useState({ block_types: [], table_families: [] });
  const [selectedTemplateId, setSelectedTemplateId] = useState('');
  const [draft, setDraft] = useState(createBlankTemplate('general'));
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [newBlockType, setNewBlockType] = useState('ResultsTableBlock');
  const [importPayload, setImportPayload] = useState('');
  const [institution, setInstitution] = useState({
    legal_name: 'METROLOGÍA Y SERVICIOS MYC',
    document_code: 'FCA-30',
    initial_revision: 'R1',
    address: '',
    phone: '',
    email: '',
    logo_path: 'frontend/src/assets/myc-logo.png',
  });

  const templatesById = useMemo(() => Object.fromEntries(templates.map((template) => [String(template.id), normalizeTemplate(template)])), [templates]);
  const blockTypes = useMemo(() => (catalog.block_types?.length ? catalog.block_types : Object.keys(fieldSheetBlockFamilies).map((key) => ({ key, label: key, is_table: key.includes('Table') }))), [catalog]);
  const tableFamilies = useMemo(() => (catalog.table_families?.length ? catalog.table_families : Object.values(tableFamilyDefinitions)), [catalog]);

  useEffect(() => {
    loadTemplates();
  }, []);

  async function loadTemplates() {
    setError('');
    setIsLoading(true);
    try {
      const [templateData, catalogData, institutionData] = await Promise.all([
        listFieldSheetTemplates({ includeAll: true }),
        getFieldSheetTemplateCatalog(),
        getInstitutionalConfiguration(),
      ]);
      const normalizedTemplates = Array.isArray(templateData) && templateData.length
        ? templateData.map((item) => normalizeTemplate(item))
        : Object.values(fallbackTemplates).map((item) => normalizeTemplate(item));
      setTemplates(normalizedTemplates);
      setCatalog(catalogData || { block_types: [], table_families: [] });
      setInstitution((current) => ({ ...current, ...(institutionData || {}) }));
      const initial = normalizedTemplates[0] || createBlankTemplate('general');
      setSelectedTemplateId(initial.id ? String(initial.id) : '');
      setDraft(cloneTemplate(initial));
    } catch (requestError) {
      setError(requestError.message);
      const fallbackList = Object.values(fallbackTemplates).map((item) => normalizeTemplate(item));
      setTemplates(fallbackList);
      setSelectedTemplateId('');
      setDraft(cloneTemplate(fallbackList[0]));
    } finally {
      setIsLoading(false);
    }
  }

  function selectTemplateById(templateId) {
    setSelectedTemplateId(templateId);
    const nextTemplate = templatesById[templateId];
    if (nextTemplate) {
      setDraft(cloneTemplate(nextTemplate));
    }
  }

  function updateDraft(field, value) {
    setDraft((current) => ({ ...current, [field]: value }));
  }

  function updateBlock(index, updates) {
    setDraft((current) => ({
      ...current,
      blocks: current.blocks.map((block, blockIndex) => (blockIndex === index ? { ...block, ...updates } : block)),
    }));
  }

  function moveBlock(index, direction) {
    setDraft((current) => {
      const blocks = [...current.blocks];
      const nextIndex = index + direction;
      if (nextIndex < 0 || nextIndex >= blocks.length) return current;
      [blocks[index], blocks[nextIndex]] = [blocks[nextIndex], blocks[index]];
      return {
        ...current,
        blocks: blocks.map((block, blockIndex) => ({
          ...block,
          order: blockIndex + 1,
          capture_order: blockIndex + 1,
          print_order: blockIndex + 1,
        })),
      };
    });
  }

  function removeBlock(index) {
    setDraft((current) => ({
      ...current,
      blocks: current.blocks
        .filter((_, blockIndex) => blockIndex !== index)
        .map((block, blockIndex) => ({
          ...block,
          order: blockIndex + 1,
          capture_order: blockIndex + 1,
          print_order: blockIndex + 1,
        })),
    }));
  }

  function addBlock() {
    const baseTemplate = getFieldSheetTemplate(draft.template_key || draft.key || 'general');
    const sourceBlock = baseTemplate.blocks.find((block) => block.block_type === newBlockType);
    const nextIndex = draft.blocks.length + 1;
    setDraft((current) => ({
      ...current,
      blocks: [
        ...current.blocks,
        sourceBlock
          ? {
              ...JSON.parse(JSON.stringify(sourceBlock)),
              key: `${sourceBlock.key}_${Date.now()}`,
              block_key: `${sourceBlock.block_key || sourceBlock.key}_${Date.now()}`,
              order: nextIndex,
              capture_order: nextIndex,
              print_order: nextIndex,
            }
          : {
              key: `${newBlockType}_${Date.now()}`,
              block_key: `${newBlockType}_${Date.now()}`,
              block_type: newBlockType,
              title: newBlockType,
              visible_fields: [],
              fields: [],
              columns: [],
              sections: [],
              table_config: {},
              order: nextIndex,
              capture_order: nextIndex,
              print_order: nextIndex,
              visible: true,
              print_visible: true,
              capture_visible: true,
              pdf_visible: true,
            },
      ],
    }));
  }

  function templatePayload() {
    return {
      template_key: draft.template_key || draft.key,
      name: draft.name,
      description: draft.description || null,
      status: draft.status || 'draft',
      code: draft.code || draft.document_code || 'FCA-30',
      revision: draft.revision || draft.document_revision || 'R1',
      document_code: draft.document_code || draft.code || 'FCA-30',
      document_revision: draft.document_revision || draft.revision || 'R1',
      pages: Number(draft.pages || 1),
      pdf_template: draft.pdf_template || 'field_sheet_general_pdf.html',
      table_family: draft.table_family || 'custom',
      blocks: draft.blocks,
      validations: draft.validations || {},
      print_config: draft.print_config || {},
      pdf_config: draft.pdf_config || {},
      permissions_config: draft.permissions_config || {},
      metadata: draft.metadata || {},
      signature_layout: draft.signature_layout || {},
      pagination: draft.pagination || { mode: 'dynamic', label: 'Página X de Y' },
      automation: draft.automation || { mode: 'manual_only', calculations: [] },
    };
  }

  async function handleSave() {
    setIsSaving(true);
    setError('');
    setNotice('');
    try {
      const payload = templatePayload();
      const saved = draft.id
        ? await updateFieldSheetTemplateDefinition(draft.id, payload)
        : await createFieldSheetTemplate(payload);
      setNotice(draft.id && draft.status === 'active' ? 'Nueva versión creada a partir de la activa' : 'Plantilla guardada');
      await loadTemplates();
      if (saved?.id) {
        selectTemplateById(String(saved.id));
      }
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsSaving(false);
    }
  }

  async function handleDuplicate() {
    if (!draft.id) return;
    setError('');
    setNotice('');
    try {
      const duplicated = await duplicateFieldSheetTemplate(draft.id);
      setNotice('Versión duplicada');
      await loadTemplates();
      if (duplicated?.id) {
        selectTemplateById(String(duplicated.id));
      }
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  async function handleActivate() {
    if (!draft.id) return;
    setError('');
    setNotice('');
    try {
      const activated = await activateFieldSheetTemplate(draft.id);
      setNotice('Versión publicada y activada');
      await loadTemplates();
      if (activated?.id) {
        selectTemplateById(String(activated.id));
      }
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  async function handleDelete() {
    if (!draft.id) return;
    setError('');
    setNotice('');
    try {
      await deleteFieldSheetTemplate(draft.id);
      setNotice('Plantilla archivada');
      await loadTemplates();
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  async function handleExport() {
    if (!draft.id) return;
    setError('');
    try {
      const payload = await exportFieldSheetTemplate(draft.id);
      downloadJson(`${draft.template_key || draft.key}-v${draft.version || 1}.json`, payload);
      setNotice('Plantilla exportada');
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  async function handleImport() {
    if (!importPayload.trim()) return;
    setError('');
    setNotice('');
    try {
      const parsed = JSON.parse(importPayload);
      const imported = await importFieldSheetTemplate({
        template: parsed.template || parsed,
        activate: false,
        mode: 'new_version',
      });
      setNotice('Plantilla importada');
      await loadTemplates();
      if (imported?.id) {
        selectTemplateById(String(imported.id));
      }
    } catch (requestError) {
      setError(requestError.message || 'JSON inválido');
    }
  }

  async function handleInstitutionSave() {
    setIsSaving(true);
    setError('');
    setNotice('');
    try {
      const saved = await updateInstitutionalConfiguration({
        legal_name: institution.legal_name,
        document_code: institution.document_code,
        initial_revision: institution.initial_revision,
        address: institution.address || null,
        phone: institution.phone || null,
        email: institution.email || null,
        logo_path: institution.logo_path || null,
      });
      setInstitution(saved);
      setNotice('Identidad institucional actualizada');
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsSaving(false);
    }
  }

  if (!canManageTemplates(user)) {
    return <div className="clients-empty">Sin permisos para administrar plantillas de hojas.</div>;
  }

  return (
    <section className="settings-panel">
      {error ? <div className="form-error dashboard-error">{error}</div> : null}
      {notice ? <div className="form-success dashboard-success">{notice}</div> : null}

      <div className="section-heading">
        <div>
          <p>Plantillas de hojas</p>
          <h2>{isLoading ? 'Cargando...' : `${templates.length || TEMPLATE_KEYS.length} versiones disponibles`}</h2>
        </div>
      </div>

      <section className="quotation-section">
        <div className="quotation-section__title">
          <p>Identidad institucional</p>
          <h3>Fuente única para hojas de campo</h3>
        </div>
        <div className="client-form client-form--modal">
          <label>Razón social<input value={institution.legal_name || ''} onChange={(event) => setInstitution((current) => ({ ...current, legal_name: event.target.value }))} /></label>
          <label>Código documental<input value={institution.document_code || ''} onChange={(event) => setInstitution((current) => ({ ...current, document_code: event.target.value }))} /></label>
          <label>Revisión inicial<input value={institution.initial_revision || ''} onChange={(event) => setInstitution((current) => ({ ...current, initial_revision: event.target.value }))} /></label>
          <label>Domicilio<input value={institution.address || ''} onChange={(event) => setInstitution((current) => ({ ...current, address: event.target.value }))} /></label>
          <label>Teléfono<input value={institution.phone || ''} onChange={(event) => setInstitution((current) => ({ ...current, phone: event.target.value }))} /></label>
          <label>Correo<input type="email" value={institution.email || ''} onChange={(event) => setInstitution((current) => ({ ...current, email: event.target.value }))} /></label>
          <label>Ruta o URL del logotipo<input value={institution.logo_path || ''} onChange={(event) => setInstitution((current) => ({ ...current, logo_path: event.target.value }))} /></label>
        </div>
        <div className="settings-filters__actions">
          <button className="primary-button" disabled={isSaving} onClick={handleInstitutionSave} type="button">Guardar identidad</button>
        </div>
      </section>

      <div className="quotation-commercial-grid service-order-info-grid">
        <article>
          <span>Versión</span>
          <select value={selectedTemplateId} onChange={(event) => selectTemplateById(event.target.value)}>
            {templates.map((template) => (
              <option key={`${template.template_key}-${template.version}-${template.id ?? 'fallback'}`} value={String(template.id ?? '')}>
                {template.name} | {template.template_key} | v{template.version} | {template.status}
              </option>
            ))}
          </select>
        </article>
        <article>
          <span>Plantilla base</span>
          <select value={draft.template_key || 'general'} onChange={(event) => setDraft(createBlankTemplate(event.target.value))}>
            {TEMPLATE_KEYS.map((templateKey) => (
              <option key={templateKey} value={templateKey}>{templateNameByKey[templateKey]}</option>
            ))}
          </select>
        </article>
        <article>
          <span>Estado</span>
          <strong>{draft.status || 'draft'}</strong>
        </article>
        <article>
          <span>Versión</span>
          <strong>{draft.version || 1}</strong>
        </article>
      </div>

      <div className="client-form client-form--modal">
        <label>
          Nombre visible
          <input type="text" value={draft.name || ''} onChange={(event) => updateDraft('name', event.target.value)} />
        </label>
        <label>
          Descripción
          <input type="text" value={draft.description || ''} onChange={(event) => updateDraft('description', event.target.value)} />
        </label>
        <label>
          Estado
          <select value={draft.status || 'draft'} onChange={(event) => updateDraft('status', event.target.value)}>
            <option value="draft">draft</option>
            <option value="active">active</option>
            <option value="inactive">inactive</option>
          </select>
        </label>
        <label>
          Familia de tabla
          <select value={draft.table_family || 'custom'} onChange={(event) => updateDraft('table_family', event.target.value)}>
            {tableFamilies.map((family) => (
              <option key={family.family_key} value={family.family_key}>{family.name}</option>
            ))}
          </select>
        </label>
        <label>
          Código documental
          <input type="text" value={draft.document_code || draft.code || ''} onChange={(event) => updateDraft('document_code', event.target.value)} />
        </label>
        <label>
          Revisión documental
          <input type="text" value={draft.document_revision || draft.revision || ''} onChange={(event) => updateDraft('document_revision', event.target.value)} />
        </label>
      </div>

      <div className="settings-filters">
        <label className="field-label">
          Agregar bloque
          <select className="settings-role-select" value={newBlockType} onChange={(event) => setNewBlockType(event.target.value)}>
            {blockTypes.map((blockType) => (
              <option key={blockType.key} value={blockType.key}>{blockType.label}</option>
            ))}
          </select>
        </label>
        <div className="settings-filters__actions">
          <button className="secondary-button" onClick={addBlock} type="button">Agregar bloque</button>
          <button className="secondary-button" disabled={!draft.id} onClick={handleDuplicate} type="button">Duplicar versión</button>
          <button className="secondary-button" disabled={!draft.id} onClick={handleActivate} type="button">Publicar</button>
          <button className="secondary-button" disabled={!draft.id} onClick={handleExport} type="button">Exportar JSON</button>
          <button className="secondary-button" disabled={!draft.id} onClick={handleDelete} type="button">Archivar</button>
          <button className="primary-button" disabled={isSaving} onClick={handleSave} type="button">{isSaving ? 'Guardando...' : 'Guardar versión'}</button>
        </div>
      </div>

      <div className="field-sheet-prep-list">
        {draft.blocks.map((block, index) => (
          <article className="glass-card-mini" key={block.key}>
            <strong>{block.title}</strong>
            <span>{block.block_type}</span>
            <label>
              Título visible
              <input type="text" value={block.title || ''} onChange={(event) => updateBlock(index, { title: event.target.value })} />
            </label>
            <label>
              Campos visibles
              <input
                type="text"
                value={(block.visible_fields || []).join(', ')}
                onChange={(event) => updateBlock(index, { visible_fields: event.target.value.split(',').map((value) => value.trim()).filter(Boolean) })}
              />
            </label>
            {(String(block.block_type).includes('TableBlock') || block.block_type === 'ResultsTableBlock') ? (
              <>
                <label>
                  Filas
                  <input type="number" value={block.rows ?? 0} onChange={(event) => updateBlock(index, { rows: Number(event.target.value || 0) })} />
                </label>
                <label>
                  Mínimo
                  <input type="number" value={block.min_rows ?? 0} onChange={(event) => updateBlock(index, { min_rows: Number(event.target.value || 0) })} />
                </label>
                <label>
                  Máximo
                  <input type="number" value={block.max_rows ?? 0} onChange={(event) => updateBlock(index, { max_rows: Number(event.target.value || 0) })} />
                </label>
                <label>
                  Columnas
                  <input
                    type="text"
                    value={(block.columns || []).map((column) => column.key).join(', ')}
                    onChange={(event) => updateBlock(index, {
                      columns: event.target.value.split(',').map((value) => value.trim()).filter(Boolean).map((key) => ({
                        key,
                        label: key,
                        source: key,
                        editable: true,
                      })),
                    })}
                  />
                </label>
              </>
            ) : null}
            <label>
              <input type="checkbox" checked={Boolean(block.required)} onChange={(event) => updateBlock(index, { required: event.target.checked })} />
              Obligatorio
            </label>
            <label>
              <input type="checkbox" checked={Boolean(block.capture_visible ?? true)} onChange={(event) => updateBlock(index, { capture_visible: event.target.checked })} />
              Visible en captura
            </label>
            <label>
              <input type="checkbox" checked={Boolean(block.pdf_visible ?? true)} onChange={(event) => updateBlock(index, { pdf_visible: event.target.checked })} />
              Visible en PDF
            </label>
            <div className="toolbar-actions">
              <button className="table-button" onClick={() => moveBlock(index, -1)} type="button">Subir</button>
              <button className="table-button" onClick={() => moveBlock(index, 1)} type="button">Bajar</button>
              <button className="table-button" onClick={() => removeBlock(index)} type="button">Quitar</button>
            </div>
          </article>
        ))}
      </div>

      <section className="quotation-section">
        <div className="quotation-section__title">
          <p>Importar plantilla</p>
          <h3>JSON completo</h3>
        </div>
        <textarea
          className="quotation-notes"
          value={importPayload}
          onChange={(event) => setImportPayload(event.target.value)}
          placeholder="Pega aquí el JSON exportado de una plantilla"
          rows={8}
        />
        <div className="settings-filters__actions">
          <button className="secondary-button" onClick={handleImport} type="button">Importar como nueva versión</button>
        </div>
      </section>

      <section className="quotation-section">
        <div className="quotation-section__title">
          <p>Previsualización</p>
          <h3>{draft.name || 'Vista previa'}</h3>
        </div>
        <FieldSheetLayout
          template={normalizeTemplate(draft)}
          institution={institution}
          values={blankPreviewValues()}
          resultSections={buildFieldSheetResultSections([], draft.template_key || draft.key || 'general', {
            [draft.template_key || draft.key || 'general']: normalizeTemplate(draft),
          })}
          onValueChange={() => {}}
          onResultChange={() => {}}
        />
      </section>

      <TableFamiliesPanel families={tableFamilies} />
      <BlockCatalogPanel blockTypes={blockTypes} />
      <SettingsMasterPanel />
    </section>
  );
}

export default FieldSheetTemplatesSettingsPanel;
