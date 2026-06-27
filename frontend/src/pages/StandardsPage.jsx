import { Plus, Ruler, X } from 'lucide-react';
import React, { useEffect, useMemo, useState } from 'react';

import ConfirmDialog from '../components/ConfirmDialog.jsx';
import {
  emptyReferenceStandardForm,
  emptyReferenceStandardUncertaintyForm
} from '../constants/forms.js';
import { referenceStandardStatusLabels } from '../constants/statuses.js';
import {
  activateReferenceStandardCertificate,
  createReferenceStandard,
  createReferenceStandardCertificate,
  createReferenceStandardCertificateUncertainty,
  createReferenceStandardUncertainty,
  deleteReferenceStandard,
  deleteReferenceStandardCertificateUncertainty,
  deleteReferenceStandardUncertainty,
  listReferenceStandardCertificates,
  listReferenceStandards,
  suspendReferenceStandardCertificate,
  updateReferenceStandard,
  updateReferenceStandardCertificate,
  updateReferenceStandardCertificateUncertainty,
  updateReferenceStandardUncertainty
} from '../services/api.js';
import { formatDate, formatDateTime } from '../utils/formatters.js';
import useConfirmDialog from '../utils/useConfirmDialog.js';

const emptyCertificateForm = {
  id: null,
  certificateNumber: '',
  issuingLaboratory: '',
  accreditationBody: '',
  accreditationNumber: '',
  calibrationDate: '',
  expirationDate: '',
  receivedDate: '',
  status: 'draft',
  traceabilityStatement: '',
  environmentalConditions: '',
  notes: ''
};

const emptyCertificateUncertaintyForm = {
  certificateId: '',
  id: null,
  magnitude: '',
  measurementType: '',
  rangeMin: '',
  rangeMax: '',
  unit: '',
  uncertaintyValue: '',
  uncertaintyUnit: '',
  kFactor: '2',
  confidenceLevel: '',
  distribution: '',
  formulaReference: '',
  notes: ''
};

function normalizeText(value) {
  return typeof value === 'string' ? value.trim() : value;
}

function mapStandardPayload(form) {
  return {
    internal_code: normalizeText(form.internalCode),
    name: normalizeText(form.name),
    description: normalizeText(form.description) || null,
    owner_company: form.ownerCompany,
    magnitude: normalizeText(form.magnitude),
    brand: normalizeText(form.brand) || null,
    model: normalizeText(form.model) || null,
    serial_number: normalizeText(form.serialNumber) || null,
    identification: normalizeText(form.identification) || null,
    unit: normalizeText(form.unit) || null,
    range_min: form.rangeMin === '' ? null : Number(form.rangeMin),
    range_max: form.rangeMax === '' ? null : Number(form.rangeMax),
    resolution: form.resolution === '' ? null : Number(form.resolution),
    coverage_factor_k: form.coverageFactorK === '' ? null : Number(form.coverageFactorK),
    provider: normalizeText(form.provider) || null,
    calibration_laboratory: normalizeText(form.calibrationLaboratory) || null,
    certificate_number: normalizeText(form.certificateNumber) || null,
    certificate_file_path: normalizeText(form.certificateFilePath) || null,
    calibrated_on: form.calibratedOn || null,
    next_calibration_on: form.nextCalibrationOn || null,
    status: form.status,
    notes: normalizeText(form.notes) || null
  };
}

function mapUncertaintyPayload(form) {
  return {
    range_min: form.rangeMin === '' ? null : Number(form.rangeMin),
    range_max: form.rangeMax === '' ? null : Number(form.rangeMax),
    unit: normalizeText(form.unit) || null,
    uncertainty_value: Number(form.uncertaintyValue),
    coverage_factor_k: form.coverageFactorK === '' ? null : Number(form.coverageFactorK),
    distribution: normalizeText(form.distribution) || null,
    notes: normalizeText(form.notes) || null
  };
}

function mapCertificatePayload(form) {
  return {
    certificate_number: normalizeText(form.certificateNumber),
    issuing_laboratory: normalizeText(form.issuingLaboratory) || null,
    accreditation_body: normalizeText(form.accreditationBody) || null,
    accreditation_number: normalizeText(form.accreditationNumber) || null,
    calibration_date: form.calibrationDate || null,
    expiration_date: form.expirationDate || null,
    received_date: form.receivedDate || null,
    status: form.status,
    traceability_statement: normalizeText(form.traceabilityStatement) || null,
    environmental_conditions: normalizeText(form.environmentalConditions) || null,
    notes: normalizeText(form.notes) || null,
    uncertainties: []
  };
}

function mapCertificateUncertaintyPayload(form) {
  return {
    magnitude: normalizeText(form.magnitude) || null,
    measurement_type: normalizeText(form.measurementType) || null,
    range_min: form.rangeMin === '' ? null : Number(form.rangeMin),
    range_max: form.rangeMax === '' ? null : Number(form.rangeMax),
    unit: normalizeText(form.unit) || null,
    uncertainty_value: Number(form.uncertaintyValue),
    uncertainty_unit: normalizeText(form.uncertaintyUnit) || null,
    k_factor: form.kFactor === '' ? null : Number(form.kFactor),
    confidence_level: normalizeText(form.confidenceLevel) || null,
    distribution: normalizeText(form.distribution) || null,
    formula_reference: normalizeText(form.formulaReference) || null,
    notes: normalizeText(form.notes) || null
  };
}

