import { Plus, Ruler, Trash2 } from 'lucide-react';
import React, { useEffect, useMemo, useState } from 'react';

import ConfirmDialog from '../components/ConfirmDialog.jsx';
import {
  emptyReferenceStandardForm,
  emptyReferenceStandardUncertaintyForm
} from '../constants/forms.js';
import { referenceStandardStatusLabels } from '../constants/statuses.js';
import {
  createReferenceStandard,
  createReferenceStandardUncertainty,
  deleteReferenceStandard,
  deleteReferenceStandardUncertainty,
  listReferenceStandards,
  updateReferenceStandard,
  updateReferenceStandardUncertainty
} from '../services/api.js';
import useConfirmDialog from '../utils/useConfirmDialog.js';
import { formatDate, formatDateTime } from '../utils/formatters.js';

function mapStandardPayload(form) {
  return {
    internal_code: form.internalCode.trim(),
    name: form.name.trim(),
    description: form.description.trim() || null,
    owner_company: form.ownerCompany,
    magnitude: form.magnitude.trim(),
    brand: form.brand.trim() || null,
    model: form.model.trim() || null,
    serial_number: form.serialNumber.trim() || null,
    identification: form.identification.trim() || null,
    unit: form.unit.trim() || null,
    range_min: form.rangeMin === '' ? null : Number(form.rangeMin),
    range_max: form.rangeMax === '' ? null : Number(form.rangeMax),
    resolution: form.resolution === '' ? null : Number(form.resolution),
    coverage_factor_k: form.coverageFactorK === '' ? null : Number(form.coverageFactorK),
    provider: form.provider.trim() || null,
    calibration_laboratory: form.calibrationLaboratory.trim() || null,
    certificate_number: form.certificateNumber.trim() || null,
    certificate_file_path: form.certificateFilePath.trim() || null,
    calibrated_on: form.calibratedOn || null,
    next_calibration_on: form.nextCalibrationOn || null,
    status: form.status,
    notes: form.notes.trim() || null
  };
}

function mapUncertaintyPayload(form) {
  return {
    range_min: form.rangeMin === '' ? null : Number(form.rangeMin),
    range_max: form.rangeMax === '' ? null : Number(form.rangeMax),
    unit: form.unit.trim() || null,
    uncertainty_value: Number(form.uncertaintyValue),
    coverage_factor_k: form.coverageFactorK === '' ? null : Number(form.coverageFactorK),
    distribution: form.distribution.trim() || null,
    notes: form.notes.trim() || null
  };
}

