import { FlaskConical, Plus } from 'lucide-react';
import React, { useEffect, useMemo, useState } from 'react';

import ConfirmDialog from '../components/ConfirmDialog.jsx';
import ActivityPanel from '../components/activity/ActivityPanel.jsx';
import { emptyCalibrationProcedureForm } from '../constants/forms.js';
import { calibrationProcedureStatusLabels } from '../constants/statuses.js';
import {
  createCalibrationProcedure,
  deleteCalibrationProcedure,
  listCalibrationProcedures,
  listMetrologyProfiles,
  listUncertaintyModels,
  listUncertaintyModelVersions,
  updateCalibrationProcedure
} from '../services/api.js';
import useConfirmDialog from '../utils/useConfirmDialog.js';
import { formatDateTime } from '../utils/formatters.js';

function mapProcedurePayload(form) {
  return {
    code: form.code.trim(),
    name: form.name.trim(),
    description: form.description.trim() || null,
    magnitude: form.magnitude.trim(),
    profile_key: form.profileKey || null,
    uncertainty_model_id: form.uncertaintyModelId === '' ? null : Number(form.uncertaintyModelId),
    uncertainty_model_version_id: form.uncertaintyModelVersionId === '' ? null : Number(form.uncertaintyModelVersionId),
    version: form.version.trim(),
    issuer_company: form.issuerCompany,
    certificate_type: form.certificateType,
    required_readings: form.requiredReadings === '' ? null : Number(form.requiredReadings),
    decision_rule: form.decisionRule.trim() || null,
    acceptance_criteria: form.acceptanceCriteria.trim() || null,
    notes: form.notes.trim() || null,
    status: form.status
  };
}