function standardToForm(standard) {
  return {
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
  };
}

function certificateToForm(certificate) {
  return {
    id: certificate.id,
    certificateNumber: certificate.certificate_number ?? '',
    issuingLaboratory: certificate.issuing_laboratory ?? '',
    accreditationBody: certificate.accreditation_body ?? '',
    accreditationNumber: certificate.accreditation_number ?? '',
    calibrationDate: certificate.calibration_date ?? '',
    expirationDate: certificate.expiration_date ?? '',
    receivedDate: certificate.received_date ?? '',
    status: certificate.status ?? 'draft',
    traceabilityStatement: certificate.traceability_statement ?? '',
    environmentalConditions: certificate.environmental_conditions ?? '',
    notes: certificate.notes ?? ''
  };
}

function certificateUncertaintyToForm(certificate, uncertainty) {
  return {
    certificateId: certificate.id,
    id: uncertainty.id,
    magnitude: uncertainty.magnitude ?? '',
    measurementType: uncertainty.measurement_type ?? '',
    rangeMin: uncertainty.range_min ?? '',
    rangeMax: uncertainty.range_max ?? '',
    unit: uncertainty.unit ?? '',
    uncertaintyValue: uncertainty.uncertainty_value ?? '',
    uncertaintyUnit: uncertainty.uncertainty_unit ?? '',
    kFactor: uncertainty.k_factor ?? '2',
    confidenceLevel: uncertainty.confidence_level ?? '',
    distribution: uncertainty.distribution ?? '',
    formulaReference: uncertainty.formula_reference ?? '',
    notes: uncertainty.notes ?? ''
  };
}