function StandardsPage() {
  const [standards, setStandards] = useState([]);
  const [activeTab, setActiveTab] = useState('all');
  const [selectedStandard, setSelectedStandard] = useState(null);
  const [standardForm, setStandardForm] = useState(emptyReferenceStandardForm);
  const [uncertaintyForm, setUncertaintyForm] = useState(emptyReferenceStandardUncertaintyForm);
  const [editingUncertaintyId, setEditingUncertaintyId] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const { confirmDialog, openConfirm, closeConfirm, handleConfirm } = useConfirmDialog();

  const displayedStandards = useMemo(() => {
    if (activeTab === 'expired') {
      return standards.filter((item) => item.effective_status === 'expired');
    }
    if (activeTab === 'inactive') {
      return standards.filter((item) => item.status === 'inactive' || item.status === 'out_of_service');
    }
    return standards;
  }, [activeTab, standards]);

  async function loadStandards() {
    setError('');
    setIsLoading(true);
    try {
      const result = await listReferenceStandards();
      setStandards(Array.isArray(result) ? result : []);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    loadStandards();
  }, []);

  function openCreateModal() {
    setSelectedStandard(null);
    setStandardForm(emptyReferenceStandardForm);
    setUncertaintyForm(emptyReferenceStandardUncertaintyForm);
    setEditingUncertaintyId(null);
    setIsModalOpen(true);
    setError('');
    setNotice('');
  }

  function openEditModal(standard) {
    setSelectedStandard(standard);
    setStandardForm({
      internalCode: standard.internal_code ?? '',
      name: standard.name ?? '',
      description: standard.description ?? '',
      ownerCompany: standard.owner_company ?? 'MYC',
      magnitude: standard.magnitude ?? '',
      brand: standard.brand ?? '',
      model: standard.model ?? '',
      serialNumber: standard.serial_number ?? '',
      identification: standard.identification ?? '',
      unit: standard.unit ?? '',
      rangeMin: standard.range_min ?? '',
      rangeMax: standard.range_max ?? '',
      resolution: standard.resolution ?? '',
      coverageFactorK: standard.coverage_factor_k ?? '2',
      provider: standard.provider ?? '',
      calibrationLaboratory: standard.calibration_laboratory ?? '',
      certificateNumber: standard.certificate_number ?? '',
      certificateFilePath: standard.certificate_file_path ?? '',
      calibratedOn: standard.calibrated_on ?? '',
      nextCalibrationOn: standard.next_calibration_on ?? '',
      status: standard.status ?? 'active',
      notes: standard.notes ?? ''
    });
    setUncertaintyForm(emptyReferenceStandardUncertaintyForm);
    setEditingUncertaintyId(null);
    setIsModalOpen(true);
    setError('');
    setNotice('');
  }

  function closeModal() {
    setIsModalOpen(false);
    setSelectedStandard(null);
    setStandardForm(emptyReferenceStandardForm);
    setUncertaintyForm(emptyReferenceStandardUncertaintyForm);
    setEditingUncertaintyId(null);
  }

  async function handleSaveStandard(event) {
    event.preventDefault();
    if (!standardForm.internalCode.trim() || !standardForm.name.trim() || !standardForm.magnitude.trim()) {
      setError('Captura clave interna, nombre y magnitud.');
      return;
    }
    setIsSaving(true);
    setError('');
    setNotice('');
    try {
      const payload = mapStandardPayload(standardForm);
      const saved = selectedStandard
        ? await updateReferenceStandard(selectedStandard.id, payload)
        : await createReferenceStandard(payload);
      setNotice(selectedStandard ? 'Patron actualizado' : 'Patron creado');
      closeModal();
      await loadStandards();
      if (saved?.id) {
        setSelectedStandard(saved);
      }
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsSaving(false);
    }
  }

  function startEditUncertainty(item) {
    setEditingUncertaintyId(item.id);
    setUncertaintyForm({
      rangeMin: item.range_min ?? '',
      rangeMax: item.range_max ?? '',
      unit: item.unit ?? '',
      uncertaintyValue: item.uncertainty_value ?? '',
      coverageFactorK: item.coverage_factor_k ?? '2',
      distribution: item.distribution ?? '',
      notes: item.notes ?? ''
    });
  }

  async function handleSaveUncertainty(event) {
    event.preventDefault();
    if (!selectedStandard) {
      setError('Guarda primero el patron para poder agregar incertidumbres.');
      return;
    }
    if (!uncertaintyForm.uncertaintyValue) {
      setError('Captura la incertidumbre.');
      return;
    }
    setIsSaving(true);
    setError('');
    try {
      const payload = mapUncertaintyPayload(uncertaintyForm);
      const saved = editingUncertaintyId
        ? await updateReferenceStandardUncertainty(selectedStandard.id, editingUncertaintyId, payload)
        : await createReferenceStandardUncertainty(selectedStandard.id, payload);
      setStandards((current) => current.map((item) => (item.id === saved.id ? saved : item)));
      setSelectedStandard(saved);
      setUncertaintyForm(emptyReferenceStandardUncertaintyForm);
      setEditingUncertaintyId(null);
      setNotice(editingUncertaintyId ? 'Incertidumbre actualizada' : 'Incertidumbre agregada');
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsSaving(false);
    }
  }

  function handleDeleteStandard(standard) {
    openConfirm({
      title: 'Dar de baja patron',
      message: `Se dará de baja el patron ${standard.internal_code}.`,
      confirmText: 'Dar de baja',
      variant: 'danger',
      onConfirm: async () => {
        setError('');
        setNotice('');
        try {
          await deleteReferenceStandard(standard.id);
          setNotice('Patron dado de baja');
          await loadStandards();
          if (selectedStandard?.id === standard.id) {
            closeModal();
          }
        } catch (requestError) {
          setError(requestError.message);
        }
      }
    });
  }

  function handleDeleteUncertainty(uncertainty) {
    if (!selectedStandard) return;
    openConfirm({
      title: 'Dar de baja incertidumbre',
      message: 'Se desactivará este rango de incertidumbre.',
      confirmText: 'Desactivar',
      variant: 'danger',
      onConfirm: async () => {
        setError('');
        try {
          const saved = await deleteReferenceStandardUncertainty(selectedStandard.id, uncertainty.id);
          setStandards((current) => current.map((item) => (item.id === saved.id ? saved : item)));
          setSelectedStandard(saved);
          setNotice('Incertidumbre desactivada');
        } catch (requestError) {
          setError(requestError.message);
        }
      }
    });
  }

  const currentStandard = standards.find((item) => item.id === selectedStandard?.id) ?? selectedStandard;

  return (
    <section className="module-workspace service-orders-workspace">
      <div className="module-workspace__hero clients-hero">
        <span className="module-workspace__icon">
          <Ruler size={28} />
        </span>
        <div>
          <p>Trazabilidad metrologica</p>
          <h1>Patrones</h1>
          <span>Gestion de equipos patron, vigencias y rangos de incertidumbre reutilizables.</span>
        </div>
      </div>

      {error ? <div className="form-error dashboard-error">{error}</div> : null}
      {notice ? <div className="form-notice dashboard-error">{notice}</div> : null}

      <section className="operations-band certificates-summary">
        <div className="operations-band__metric">
          <strong>{isLoading ? '-' : standards.length}</strong>
          <span>Total patrones</span>
        </div>
        <div className="operations-band__metric">
          <strong>{isLoading ? '-' : standards.filter((item) => item.effective_status === 'expired').length}</strong>
          <span>Vencidos</span>
        </div>
        <div className="operations-band__metric">
          <strong>{isLoading ? '-' : standards.filter((item) => item.effective_status === 'active').length}</strong>
          <span>Activos vigentes</span>
        </div>
      </section>

      <div className="module-tabs" role="tablist" aria-label="Vista de patrones">
        {[
          ['all', 'Todos'],
          ['expired', 'Vencidos'],
          ['inactive', 'Inactivos']
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
            <p>Catalogo de patrones</p>
            <h2>{isLoading ? 'Cargando...' : `${displayedStandards.length} registros`}</h2>
          </div>
          <div className="toolbar-actions">
            <button className="primary-button" type="button" onClick={openCreateModal}>
              <Plus size={16} />
              Nuevo patron
            </button>
          </div>
        </div>
        <div className="clients-table certificates-table" aria-busy={isLoading}>
          <div className="clients-table__head">
            <span>Clave</span>
            <span>Patron</span>
            <span>Magnitud</span>
            <span>Empresa</span>
            <span>Rango</span>
            <span>Proxima calibracion</span>
            <span>Estado</span>
            <span>Acciones</span>
          </div>
          {isLoading ? (
            <div className="clients-empty">Cargando patrones...</div>
          ) : displayedStandards.length ? (
            displayedStandards.map((item) => (
              <div className="clients-table__row" key={item.id}>
                <span><strong>{item.internal_code}</strong></span>
                <span>
                  <strong>{item.name}</strong>
                  <br />
                  <small>{[item.brand, item.model, item.serial_number].filter(Boolean).join(' / ') || 'Sin datos'}</small>
                </span>
                <span>{item.magnitude}</span>
                <span>{item.owner_company}</span>
                <span>{[item.range_min, item.range_max, item.unit].filter((value) => value !== null && value !== '').join(' / ') || '-'}</span>
                <span>{formatDate(item.next_calibration_on)}</span>
                <span>
                  <mark className={`quotation-status status-${item.effective_status}`}>
                    {referenceStandardStatusLabels[item.effective_status] ?? item.effective_status}
                  </mark>
                </span>
                <span className="table-actions">
                  <button className="table-button" type="button" onClick={() => openEditModal(item)}>
                    Abrir
                  </button>
                  <button className="table-button table-button--danger" type="button" onClick={() => handleDeleteStandard(item)}>
                    Baja
                  </button>
                </span>
              </div>
            ))
          ) : (
            <div className="clients-empty">No hay patrones en esta vista.</div>
          )}
        </div>
      </section>

      {isModalOpen ? (
        <div className="modal-overlay" role="presentation" onClick={closeModal}>
          <section className="detail-modal certificate-modal" role="dialog" aria-modal="true" onClick={(event) => event.stopPropagation()}>
            <button className="detail-modal__close" onClick={closeModal} type="button" aria-label="Cerrar">
              <Trash2 size={18} />
            </button>
            <div className="detail-modal__header">
              <div>
                <p>{currentStandard ? currentStandard.internal_code : 'Nuevo patron'}</p>
                <h2>{currentStandard ? currentStandard.name : 'Alta de patron'}</h2>
              </div>
            </div>

            <form className="field-sheet-form-grid" onSubmit={handleSaveStandard}>
              {[
                ['internalCode', 'Clave interna'],
                ['name', 'Nombre'],
                ['magnitude', 'Magnitud'],
                ['brand', 'Marca'],
                ['model', 'Modelo'],
                ['serialNumber', 'Serie'],
                ['identification', 'Identificacion'],
                ['unit', 'Unidad'],
                ['rangeMin', 'Rango minimo'],
                ['rangeMax', 'Rango maximo'],
                ['resolution', 'Resolucion'],
                ['coverageFactorK', 'Factor k'],
                ['provider', 'Proveedor'],
                ['calibrationLaboratory', 'Laboratorio'],
                ['certificateNumber', 'No. certificado'],
                ['certificateFilePath', 'Ruta certificado']
              ].map(([key, label]) => (
                <label key={key}>
                  {label}
                  <input
                    type="text"
                    value={standardForm[key]}
                    onChange={(event) => setStandardForm((current) => ({ ...current, [key]: event.target.value }))}
                  />
                </label>
              ))}
              <label>
                Empresa
                <select value={standardForm.ownerCompany} onChange={(event) => setStandardForm((current) => ({ ...current, ownerCompany: event.target.value }))}>
                  <option value="MYC">MYC</option>
                  <option value="Capimet">Capimet</option>
                  <option value="Otro">Otro</option>
                </select>
              </label>
              <label>
                Estado
                <select value={standardForm.status} onChange={(event) => setStandardForm((current) => ({ ...current, status: event.target.value }))}>
                  <option value="active">Activo</option>
                  <option value="expired">Vencido</option>
                  <option value="out_of_service">Fuera de servicio</option>
                  <option value="inactive">Inactivo</option>
                </select>
              </label>
              <label>
                Fecha calibracion
                <input type="date" value={standardForm.calibratedOn} onChange={(event) => setStandardForm((current) => ({ ...current, calibratedOn: event.target.value }))} />
              </label>
              <label>
                Proxima calibracion
                <input type="date" value={standardForm.nextCalibrationOn} onChange={(event) => setStandardForm((current) => ({ ...current, nextCalibrationOn: event.target.value }))} />
              </label>
              <label className="form-field--wide">
                Descripcion
                <textarea rows={3} value={standardForm.description} onChange={(event) => setStandardForm((current) => ({ ...current, description: event.target.value }))} />
              </label>
              <label className="form-field--wide">
                Notas
                <textarea rows={3} value={standardForm.notes} onChange={(event) => setStandardForm((current) => ({ ...current, notes: event.target.value }))} />
              </label>
              <div className="quotation-detail-save">
                <div className="toolbar-actions">
                  <button className="table-button" type="button" onClick={closeModal}>Cancelar</button>
                  <button className="primary-button" type="submit" disabled={isSaving}>
                    {selectedStandard ? 'Guardar cambios' : 'Crear patron'}
                  </button>
                </div>
              </div>
            </form>

            {currentStandard?.id ? (
              <section className="quotation-section">
                <div className="quotation-section__title">
                  <p>Incertidumbres por rango</p>
                  <h3>Bloques activos</h3>
                </div>
                <form className="field-sheet-form-grid" onSubmit={handleSaveUncertainty}>
                  <label>
                    Rango minimo
                    <input type="text" value={uncertaintyForm.rangeMin} onChange={(event) => setUncertaintyForm((current) => ({ ...current, rangeMin: event.target.value }))} />
                  </label>
                  <label>
                    Rango maximo
                    <input type="text" value={uncertaintyForm.rangeMax} onChange={(event) => setUncertaintyForm((current) => ({ ...current, rangeMax: event.target.value }))} />
                  </label>
                  <label>
                    Unidad
                    <input type="text" value={uncertaintyForm.unit} onChange={(event) => setUncertaintyForm((current) => ({ ...current, unit: event.target.value }))} />
                  </label>
                  <label>
                    Incertidumbre
                    <input type="text" value={uncertaintyForm.uncertaintyValue} onChange={(event) => setUncertaintyForm((current) => ({ ...current, uncertaintyValue: event.target.value }))} />
                  </label>
                  <label>
                    Factor k
                    <input type="text" value={uncertaintyForm.coverageFactorK} onChange={(event) => setUncertaintyForm((current) => ({ ...current, coverageFactorK: event.target.value }))} />
                  </label>
                  <label>
                    Distribucion
                    <input type="text" value={uncertaintyForm.distribution} onChange={(event) => setUncertaintyForm((current) => ({ ...current, distribution: event.target.value }))} />
                  </label>
                  <label className="form-field--wide">
                    Notas
                    <textarea rows={2} value={uncertaintyForm.notes} onChange={(event) => setUncertaintyForm((current) => ({ ...current, notes: event.target.value }))} />
                  </label>
                  <div className="quotation-detail-save">
                    <div className="toolbar-actions">
                      {editingUncertaintyId ? (
                        <button className="table-button" type="button" onClick={() => {
                          setEditingUncertaintyId(null);
                          setUncertaintyForm(emptyReferenceStandardUncertaintyForm);
                        }}>
                          Cancelar edicion
                        </button>
                      ) : null}
                      <button className="primary-button" type="submit" disabled={isSaving}>
                        {editingUncertaintyId ? 'Guardar incertidumbre' : 'Agregar incertidumbre'}
                      </button>
                    </div>
                  </div>
                </form>
                <div className="clients-table certificates-table">
                  <div className="clients-table__head">
                    <span>Rango</span>
                    <span>Unidad</span>
                    <span>Incertidumbre</span>
                    <span>k</span>
                    <span>Distribucion</span>
                    <span>Acciones</span>
                  </div>
                  {(currentStandard.uncertainties ?? []).filter((item) => item.is_active !== false).length ? (
                    currentStandard.uncertainties
                      .filter((item) => item.is_active !== false)
                      .map((item) => (
                        <div className="clients-table__row" key={item.id}>
                          <span>{[item.range_min, item.range_max].filter((value) => value !== null && value !== '').join(' a ') || 'Abierto'}</span>
                          <span>{item.unit || '-'}</span>
                          <span>{item.uncertainty_value}</span>
                          <span>{item.coverage_factor_k || '-'}</span>
                          <span>{item.distribution || '-'}</span>
                          <span className="table-actions">
                            <button className="table-button" type="button" onClick={() => startEditUncertainty(item)}>Editar</button>
                            <button className="table-button table-button--danger" type="button" onClick={() => handleDeleteUncertainty(item)}>Baja</button>
                          </span>
                        </div>
                      ))
                  ) : (
                    <div className="clients-empty">No hay incertidumbres activas para este patron.</div>
                  )}
                </div>
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

export default StandardsPage;
