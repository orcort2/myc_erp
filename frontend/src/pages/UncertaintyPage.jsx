import { Calculator, Check, Copy, Plus, Send, XCircle } from 'lucide-react';
import React, { useEffect, useMemo, useState } from 'react';
import ActivityPanel from '../components/activity/ActivityPanel.jsx';

import {
  changeUncertaintyModelVersionStatus,
  cloneUncertaintyModelVersion,
  createUncertaintyComponent,
  createUncertaintyFormula,
  createUncertaintyModel,
  createUncertaintyModelVersion,
  getUncertaintyPreview,
  listFieldSheets,
  listUncertaintyModels,
  listUncertaintyModelVersions
} from '../services/api.js';

const emptyModel = {
  code: '',
  name: '',
  description: '',
  magnitude: '',
  equipment_family: '',
  version: '1.0',
  status: 'active',
  default_coverage_factor: 2,
  notes: ''
};

const emptyVersion = {
  version_number: '',
  change_summary: '',
  default_coverage_factor: 2
};

const emptyComponent = {
  key: 'u_patron',
  name: 'Incertidumbre del patron',
  source_type: 'standard_uncertainty',
  distribution: 'normal',
  divisor: '',
  sensitivity_coefficient: 1,
  value_expression: '',
  required: true,
  sort_order: 1,
  metadataText: '{}'
};

const emptyFormula = {
  key: 'u_expandida',
  name: 'Incertidumbre expandida',
  expression: 'expanded(combined_uncertainty, k)',
  result_key: 'expanded_uncertainty',
  sort_order: 1,
  is_active_formula: true
};

function nullable(value) {
  return value === '' || value === undefined ? null : value;
}

function parseMetadata(text) {
  if (!text.trim()) return null;
  try {
    return JSON.parse(text);
  } catch {
    throw new Error('metadata_json debe ser JSON valido.');
  }
}

function statusLabel(value) {
  const labels = {
    draft: 'Borrador',
    in_review: 'En revision',
    approved: 'Aprobada',
    obsolete: 'Obsoleta',
    archived: 'Archivada'
  };
  return labels[value] ?? value;
}