function ProceduresPage() {
  const [procedures, setProcedures] = useState([]);
  const [profiles, setProfiles] = useState([]);
  const [uncertaintyModels, setUncertaintyModels] = useState([]);
  const [uncertaintyVersions, setUncertaintyVersions] = useState([]);
  const [activeTab, setActiveTab] = useState('all');
  const [selectedProcedure, setSelectedProcedure] = useState(null);
  const [procedureForm, setProcedureForm] = useState(emptyCalibrationProcedureForm);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const { confirmDialog, openConfirm, closeConfirm, handleConfirm } = useConfirmDialog();

  const displayedProcedures = useMemo(() => {
    if (activeTab === 'active') return procedures.filter((item) => item.status === 'active');
    if (activeTab === 'draft') return procedures.filter((item) => item.status === 'draft');
    if (activeTab === 'obsolete') return procedures.filter((item) => ['obsolete', 'inactive'].includes(item.status));
    return procedures;
  }, [activeTab, procedures]);

  async function loadData() {
    setError('');
    setIsLoading(true);
    try {
      const [proceduresResult, profilesResult] = await Promise.all([
        listCalibrationProcedures(),
        listMetrologyProfiles()
      ]);
      setProcedures(Array.isArray(proceduresResult) ? proceduresResult : []);
      setProfiles(Array.isArray(profilesResult) ? profilesResult : []);
      const modelsResult = await listUncertaintyModels();
      setUncertaintyModels(Array.isArray(modelsResult) ? modelsResult : []);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  function openCreateModal() {
    setSelectedProcedure(null);
    setProcedureForm(emptyCalibrationProcedureForm);
    setIsModalOpen(true);
    setError('');
    setNotice('');
  }

  function openEditModal(item) {
    setSelectedProcedure(item);
    setProcedureForm({
      code: item.code ?? '',
      name: item.name ?? '',
      description: item.description ?? '',
      magnitude: item.magnitude ?? '',
      profileKey: item.profile_key ?? '',
      uncertaintyModelId: item.uncertainty_model_id ?? '',
      uncertaintyModelVersionId: item.uncertainty_model_version_id ?? '',
      version: item.version ?? '1.0',
      issuerCompany: item.issuer_company ?? 'MYC',
      certificateType: item.certificate_type ?? 'trazable',
      requiredReadings: item.required_readings ?? '',
      decisionRule: item.decision_rule ?? '',
      acceptanceCriteria: item.acceptance_criteria ?? '',
      notes: item.notes ?? '',
      status: item.status ?? 'draft'
    });
    setIsModalOpen(true);
    setError('');
    setNotice('');
  }

  useEffect(() => {
    async function loadVersions() {
      const modelId = procedureForm.uncertaintyModelId;
      if (!modelId) {
        setUncertaintyVersions([]);
        return;
      }
      try {
        const versions = await listUncertaintyModelVersions(modelId);
        setUncertaintyVersions(Array.isArray(versions) ? versions : []);
      } catch (requestError) {
        setError(requestError.message);
      }
    }
    loadVersions();
  }, [procedureForm.uncertaintyModelId]);

  function closeModal() {
    setIsModalOpen(false);
    setSelectedProcedure(null);
    setProcedureForm(emptyCalibrationProcedureForm);
  }

  async function handleSaveProcedure(event) {
    event.preventDefault();
    if (!procedureForm.code.trim() || !procedureForm.name.trim() || !procedureForm.magnitude.trim()) {
      setError('Captura codigo, nombre y magnitud.');
      return;
    }
    setIsSaving(true);
    setError('');
    try {
      const payload = mapProcedurePayload(procedureForm);
      await (selectedProcedure
        ? updateCalibrationProcedure(selectedProcedure.id, payload)
        : createCalibrationProcedure(payload));
      setNotice(selectedProcedure ? 'Procedimiento actualizado' : 'Procedimiento creado');
      closeModal();
      await loadData();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsSaving(false);
    }
  }

  function handleDeleteProcedure(item) {
    openConfirm({
      title: 'Dar de baja procedimiento',
      message: `Se dará de baja el procedimiento ${item.code} ${item.version}.`,
      confirmText: 'Dar de baja',
      variant: 'danger',
      onConfirm: async () => {
        setError('');
        try {
          await deleteCalibrationProcedure(item.id);
          setNotice('Procedimiento dado de baja');
          await loadData();
          if (selectedProcedure?.id === item.id) {
            closeModal();
          }
        } catch (requestError) {
          setError(requestError.message);
        }
      }
    });
  }

  return (
    <section className="module-workspace service-orders-workspace">
      <div className="module-workspace__hero clients-hero">
        <span className="module-workspace__icon">
          <FlaskConical size={28} />
        </span>
        <div>
          <p>Base tecnica</p>
          <h1>Procedimientos</h1>
          <span>Versionado de procedimientos de calibracion, perfiles y reglas operativas.</span>
        </div>
      </div>

      {error ? <div className="form-error dashboard-error">{error}</div> : null}
      {notice ? <div className="form-notice dashboard-error">{notice}</div> : null}

      <section className="operations-band certificates-summary">
        <div className="operations-band__metric">
          <strong>{isLoading ? '-' : procedures.length}</strong>
          <span>Total procedimientos</span>
        </div>
        <div className="operations-band__metric">
          <strong>{isLoading ? '-' : procedures.filter((item) => item.status === 'active').length}</strong>
          <span>Activos</span>
        </div>
        <div className="operations-band__metric">
          <strong>{isLoading ? '-' : procedures.filter((item) => item.status === 'draft').length}</strong>
          <span>Borrador</span>
        </div>
      </section>

      <div className="module-tabs" role="tablist" aria-label="Vista de procedimientos">
        {[
          ['all', 'Todos'],
          ['active', 'Activos'],
          ['draft', 'Borrador'],
          ['obsolete', 'Inactivos / obsoletos']
        ].map(([key, label]) => (
          <button
            key={key}
            type="button"
            aria-selected={activeTab === key}
            className={activeTab === key ? 'module-tab is-active' : 'module-tab'}
            onClick={() => setActiveTab(key)}
          >
            {label}
          </button>
        ))}
      </div>

      <section className="clients-list-panel">
        <div className="section-heading">
          <div>
            <p>Listado de procedimientos</p>
            <h2>{isLoading ? 'Cargando...' : `${displayedProcedures.length} procedimientos`}</h2>
          </div>
          <div className="toolbar-actions">
            <button className="primary-button" type="button" onClick={openCreateModal}>
              <Plus size={16} />
              Nuevo procedimiento
            </button>
          </div>
        </div>
        <div className="clients-table certificates-table">
          <div className="clients-table__head">
            <span>Codigo</span>
            <span>Nombre</span>
            <span>Magnitud</span>
            <span>Perfil</span>
            <span>Incertidumbre</span>
            <span>Certificado</span>
            <span>Estado</span>
            <span>Actualizado</span>
            <span>Acciones</span>
          </div>
          {isLoading ? (
            <div className="clients-empty">Cargando procedimientos...</div>
          ) : displayedProcedures.length ? (
            displayedProcedures.map((item) => (
              <div className="clients-table__row" key={item.id}>
                <span><strong>{item.code}</strong><br /><small>v{item.version}</small></span>
                <span>{item.name}</span>
                <span>{item.magnitude}</span>
                <span>{item.profile_key || '-'}</span>
                <span>{item.uncertainty_model_version_id ? `Version #${item.uncertainty_model_version_id}` : (item.uncertainty_model_id ? `Modelo #${item.uncertainty_model_id}` : '-')}</span>
                <span>{item.certificate_type}</span>
                <span>
                  <mark className={`quotation-status status-${item.status}`}>
                    {calibrationProcedureStatusLabels[item.status] ?? item.status}
                  </mark>
                </span>
                <span>{formatDateTime(item.updated_at)}</span>
                <span className="table-actions">
                  <button className="table-button" type="button" onClick={() => openEditModal(item)}>
                    Abrir
                  </button>
                  <button className="table-button table-button--danger" type="button" onClick={() => handleDeleteProcedure(item)}>
                    Baja
                  </button>
                </span>
              </div>
            ))
          ) : (
            <div className="clients-empty">No hay procedimientos en esta vista.</div>
          )}
        </div>
      </section>

      {isModalOpen ? (
        <div className="modal-overlay" role="presentation" onClick={closeModal}>
          <section className="detail-modal certificate-modal" role="dialog" aria-modal="true" onClick={(event) => event.stopPropagation()}>
            <div className="detail-modal__header">
              <div>
                <p>{selectedProcedure ? `${selectedProcedure.code} v${selectedProcedure.version}` : 'Nuevo procedimiento'}</p>
                <h2>{selectedProcedure ? selectedProcedure.name : 'Alta de procedimiento'}</h2>
              </div>
            </div>
            <form className="field-sheet-form-grid" onSubmit={handleSaveProcedure}>
              {[
                ['code', 'Codigo'],
                ['name', 'Nombre'],
                ['magnitude', 'Magnitud'],
                ['version', 'Version'],
                ['requiredReadings', 'Lecturas requeridas']
              ].map(([key, label]) => (
                <label key={key}>
                  {label}
                  <input
                    type="text"
                    value={procedureForm[key]}
                    onChange={(event) => setProcedureForm((current) => ({ ...current, [key]: event.target.value }))}
                  />
                </label>
              ))}
              <label>
                Perfil metrologico
                <select value={procedureForm.profileKey} onChange={(event) => setProcedureForm((current) => ({ ...current, profileKey: event.target.value }))}>
                  <option value="">Sin perfil</option>
                  {profiles.map((profile) => (
                    <option key={profile.profile_key} value={profile.profile_key}>
                      {profile.display_name} · {profile.profile_key}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Modelo de incertidumbre
                <select
                  value={procedureForm.uncertaintyModelId}
                  onChange={(event) => setProcedureForm((current) => ({
                    ...current,
                    uncertaintyModelId: event.target.value,
                    uncertaintyModelVersionId: ''
                  }))}
                >
                  <option value="">Sin modelo</option>
                  {uncertaintyModels.map((model) => (
                    <option key={model.id} value={model.id}>
                      {model.code} · {model.name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Version aprobada
                <select
                  value={procedureForm.uncertaintyModelVersionId}
                  onChange={(event) => setProcedureForm((current) => ({ ...current, uncertaintyModelVersionId: event.target.value }))}
                >
                  <option value="">Resolver automaticamente</option>
                  {uncertaintyVersions
                    .filter((version) => version.status === 'approved')
                    .map((version) => (
                      <option key={version.id} value={version.id}>
                        v{version.version_number} · {version.status}
                      </option>
                    ))}
                </select>
              </label>
              <label>
                Empresa emisora
                <select value={procedureForm.issuerCompany} onChange={(event) => setProcedureForm((current) => ({ ...current, issuerCompany: event.target.value }))}>
                  <option value="MYC">MYC</option>
                  <option value="Capimet">Capimet</option>
                  <option value="Otro">Otro</option>
                </select>
              </label>
              <label>
                Tipo certificado
                <select value={procedureForm.certificateType} onChange={(event) => setProcedureForm((current) => ({ ...current, certificateType: event.target.value }))}>
                  <option value="acreditado">Acreditado</option>
                  <option value="trazable">Trazable</option>
                  <option value="verificacion">Verificacion</option>
                  <option value="inspeccion">Inspeccion</option>
                  <option value="otro">Otro</option>
                </select>
              </label>
              <label>
                Estado
                <select value={procedureForm.status} onChange={(event) => setProcedureForm((current) => ({ ...current, status: event.target.value }))}>
                  <option value="draft">Borrador</option>
                  <option value="active">Activo</option>
                  <option value="inactive">Inactivo</option>
                  <option value="obsolete">Obsoleto</option>
                </select>
              </label>
              <label className="form-field--wide">
                Descripcion
                <textarea rows={3} value={procedureForm.description} onChange={(event) => setProcedureForm((current) => ({ ...current, description: event.target.value }))} />
              </label>
              <label className="form-field--wide">
                Regla de decision
                <textarea rows={3} value={procedureForm.decisionRule} onChange={(event) => setProcedureForm((current) => ({ ...current, decisionRule: event.target.value }))} />
              </label>
              <label className="form-field--wide">
                Criterio de aceptacion
                <textarea rows={3} value={procedureForm.acceptanceCriteria} onChange={(event) => setProcedureForm((current) => ({ ...current, acceptanceCriteria: event.target.value }))} />
              </label>
              <label className="form-field--wide">
                Notas
                <textarea rows={3} value={procedureForm.notes} onChange={(event) => setProcedureForm((current) => ({ ...current, notes: event.target.value }))} />
              </label>
              <div className="quotation-detail-save">
                <div className="toolbar-actions">
                  <button className="table-button" type="button" onClick={closeModal}>Cancelar</button>
                  <button className="primary-button" type="submit" disabled={isSaving}>
                    {selectedProcedure ? 'Guardar cambios' : 'Crear procedimiento'}
                  </button>
                </div>
              </div>
            </form>
            {selectedProcedure?.id ? (
              <section className="quotation-section">
                <div className="quotation-section__title">
                  <p>Comunicación interna</p>
                  <h3>Actividad del procedimiento</h3>
                </div>
                <ActivityPanel
                  entityId={selectedProcedure.id}
                  entityType="calibration_procedure"
                />
              </section>
            ) : null}
          </section>
        </div>
      ) : null}

      <ConfirmDialog
        {...confirmDialog}
        isOpen={confirmDialog.isOpen}
        onClose={closeConfirm}
        onConfirm={handleConfirm}
      />
    </section>
  );
}

export default ProceduresPage;