function StandardsPage() {
  const [standards, setStandards] = useState([]);
  const [activeTab, setActiveTab] = useState('all');
  const [modalTab, setModalTab] = useState('general');
  const [selectedStandard, setSelectedStandard] = useState(null);

  const [standardForm, setStandardForm] = useState(emptyReferenceStandardForm);
  const [uncertaintyForm, setUncertaintyForm] = useState(emptyReferenceStandardUncertaintyForm);
  const [editingUncertaintyId, setEditingUncertaintyId] = useState(null);

  const [standardCertificates, setStandardCertificates] = useState([]);
  const [certificateForm, setCertificateForm] = useState(emptyCertificateForm);
  const [certificateUncertaintyForm, setCertificateUncertaintyForm] = useState(emptyCertificateUncertaintyForm);

  const [showCertificateForm, setShowCertificateForm] = useState(false);
  const [showCertificateUncertaintyForm, setShowCertificateUncertaintyForm] = useState(false);
  const [showLegacyUncertaintyForm, setShowLegacyUncertaintyForm] = useState(false);

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  const { confirmDialog, openConfirm, closeConfirm, handleConfirm } = useConfirmDialog();

  const currentStandard = standards.find((item) => item.id === selectedStandard?.id) ?? selectedStandard;

  const displayedStandards = useMemo(() => {
    if (activeTab === 'expired') {
      return standards.filter((item) => item.effective_status === 'expired');
    }

    if (activeTab === 'inactive') {
      return standards.filter((item) => item.status === 'inactive' || item.status === 'out_of_service');
    }

    return standards;
  }, [activeTab, standards]);

  const currentCertificate = useMemo(() => {
    return standardCertificates.find((certificate) => certificate.is_current);
  }, [standardCertificates]);

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

  async function loadCertificates(standardId) {
    if (!standardId) {
      setStandardCertificates([]);
      return;
    }

    const result = await listReferenceStandardCertificates({ reference_standard_id: standardId });
    setStandardCertificates(Array.isArray(result) ? result : []);
  }

  useEffect(() => {
    loadStandards();
  }, []);

  function resetModalState() {
    setModalTab('general');
    setStandardForm(emptyReferenceStandardForm);
    setUncertaintyForm(emptyReferenceStandardUncertaintyForm);
    setEditingUncertaintyId(null);
    setStandardCertificates([]);
    setCertificateForm(emptyCertificateForm);
    setCertificateUncertaintyForm(emptyCertificateUncertaintyForm);
    setShowCertificateForm(false);
    setShowCertificateUncertaintyForm(false);
    setShowLegacyUncertaintyForm(false);
  }

  function openCreateModal() {
    setSelectedStandard(null);
    resetModalState();
    setIsModalOpen(true);
    setError('');
    setNotice('');
  }

  function openEditModal(standard) {
    setSelectedStandard(standard);
    setStandardForm(standardToForm(standard));
    setUncertaintyForm(emptyReferenceStandardUncertaintyForm);
    setEditingUncertaintyId(null);
    setCertificateForm(emptyCertificateForm);
    setCertificateUncertaintyForm(emptyCertificateUncertaintyForm);
    setShowCertificateForm(false);
    setShowCertificateUncertaintyForm(false);
    setShowLegacyUncertaintyForm(false);
    setModalTab('general');
    loadCertificates(standard.id).catch((requestError) => setError(requestError.message));
    setIsModalOpen(true);
    setError('');
    setNotice('');
  }

  function closeModal() {
    setIsModalOpen(false);
    setSelectedStandard(null);
    resetModalState();
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

      setNotice(selectedStandard ? 'Patrón actualizado.' : 'Patrón creado.');
      await loadStandards();

      if (!selectedStandard && saved?.id) {
        setSelectedStandard(saved);
        setStandardForm(standardToForm(saved));
        setModalTab('certificates');
      } else if (saved?.id) {
        setSelectedStandard(saved);
      }
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsSaving(false);
    }
  }

  function handleDeleteStandard(standard) {
    openConfirm({
      title: 'Dar de baja patrón',
      message: `Se dará de baja el patrón ${standard.internal_code}.`,
      confirmText: 'Dar de baja',
      variant: 'danger',
      onConfirm: async () => {
        setError('');
        setNotice('');

        try {
          await deleteReferenceStandard(standard.id);
          setNotice('Patrón dado de baja.');
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

  async function handleSaveCertificate(event) {
    event.preventDefault();

    if (!currentStandard?.id) return;

    if (!certificateForm.certificateNumber.trim()) {
      setError('Captura el número de certificado.');
      return;
    }

    setIsSaving(true);
    setError('');
    setNotice('');

    try {
      const payload = mapCertificatePayload(certificateForm);

      await (certificateForm.id
        ? updateReferenceStandardCertificate(certificateForm.id, payload)
        : createReferenceStandardCertificate(currentStandard.id, payload));

      setCertificateForm(emptyCertificateForm);
      setShowCertificateForm(false);
      setNotice('Certificado de patrón guardado.');
      await loadCertificates(currentStandard.id);
      await loadStandards();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsSaving(false);
    }
  }

  function editCertificate(certificate) {
    setCertificateForm(certificateToForm(certificate));
    setShowCertificateForm(true);
    setModalTab('certificates');
  }

  function handleActivateCertificate(certificate) {
    openConfirm({
      title: 'Activar certificado vigente',
      message: `Se marcará ${certificate.certificate_number} como certificado vigente del patrón.`,
      confirmText: 'Activar',
      onConfirm: async () => {
        setError('');
        setNotice('');

        try {
          await activateReferenceStandardCertificate(certificate.id);
          setNotice('Certificado vigente activado.');
          await loadCertificates(currentStandard.id);
          await loadStandards();
        } catch (requestError) {
          setError(requestError.message);
        }
      }
    });
  }

  function handleSuspendCertificate(certificate) {
    openConfirm({
      title: 'Suspender certificado',
      message: `Se suspenderá el certificado ${certificate.certificate_number}.`,
      confirmText: 'Suspender',
      variant: 'danger',
      onConfirm: async () => {
        setError('');
        setNotice('');

        try {
          await suspendReferenceStandardCertificate(certificate.id);
          setNotice('Certificado suspendido.');
          await loadCertificates(currentStandard.id);
          await loadStandards();
        } catch (requestError) {
          setError(requestError.message);
        }
      }
    });
  }

  async function handleSaveCertificateUncertainty(event) {
    event.preventDefault();

    if (!currentStandard?.id) return;

    if (!certificateUncertaintyForm.certificateId || !certificateUncertaintyForm.uncertaintyValue) {
      setError('Selecciona certificado y captura incertidumbre.');
      return;
    }

    setIsSaving(true);
    setError('');
    setNotice('');

    try {
      const payload = mapCertificateUncertaintyPayload(certificateUncertaintyForm);

      await (certificateUncertaintyForm.id
        ? updateReferenceStandardCertificateUncertainty(certificateUncertaintyForm.id, payload)
        : createReferenceStandardCertificateUncertainty(certificateUncertaintyForm.certificateId, payload));

      setCertificateUncertaintyForm(emptyCertificateUncertaintyForm);
      setShowCertificateUncertaintyForm(false);
      setNotice('Incertidumbre del certificado guardada.');
      await loadCertificates(currentStandard.id);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsSaving(false);
    }
  }

  function editCertificateUncertainty(certificate, uncertainty) {
    setCertificateUncertaintyForm(certificateUncertaintyToForm(certificate, uncertainty));
    setShowCertificateUncertaintyForm(true);
    setModalTab('uncertainties');
  }

  function handleDeleteCertificateUncertainty(uncertainty) {
    openConfirm({
      title: 'Dar de baja incertidumbre',
      message: 'Se desactivará esta incertidumbre del certificado.',
      confirmText: 'Dar de baja',
      variant: 'danger',
      onConfirm: async () => {
        if (!currentStandard?.id) return;

        setError('');
        setNotice('');

        try {
          await deleteReferenceStandardCertificateUncertainty(uncertainty.id);
          setNotice('Incertidumbre dada de baja.');
          await loadCertificates(currentStandard.id);
        } catch (requestError) {
          setError(requestError.message);
        }
      }
    });
  }

  function startEditLegacyUncertainty(item) {
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
    setShowLegacyUncertaintyForm(true);
  }

  async function handleSaveLegacyUncertainty(event) {
    event.preventDefault();

    if (!selectedStandard) {
      setError('Guarda primero el patrón para poder agregar incertidumbres.');
      return;
    }

    if (!uncertaintyForm.uncertaintyValue) {
      setError('Captura la incertidumbre.');
      return;
    }

    setIsSaving(true);
    setError('');
    setNotice('');

    try {
      const payload = mapUncertaintyPayload(uncertaintyForm);

      const saved = editingUncertaintyId
        ? await updateReferenceStandardUncertainty(selectedStandard.id, editingUncertaintyId, payload)
        : await createReferenceStandardUncertainty(selectedStandard.id, payload);

      setStandards((current) => current.map((item) => (item.id === saved.id ? saved : item)));
      setSelectedStandard(saved);
      setUncertaintyForm(emptyReferenceStandardUncertaintyForm);
      setEditingUncertaintyId(null);
      setShowLegacyUncertaintyForm(false);
      setNotice(editingUncertaintyId ? 'Incertidumbre actualizada.' : 'Incertidumbre agregada.');
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsSaving(false);
    }
  }

  function handleDeleteLegacyUncertainty(uncertainty) {
    if (!selectedStandard) return;

    openConfirm({
      title: 'Dar de baja incertidumbre',
      message: 'Se desactivará este rango de incertidumbre legacy.',
      confirmText: 'Desactivar',
      variant: 'danger',
      onConfirm: async () => {
        setError('');
        setNotice('');

        try {
          const saved = await deleteReferenceStandardUncertainty(selectedStandard.id, uncertainty.id);
          setStandards((current) => current.map((item) => (item.id === saved.id ? saved : item)));
          setSelectedStandard(saved);
          setNotice('Incertidumbre desactivada.');
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
          <Ruler size={28} />
        </span>
        <div>
          <p>Trazabilidad metrológica</p>
          <h1>Patrones</h1>
          <span>Gestión de equipos patrón, certificados vigentes e incertidumbres por rango.</span>
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
            <p>Catálogo de patrones</p>
            <h2>{isLoading ? 'Cargando...' : `${displayedStandards.length} registros`}</h2>
          </div>
          <div className="toolbar-actions">
            <button className="primary-button" type="button" onClick={openCreateModal}>
              <Plus size={16} />
              Nuevo patrón
            </button>
          </div>
        </div>

        <div className="clients-table certificates-table" aria-busy={isLoading}>
          <div className="clients-table__head">
            <span>Clave</span>
            <span>Patrón</span>
            <span>Magnitud</span>
            <span>Empresa</span>
            <span>Rango</span>
            <span>Certificado vigente</span>
            <span>Estado</span>
            <span>Acciones</span>
          </div>

          {isLoading ? (
            <div className="clients-empty">Cargando patrones...</div>
          ) : displayedStandards.length ? (
            displayedStandards.map((item) => (
              <button
                className="clients-table__row clients-table__row--button"
                key={item.id}
                type="button"
                onClick={() => openEditModal(item)}
              >
                <span>
                  <strong>{item.internal_code}</strong>
                </span>
                <span>
                  <strong>{item.name}</strong>
                  <br />
                  <small>{[item.brand, item.model, item.serial_number].filter(Boolean).join(' / ') || 'Sin datos'}</small>
                </span>
                <span>{item.magnitude || '-'}</span>
                <span>{item.owner_company || '-'}</span>
                <span>
                  {[item.range_min, item.range_max, item.unit]
                    .filter((value) => value !== null && value !== '')
                    .join(' / ') || '-'}
                </span>
                <span>
                  <strong>{item.current_certificate_number || 'No vigente'}</strong>
                  <br />
                  <small>{item.current_certificate_expiration_date ? `Vence: ${formatDate(item.current_certificate_expiration_date)}` : ''}</small>
                </span>
                <span>
                  <mark className={`quotation-status status-${item.effective_status}`}>
                    {referenceStandardStatusLabels[item.effective_status] ?? item.effective_status}
                  </mark>
                </span>
                <span className="table-actions" onClick={(event) => event.stopPropagation()}>
                  <button className="table-button" type="button" onClick={() => openEditModal(item)}>
                    Abrir
                  </button>
                  <button className="table-button table-button--danger" type="button" onClick={() => handleDeleteStandard(item)}>
                    Baja
                  </button>
                </span>
              </button>
            ))
          ) : (
            <div className="clients-empty">No hay patrones en esta vista.</div>
          )}
        </div>
      </section>

      {isModalOpen ? (
        <div className="modal-overlay" role="presentation" onClick={closeModal}>
          <section
            className="detail-modal certificate-modal standards-detail-modal"
            role="dialog"
            aria-modal="true"
            onClick={(event) => event.stopPropagation()}
          >
            <button className="detail-modal__close" onClick={closeModal} type="button" aria-label="Cerrar">
              <X size={18} />
            </button>

            <div className="detail-modal__header standards-header">
              <div className="standards-header__info">
                <span className="standards-header__caption">
                  {currentStandard ? currentStandard.internal_code : 'Nuevo patrón'}
                </span>

                <h2>
                  {currentStandard ? currentStandard.name : 'Alta de patrón'}
                </h2>

                {currentStandard ? (
                  <p className="standards-header__meta">
                    {currentStandard.magnitude || 'Sin magnitud'}
                    {' · '}
                    {currentStandard.owner_company || 'Sin empresa'}
                  </p>
                ) : (
                  <p className="standards-header__meta">
                    Registro maestro del equipo patrón.
                  </p>
                )}
              </div>

              {currentStandard ? (
                <div className="quotation-detail-summary standards-current-certificate">
                  <span>Certificado vigente</span>
                  <strong>
                    {currentCertificate?.certificate_number ||
                      currentStandard.current_certificate_number ||
                      'No vigente'}
                  </strong>
                  <small>
                    {(currentCertificate?.expiration_date ||
                      currentStandard.current_certificate_expiration_date)
                      ? `Vence: ${formatDate(
                          currentCertificate?.expiration_date ??
                            currentStandard.current_certificate_expiration_date
                        )}`
                      : 'Sin fecha de vencimiento'}
                  </small>
                </div>
              ) : null}
            </div>

            <div className="module-tabs" role="tablist" aria-label="Detalle del patrón">
              {[
                ['general', 'General'],
                ['certificates', 'Certificados'],
                ['uncertainties', 'Incertidumbres'],
                ['history', 'Historial']
              ].map(([key, label]) => (
                <button
                  key={key}
                  type="button"
                  aria-selected={modalTab === key}
                  className={modalTab === key ? 'module-tab is-active' : 'module-tab'}
                  onClick={() => setModalTab(key)}
                  disabled={!currentStandard?.id && key !== 'general'}
                >
                  {label}
                </button>
              ))}
            </div>

            {modalTab === 'general' ? (
              <section className="quotation-section">
                <div className="quotation-section__title">
                  <p>Información física</p>
                  <h3>Datos generales del patrón</h3>
                </div>

                <form className="field-sheet-form-grid" onSubmit={handleSaveStandard}>
                  {[
                    ['internalCode', 'Clave interna'],
                    ['name', 'Nombre'],
                    ['magnitude', 'Magnitud'],
                    ['brand', 'Marca'],
                    ['model', 'Modelo'],
                    ['serialNumber', 'Serie'],
                    ['identification', 'Identificación'],
                    ['unit', 'Unidad'],
                    ['rangeMin', 'Rango mínimo'],
                    ['rangeMax', 'Rango máximo'],
                    ['resolution', 'Resolución'],
                    ['coverageFactorK', 'Factor k'],
                    ['provider', 'Proveedor'],
                    ['calibrationLaboratory', 'Laboratorio'],
                    ['certificateNumber', 'No. certificado legacy'],
                    ['certificateFilePath', 'Ruta certificado legacy']
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
                    <select
                      value={standardForm.ownerCompany}
                      onChange={(event) => setStandardForm((current) => ({ ...current, ownerCompany: event.target.value }))}
                    >
                      <option value="MYC">MYC</option>
                      <option value="Capimet">Capimet</option>
                      <option value="Otro">Otro</option>
                    </select>
                  </label>

                  <label>
                    Estado
                    <select
                      value={standardForm.status}
                      onChange={(event) => setStandardForm((current) => ({ ...current, status: event.target.value }))}
                    >
                      <option value="active">Activo</option>
                      <option value="expired">Vencido</option>
                      <option value="out_of_service">Fuera de servicio</option>
                      <option value="inactive">Inactivo</option>
                    </select>
                  </label>

                  <label>
                    Fecha calibración
                    <input
                      type="date"
                      value={standardForm.calibratedOn}
                      onChange={(event) => setStandardForm((current) => ({ ...current, calibratedOn: event.target.value }))}
                    />
                  </label>

                  <label>
                    Próxima calibración
                    <input
                      type="date"
                      value={standardForm.nextCalibrationOn}
                      onChange={(event) => setStandardForm((current) => ({ ...current, nextCalibrationOn: event.target.value }))}
                    />
                  </label>

                  <label className="form-field--wide">
                    Descripción
                    <textarea
                      rows={3}
                      value={standardForm.description}
                      onChange={(event) => setStandardForm((current) => ({ ...current, description: event.target.value }))}
                    />
                  </label>

                  <label className="form-field--wide">
                    Notas
                    <textarea
                      rows={3}
                      value={standardForm.notes}
                      onChange={(event) => setStandardForm((current) => ({ ...current, notes: event.target.value }))}
                    />
                  </label>

                  <div className="quotation-detail-save">
                    <div className="toolbar-actions">
                      <button className="table-button" type="button" onClick={closeModal}>
                        Cancelar
                      </button>
                      <button className="primary-button" type="submit" disabled={isSaving}>
                        {selectedStandard ? 'Guardar cambios' : 'Crear patrón'}
                      </button>
                    </div>
                  </div>
                </form>
              </section>
            ) : null}

            {modalTab === 'certificates' && currentStandard?.id ? (
              <section className="quotation-section">
                <div className="quotation-section__title">
                  <p>Certificados del patrón</p>
                  <h3>Historial metrológico</h3>
                  <div className="toolbar-actions">
                    <button
                      className="primary-button"
                      type="button"
                      onClick={() => {
                        setCertificateForm(emptyCertificateForm);
                        setShowCertificateForm((current) => !current);
                      }}
                    >
                      <Plus size={16} />
                      Nuevo certificado
                    </button>
                  </div>
                </div>

                {showCertificateForm ? (
                  <form className="field-sheet-form-grid" onSubmit={handleSaveCertificate}>
                    {[
                      ['certificateNumber', 'No. certificado'],
                      ['issuingLaboratory', 'Laboratorio emisor'],
                      ['accreditationBody', 'Organismo acreditador'],
                      ['accreditationNumber', 'No. acreditación']
                    ].map(([key, label]) => (
                      <label key={key}>
                        {label}
                        <input
                          type="text"
                          value={certificateForm[key]}
                          onChange={(event) => setCertificateForm((current) => ({ ...current, [key]: event.target.value }))}
                        />
                      </label>
                    ))}

                    <label>
                      Fecha calibración
                      <input
                        type="date"
                        value={certificateForm.calibrationDate}
                        onChange={(event) => setCertificateForm((current) => ({ ...current, calibrationDate: event.target.value }))}
                      />
                    </label>

                    <label>
                      Vencimiento
                      <input
                        type="date"
                        value={certificateForm.expirationDate}
                        onChange={(event) => setCertificateForm((current) => ({ ...current, expirationDate: event.target.value }))}
                      />
                    </label>

                    <label>
                      Estado
                      <select
                        value={certificateForm.status}
                        onChange={(event) => setCertificateForm((current) => ({ ...current, status: event.target.value }))}
                      >
                        <option value="draft">Borrador</option>
                        <option value="active">Activo</option>
                        <option value="expired">Vencido</option>
                        <option value="obsolete">Obsoleto</option>
                        <option value="rejected">Rechazado</option>
                        <option value="suspended">Suspendido</option>
                      </select>
                    </label>

                    <label className="form-field--wide">
                      Trazabilidad
                      <textarea
                        rows={2}
                        value={certificateForm.traceabilityStatement}
                        onChange={(event) => setCertificateForm((current) => ({ ...current, traceabilityStatement: event.target.value }))}
                      />
                    </label>

                    <label className="form-field--wide">
                      Observaciones
                      <textarea
                        rows={2}
                        value={certificateForm.notes}
                        onChange={(event) => setCertificateForm((current) => ({ ...current, notes: event.target.value }))}
                      />
                    </label>

                    <div className="quotation-detail-save">
                      <div className="toolbar-actions">
                        <button
                          className="table-button"
                          type="button"
                          onClick={() => {
                            setCertificateForm(emptyCertificateForm);
                            setShowCertificateForm(false);
                          }}
                        >
                          Cancelar
                        </button>
                        <button className="primary-button" type="submit" disabled={isSaving}>
                          {certificateForm.id ? 'Guardar certificado' : 'Crear certificado'}
                        </button>
                      </div>
                    </div>
                  </form>
                ) : null}

                <div className="clients-table certificates-table">
                  <div className="clients-table__head">
                    <span>No.</span>
                    <span>Laboratorio</span>
                    <span>Calibración</span>
                    <span>Vencimiento</span>
                    <span>Estado</span>
                    <span>Incertidumbres</span>
                    <span>Acciones</span>
                  </div>

                  {standardCertificates.length ? (
                    standardCertificates.map((certificate) => (
                      <div className="clients-table__row" key={certificate.id}>
                        <span>
                          <strong>{certificate.certificate_number}</strong>
                          <br />
                          <small>{certificate.is_current ? 'Vigente actual' : 'Histórico'}</small>
                        </span>
                        <span>{certificate.issuing_laboratory || '-'}</span>
                        <span>{formatDate(certificate.calibration_date)}</span>
                        <span>{formatDate(certificate.expiration_date)}</span>
                        <span>
                          <mark className={`quotation-status status-${certificate.effective_status}`}>
                            {certificate.effective_status}
                          </mark>
                        </span>
                        <span>{(certificate.uncertainties ?? []).filter((item) => item.is_active !== false).length}</span>
                        <span className="table-actions">
                          <button className="table-button" type="button" onClick={() => editCertificate(certificate)}>
                            Editar
                          </button>
                          <button className="table-button" type="button" onClick={() => handleActivateCertificate(certificate)}>
                            Activar
                          </button>
                          <button className="table-button table-button--danger" type="button" onClick={() => handleSuspendCertificate(certificate)}>
                            Suspender
                          </button>
                        </span>
                      </div>
                    ))
                  ) : (
                    <div className="clients-empty">No hay certificados registrados para este patrón.</div>
                  )}
                </div>
              </section>
            ) : null}

            {modalTab === 'uncertainties' && currentStandard?.id ? (
              <section className="quotation-section">
                <div className="quotation-section__title">
                  <p>Incertidumbres</p>
                  <h3>Incertidumbres por certificado vigente o histórico</h3>
                  <div className="toolbar-actions">
                    <button
                      className="primary-button"
                      type="button"
                      onClick={() => {
                        setCertificateUncertaintyForm(emptyCertificateUncertaintyForm);
                        setShowCertificateUncertaintyForm((current) => !current);
                      }}
                    >
                      <Plus size={16} />
                      Agregar incertidumbre
                    </button>
                  </div>
                </div>

                {showCertificateUncertaintyForm ? (
                  <form className="field-sheet-form-grid" onSubmit={handleSaveCertificateUncertainty}>
                    <label>
                      Certificado
                      <select
                        value={certificateUncertaintyForm.certificateId}
                        onChange={(event) => setCertificateUncertaintyForm((current) => ({ ...current, certificateId: event.target.value }))}
                      >
                        <option value="">Selecciona certificado</option>
                        {standardCertificates.map((certificate) => (
                          <option key={certificate.id} value={certificate.id}>
                            {certificate.certificate_number}
                          </option>
                        ))}
                      </select>
                    </label>

                    <label>
                      Tipo de medición
                      <input
                        type="text"
                        value={certificateUncertaintyForm.measurementType}
                        onChange={(event) => setCertificateUncertaintyForm((current) => ({ ...current, measurementType: event.target.value }))}
                      />
                    </label>

                    <label>
                      Rango mínimo
                      <input
                        type="text"
                        value={certificateUncertaintyForm.rangeMin}
                        onChange={(event) => setCertificateUncertaintyForm((current) => ({ ...current, rangeMin: event.target.value }))}
                      />
                    </label>

                    <label>
                      Rango máximo
                      <input
                        type="text"
                        value={certificateUncertaintyForm.rangeMax}
                        onChange={(event) => setCertificateUncertaintyForm((current) => ({ ...current, rangeMax: event.target.value }))}
                      />
                    </label>

                    <label>
                      Unidad
                      <input
                        type="text"
                        value={certificateUncertaintyForm.unit}
                        onChange={(event) => setCertificateUncertaintyForm((current) => ({ ...current, unit: event.target.value }))}
                      />
                    </label>

                    <label>
                      Incertidumbre
                      <input
                        type="text"
                        value={certificateUncertaintyForm.uncertaintyValue}
                        onChange={(event) => setCertificateUncertaintyForm((current) => ({ ...current, uncertaintyValue: event.target.value }))}
                      />
                    </label>

                    <label>
                      Unidad incertidumbre
                      <input
                        type="text"
                        value={certificateUncertaintyForm.uncertaintyUnit}
                        onChange={(event) => setCertificateUncertaintyForm((current) => ({ ...current, uncertaintyUnit: event.target.value }))}
                      />
                    </label>

                    <label>
                      Factor k
                      <input
                        type="text"
                        value={certificateUncertaintyForm.kFactor}
                        onChange={(event) => setCertificateUncertaintyForm((current) => ({ ...current, kFactor: event.target.value }))}
                      />
                    </label>

                    <label>
                      Confianza
                      <input
                        type="text"
                        value={certificateUncertaintyForm.confidenceLevel}
                        onChange={(event) => setCertificateUncertaintyForm((current) => ({ ...current, confidenceLevel: event.target.value }))}
                      />
                    </label>

                    <label className="form-field--wide">
                      Notas
                      <textarea
                        rows={2}
                        value={certificateUncertaintyForm.notes}
                        onChange={(event) => setCertificateUncertaintyForm((current) => ({ ...current, notes: event.target.value }))}
                      />
                    </label>

                    <div className="quotation-detail-save">
                      <div className="toolbar-actions">
                        <button
                          className="table-button"
                          type="button"
                          onClick={() => {
                            setCertificateUncertaintyForm(emptyCertificateUncertaintyForm);
                            setShowCertificateUncertaintyForm(false);
                          }}
                        >
                          Cancelar
                        </button>
                        <button className="primary-button" type="submit" disabled={isSaving}>
                          {certificateUncertaintyForm.id ? 'Guardar incertidumbre' : 'Agregar incertidumbre'}
                        </button>
                      </div>
                    </div>
                  </form>
                ) : null}

                {standardCertificates.map((certificate) => (
                  <div className="clients-table certificates-table" key={`unc-${certificate.id}`}>
                    <div className="clients-table__head">
                      <span>{certificate.certificate_number}</span>
                      <span>Rango</span>
                      <span>Unidad</span>
                      <span>Incertidumbre</span>
                      <span>k</span>
                      <span>Acciones</span>
                    </div>

                    {(certificate.uncertainties ?? []).filter((item) => item.is_active !== false).length ? (
                      (certificate.uncertainties ?? [])
                        .filter((item) => item.is_active !== false)
                        .map((item) => (
                          <div className="clients-table__row" key={item.id}>
                            <span>{item.measurement_type || item.magnitude || '-'}</span>
                            <span>
                              {[item.range_min, item.range_max]
                                .filter((value) => value !== null && value !== '')
                                .join(' a ') || 'Abierto'}
                            </span>
                            <span>{item.unit || '-'}</span>
                            <span>{[item.uncertainty_value, item.uncertainty_unit].filter(Boolean).join(' ')}</span>
                            <span>{item.k_factor || '-'}</span>
                            <span className="table-actions">
                              <button className="table-button" type="button" onClick={() => editCertificateUncertainty(certificate, item)}>
                                Editar
                              </button>
                              <button className="table-button table-button--danger" type="button" onClick={() => handleDeleteCertificateUncertainty(item)}>
                                Baja
                              </button>
                            </span>
                          </div>
                        ))
                    ) : (
                      <div className="clients-empty">No hay incertidumbres en este certificado.</div>
                    )}
                  </div>
                ))}

                <div className="quotation-section__title">
                  <p>Incertidumbres legacy</p>
                  <h3>Compatibilidad con el modelo anterior</h3>
                  <div className="toolbar-actions">
                    <button
                      className="table-button"
                      type="button"
                      onClick={() => {
                        setUncertaintyForm(emptyReferenceStandardUncertaintyForm);
                        setEditingUncertaintyId(null);
                        setShowLegacyUncertaintyForm((current) => !current);
                      }}
                    >
                      Gestionar legacy
                    </button>
                  </div>
                </div>

                {showLegacyUncertaintyForm ? (
                  <form className="field-sheet-form-grid" onSubmit={handleSaveLegacyUncertainty}>
                    {[
                      ['rangeMin', 'Rango mínimo'],
                      ['rangeMax', 'Rango máximo'],
                      ['unit', 'Unidad'],
                      ['uncertaintyValue', 'Incertidumbre'],
                      ['coverageFactorK', 'Factor k'],
                      ['distribution', 'Distribución']
                    ].map(([key, label]) => (
                      <label key={key}>
                        {label}
                        <input
                          type="text"
                          value={uncertaintyForm[key]}
                          onChange={(event) => setUncertaintyForm((current) => ({ ...current, [key]: event.target.value }))}
                        />
                      </label>
                    ))}

                    <label className="form-field--wide">
                      Notas
                      <textarea
                        rows={2}
                        value={uncertaintyForm.notes}
                        onChange={(event) => setUncertaintyForm((current) => ({ ...current, notes: event.target.value }))}
                      />
                    </label>

                    <div className="quotation-detail-save">
                      <div className="toolbar-actions">
                        <button
                          className="table-button"
                          type="button"
                          onClick={() => {
                            setEditingUncertaintyId(null);
                            setUncertaintyForm(emptyReferenceStandardUncertaintyForm);
                            setShowLegacyUncertaintyForm(false);
                          }}
                        >
                          Cancelar
                        </button>
                        <button className="primary-button" type="submit" disabled={isSaving}>
                          {editingUncertaintyId ? 'Guardar legacy' : 'Agregar legacy'}
                        </button>
                      </div>
                    </div>
                  </form>
                ) : null}

                <div className="clients-table certificates-table">
                  <div className="clients-table__head">
                    <span>Rango</span>
                    <span>Unidad</span>
                    <span>Incertidumbre</span>
                    <span>k</span>
                    <span>Distribución</span>
                    <span>Acciones</span>
                  </div>

                  {(currentStandard.uncertainties ?? []).filter((item) => item.is_active !== false).length ? (
                    currentStandard.uncertainties
                      .filter((item) => item.is_active !== false)
                      .map((item) => (
                        <div className="clients-table__row" key={item.id}>
                          <span>
                            {[item.range_min, item.range_max]
                              .filter((value) => value !== null && value !== '')
                              .join(' a ') || 'Abierto'}
                          </span>
                          <span>{item.unit || '-'}</span>
                          <span>{item.uncertainty_value}</span>
                          <span>{item.coverage_factor_k || '-'}</span>
                          <span>{item.distribution || '-'}</span>
                          <span className="table-actions">
                            <button className="table-button" type="button" onClick={() => startEditLegacyUncertainty(item)}>
                              Editar
                            </button>
                            <button className="table-button table-button--danger" type="button" onClick={() => handleDeleteLegacyUncertainty(item)}>
                              Baja
                            </button>
                          </span>
                        </div>
                      ))
                  ) : (
                    <div className="clients-empty">No hay incertidumbres legacy activas.</div>
                  )}
                </div>
              </section>
            ) : null}

            {modalTab === 'history' && currentStandard?.id ? (
              <section className="quotation-section">
                <div className="quotation-section__title">
                  <p>Historial</p>
                  <h3>Trazabilidad del patrón</h3>
                </div>

                <div className="field-sheet-summary-grid">
                  <article>
                    <span>Creado</span>
                    <strong>{formatDateTime(currentStandard.created_at)}</strong>
                  </article>
                  <article>
                    <span>Última actualización</span>
                    <strong>{formatDateTime(currentStandard.updated_at)}</strong>
                  </article>
                  <article>
                    <span>Estado efectivo</span>
                    <strong>{currentStandard.effective_status || '-'}</strong>
                  </article>
                  <article>
                    <span>Certificados registrados</span>
                    <strong>{standardCertificates.length}</strong>
                  </article>
                </div>

                <div className="clients-empty">
                  El historial de uso en servicios, certificados emitidos y auditoría detallada se conectará en una fase posterior.
                </div>
              </section>
            ) : null}
          </section>
        </div>
      ) : null}

      <ConfirmDialog
        {...(confirmDialog ?? {})}
        isOpen={confirmDialog?.isOpen ?? false}
        onCancel={closeConfirm}
        onConfirm={handleConfirm}
      />
    </section>
  );
}

export default StandardsPage;