export default function UncertaintyPage() {
  const [models, setModels] = useState([]);
  const [versions, setVersions] = useState([]);
  const [fieldSheets, setFieldSheets] = useState([]);
  const [selectedModelId, setSelectedModelId] = useState('');
  const [selectedVersionId, setSelectedVersionId] = useState('');
  const [selectedFieldSheetId, setSelectedFieldSheetId] = useState('');
  const [modelForm, setModelForm] = useState(emptyModel);
  const [versionForm, setVersionForm] = useState(emptyVersion);
  const [componentForm, setComponentForm] = useState(emptyComponent);
  const [formulaForm, setFormulaForm] = useState(emptyFormula);
  const [preview, setPreview] = useState(null);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [isLoading, setIsLoading] = useState(true);

  const selectedModel = useMemo(
    () => models.find((item) => String(item.id) === String(selectedModelId)) ?? null,
    [models, selectedModelId]
  );
  const selectedVersion = useMemo(
    () => versions.find((item) => String(item.id) === String(selectedVersionId)) ?? null,
    [versions, selectedVersionId]
  );

  async function loadModels() {
    const result = await listUncertaintyModels();
    const items = Array.isArray(result) ? result : [];
    setModels(items);
    if (!selectedModelId && items[0]) setSelectedModelId(String(items[0].id));
  }

  async function loadVersions(modelId = selectedModelId) {
    if (!modelId) {
      setVersions([]);
      setSelectedVersionId('');
      return;
    }
    const result = await listUncertaintyModelVersions(modelId);
    const items = Array.isArray(result) ? result : [];
    setVersions(items);
    if (!items.some((item) => String(item.id) === String(selectedVersionId))) {
      setSelectedVersionId(items[0] ? String(items[0].id) : '');
    }
  }

  async function loadData() {
    setError('');
    setIsLoading(true);
    try {
      const [modelsResult, sheetsResult] = await Promise.all([
        listUncertaintyModels(),
        listFieldSheets()
      ]);
      const modelItems = Array.isArray(modelsResult) ? modelsResult : [];
      setModels(modelItems);
      setFieldSheets(Array.isArray(sheetsResult) ? sheetsResult : []);
      const nextModelId = selectedModelId || (modelItems[0] ? String(modelItems[0].id) : '');
      setSelectedModelId(nextModelId);
      if (nextModelId) {
        const versionResult = await listUncertaintyModelVersions(nextModelId);
        const versionItems = Array.isArray(versionResult) ? versionResult : [];
        setVersions(versionItems);
        setSelectedVersionId(versionItems[0] ? String(versionItems[0].id) : '');
      }
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    loadVersions(selectedModelId).catch((requestError) => setError(requestError.message));
  }, [selectedModelId]);

  async function saveModel(event) {
    event.preventDefault();
    setError('');
    try {
      await createUncertaintyModel({
        ...modelForm,
        equipment_family: nullable(modelForm.equipment_family),
        description: nullable(modelForm.description),
        notes: nullable(modelForm.notes),
        default_coverage_factor: Number(modelForm.default_coverage_factor || 2)
      });
      setModelForm(emptyModel);
      setNotice('Modelo creado');
      await loadModels();
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  async function saveVersion(event) {
    event.preventDefault();
    if (!selectedModelId) return;
    setError('');
    try {
      await createUncertaintyModelVersion(selectedModelId, {
        ...versionForm,
        default_coverage_factor: Number(versionForm.default_coverage_factor || 2),
        change_summary: nullable(versionForm.change_summary)
      });
      setVersionForm(emptyVersion);
      setNotice('Version creada');
      await loadVersions(selectedModelId);
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  async function saveComponent(event) {
    event.preventDefault();
    if (!selectedVersionId) return;
    setError('');
    try {
      await createUncertaintyComponent(selectedVersionId, {
        key: componentForm.key.trim(),
        name: componentForm.name.trim(),
        source_type: componentForm.source_type,
        distribution: nullable(componentForm.distribution),
        divisor: componentForm.divisor === '' ? null : Number(componentForm.divisor),
        sensitivity_coefficient: Number(componentForm.sensitivity_coefficient || 1),
        value_expression: nullable(componentForm.value_expression),
        required: Boolean(componentForm.required),
        sort_order: Number(componentForm.sort_order || 0),
        metadata_json: parseMetadata(componentForm.metadataText)
      });
      setComponentForm(emptyComponent);
      setNotice('Componente agregado');
      await loadVersions(selectedModelId);
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  async function saveFormula(event) {
    event.preventDefault();
    if (!selectedVersionId) return;
    setError('');
    try {
      await createUncertaintyFormula(selectedVersionId, {
        ...formulaForm,
        sort_order: Number(formulaForm.sort_order || 0)
      });
      setFormulaForm(emptyFormula);
      setNotice('Formula agregada');
      await loadVersions(selectedModelId);
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  async function changeStatus(action) {
    if (!selectedVersionId) return;
    setError('');
    try {
      await changeUncertaintyModelVersionStatus(selectedVersionId, action);
      setNotice('Estado actualizado');
      await loadVersions(selectedModelId);
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  async function cloneVersion() {
    if (!selectedVersion) return;
    setError('');
    try {
      await cloneUncertaintyModelVersion(selectedVersion.id, {
        version_number: `${selectedVersion.version_number}.1`,
        change_summary: `Clon de version ${selectedVersion.version_number}`,
        default_coverage_factor: selectedVersion.default_coverage_factor || 2,
        components: [],
        formulas: []
      });
      setNotice('Version clonada');
      await loadVersions(selectedModelId);
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  async function runPreview() {
    if (!selectedFieldSheetId) {
      setError('Selecciona una hoja de campo.');
      return;
    }
    setError('');
    try {
      const result = await getUncertaintyPreview(selectedFieldSheetId);
      setPreview(result);
      setNotice('Preview generado');
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  return (
    <section className="module-workspace service-orders-workspace">
      <div className="module-workspace__hero clients-hero">
        <span className="module-workspace__icon"><Calculator size={28} /></span>
        <div>
          <p>Motor tecnico</p>
          <h1>Incertidumbre</h1>
          <span>Modelos versionables, componentes, formulas y preview tecnico.</span>
        </div>
      </div>

      {error ? <div className="form-error dashboard-error">{error}</div> : null}
      {notice ? <div className="form-notice dashboard-error">{notice}</div> : null}

      <section className="operations-band certificates-summary">
        <div className="operations-band__metric"><strong>{isLoading ? '-' : models.length}</strong><span>Modelos</span></div>
        <div className="operations-band__metric"><strong>{versions.filter((item) => item.status === 'approved').length}</strong><span>Versiones aprobadas</span></div>
        <div className="operations-band__metric"><strong>{selectedVersion?.components?.length ?? 0}</strong><span>Componentes seleccionados</span></div>
      </section>

      <div className="document-library-grid">
        <section className="clients-list-panel">
          <div className="section-heading">
            <div>
              <p>Modelos</p>
              <h2>{selectedModel ? selectedModel.name : 'Selecciona un modelo'}</h2>
            </div>
          </div>
          <div className="document-library-form">
            <select value={selectedModelId} onChange={(event) => setSelectedModelId(event.target.value)}>
              <option value="">Sin modelo</option>
              {models.map((item) => (
                <option key={item.id} value={item.id}>{item.code} - {item.name}</option>
              ))}
            </select>
            <select value={selectedVersionId} onChange={(event) => setSelectedVersionId(event.target.value)}>
              <option value="">Sin version</option>
              {versions.map((item) => (
                <option key={item.id} value={item.id}>v{item.version_number} - {statusLabel(item.status)}</option>
              ))}
            </select>
          </div>

          {selectedVersion ? (
            <div className="pattern-selection-panel">
              <strong>Version {selectedVersion.version_number}</strong>
              <span>Estado: {statusLabel(selectedVersion.status)}</span>
              <span>k por defecto: {selectedVersion.default_coverage_factor}</span>
              <div className="toolbar-actions">
                <button type="button" className="secondary-button" onClick={() => changeStatus('submit-review')}><Send size={15} /> Revision</button>
                <button type="button" className="secondary-button" onClick={() => changeStatus('approve')}><Check size={15} /> Aprobar</button>
                <button type="button" className="secondary-button" onClick={() => changeStatus('obsolete')}><XCircle size={15} /> Obsoletar</button>
                <button type="button" className="secondary-button" onClick={cloneVersion}><Copy size={15} /> Clonar</button>
              </div>
            </div>
          ) : null}

          <div className="document-library-panel">
            <div className="pattern-selection-panel">
              <strong>Componentes</strong>
              {(selectedVersion?.components ?? []).length ? (
                (selectedVersion.components ?? []).map((item) => (
                  <span key={item.id}>{item.key}: {item.name} ({item.source_type})</span>
                ))
              ) : (
                <span>Sin componentes.</span>
              )}
            </div>
            <div className="pattern-selection-panel">
              <strong>Formulas</strong>
              {(selectedVersion?.formulas ?? []).length ? (
                (selectedVersion.formulas ?? []).map((item) => (
                  <span key={item.id}>{item.key}: {item.expression} -&gt; {item.result_key}</span>
                ))
              ) : (
                <span>Sin formulas.</span>
              )}
            </div>
          </div>
        </section>

        <aside className="document-library-panel">
          <form className="document-library-form" onSubmit={saveModel}>
            <h3>Nuevo modelo</h3>
            <input placeholder="Codigo" value={modelForm.code} onChange={(event) => setModelForm({ ...modelForm, code: event.target.value })} />
            <input placeholder="Nombre" value={modelForm.name} onChange={(event) => setModelForm({ ...modelForm, name: event.target.value })} />
            <input placeholder="Magnitud" value={modelForm.magnitude} onChange={(event) => setModelForm({ ...modelForm, magnitude: event.target.value })} />
            <input placeholder="Familia de equipo" value={modelForm.equipment_family} onChange={(event) => setModelForm({ ...modelForm, equipment_family: event.target.value })} />
            <input placeholder="Version inicial" value={modelForm.version} onChange={(event) => setModelForm({ ...modelForm, version: event.target.value })} />
            <button className="primary-button" type="submit"><Plus size={16} /> Crear modelo</button>
          </form>

          <form className="document-library-form" onSubmit={saveVersion}>
            <h3>Nueva version</h3>
            <input placeholder="Version" value={versionForm.version_number} onChange={(event) => setVersionForm({ ...versionForm, version_number: event.target.value })} />
            <input placeholder="Resumen de cambio" value={versionForm.change_summary} onChange={(event) => setVersionForm({ ...versionForm, change_summary: event.target.value })} />
            <input type="number" step="0.01" placeholder="k" value={versionForm.default_coverage_factor} onChange={(event) => setVersionForm({ ...versionForm, default_coverage_factor: event.target.value })} />
            <button className="secondary-button" type="submit">Crear version</button>
          </form>

          <form className="document-library-form" onSubmit={saveComponent}>
            <h3>Agregar componente</h3>
            <input placeholder="Clave" value={componentForm.key} onChange={(event) => setComponentForm({ ...componentForm, key: event.target.value })} />
            <input placeholder="Nombre" value={componentForm.name} onChange={(event) => setComponentForm({ ...componentForm, name: event.target.value })} />
            <select value={componentForm.source_type} onChange={(event) => setComponentForm({ ...componentForm, source_type: event.target.value })}>
              <option value="standard_uncertainty">Incertidumbre patron</option>
              <option value="standard_resolution">Resolucion patron</option>
              <option value="ibc_resolution">Resolucion IBC</option>
              <option value="repeatability">Repetibilidad</option>
              <option value="fixed">Fijo</option>
              <option value="expression">Expresion</option>
            </select>
            <input placeholder="Expresion opcional" value={componentForm.value_expression} onChange={(event) => setComponentForm({ ...componentForm, value_expression: event.target.value })} />
            <textarea rows={3} value={componentForm.metadataText} onChange={(event) => setComponentForm({ ...componentForm, metadataText: event.target.value })} />
            <button className="secondary-button" type="submit">Agregar componente</button>
          </form>

          <form className="document-library-form" onSubmit={saveFormula}>
            <h3>Agregar formula</h3>
            <input placeholder="Clave" value={formulaForm.key} onChange={(event) => setFormulaForm({ ...formulaForm, key: event.target.value })} />
            <input placeholder="Nombre" value={formulaForm.name} onChange={(event) => setFormulaForm({ ...formulaForm, name: event.target.value })} />
            <input placeholder="Expresion" value={formulaForm.expression} onChange={(event) => setFormulaForm({ ...formulaForm, expression: event.target.value })} />
            <input placeholder="Resultado" value={formulaForm.result_key} onChange={(event) => setFormulaForm({ ...formulaForm, result_key: event.target.value })} />
            <button className="secondary-button" type="submit">Agregar formula</button>
          </form>
        </aside>
      </div>

      {selectedModel ? (
        <section className="clients-list-panel">
          <div className="section-heading">
            <div>
              <p>Comunicación interna</p>
              <h2>Actividad del modelo</h2>
            </div>
          </div>
          <ActivityPanel
            entityId={selectedModel.id}
            entityType="uncertainty_model"
          />
        </section>
      ) : null}

      <section className="clients-list-panel">
        <div className="section-heading">
          <div>
            <p>Preview tecnico</p>
            <h2>Probar con hoja de campo existente</h2>
          </div>
          <div className="toolbar-actions">
            <select value={selectedFieldSheetId} onChange={(event) => setSelectedFieldSheetId(event.target.value)}>
              <option value="">Selecciona hoja</option>
              {fieldSheets.map((item) => (
                <option key={item.id} value={item.id}>#{item.id} OT {item.work_order_number ?? '-'} - {item.status}</option>
              ))}
            </select>
            <button className="primary-button" type="button" onClick={runPreview}>Generar preview</button>
          </div>
        </div>
        {preview ? (
          <pre className="json-preview">{JSON.stringify(preview, null, 2)}</pre>
        ) : (
          <div className="clients-empty">Sin preview generado.</div>
        )}
      </section>
    </section>
  );
}
