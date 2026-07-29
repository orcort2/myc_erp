import {
  Archive,
  BookOpenCheck,
  CheckCircle2,
  Clock3,
  FilePlus2,
  Files,
  Pencil,
  Plus,
  Search,
  X
} from 'lucide-react';
import React, { useEffect, useMemo, useState } from 'react';

import ConfirmDialog from '../components/ConfirmDialog.jsx';
import ActivityPanel from '../components/activity/ActivityPanel.jsx';
import {
  activateControlledDocumentVersion,
  archiveControlledDocument,
  createControlledDocument,
  createCertificateMaster,
  createControlledDocumentVersion,
  downloadControlledDocumentVersion,
  listControlledDocuments,
  updateControlledDocument
} from '../services/api.js';
import useConfirmDialog from '../utils/useConfirmDialog.js';

const documentTypes = [
  'manual', 'procedure', 'format', 'record', 'policy', 'uncertainty_calculation',
  'certificate_master', 'field_sheet_template', 'work_order_template',
  'quotation_template', 'external_standard', 'other'
];

const typeLabels = {
  manual: 'Manual',
  procedure: 'Procedimiento',
  format: 'Formato',
  record: 'Registro',
  policy: 'Politica',
  uncertainty_calculation: 'Calculo de incertidumbre',
  certificate_master: 'Maestro de certificado',
  field_sheet_template: 'Plantilla de hoja de campo',
  work_order_template: 'Plantilla de orden de trabajo',
  quotation_template: 'Plantilla de cotizacion',
  external_standard: 'Norma externa',
  other: 'Otro'
};

const compactTypeLabels = {
  manual: 'Manual',
  procedure: 'Procedimiento',
  format: 'Formato',
  record: 'Registro',
  policy: 'Politica',
  uncertainty_calculation: 'Incertidumbre',
  certificate_master: 'Certificado',
  field_sheet_template: 'Hoja de Campo',
  work_order_template: 'Orden de Trabajo',
  quotation_template: 'Cotizacion',
  external_standard: 'Norma externa',
  other: 'Otro'
};

const statusLabels = {
  draft: 'Borrador',
  in_review: 'En revision',
  approved: 'Aprobado',
  active: 'Vigente',
  obsolete: 'Obsoleto',
  archived: 'Archivado',
  suspended: 'Suspendido'
};

const detailTabs = [
  ['information', 'Informacion'],
  ['versions', 'Versiones'],
  ['activity', 'Actividad'],
  ['history', 'Historial'],
  ['publication', 'Publicacion'],
  ['designer', 'Diseñador']
];

const emptyDocument = {
  code: '', name: '', document_type: 'format', quality_level: '', current_revision: '',
  issue_date: '', last_review_date: '', effective_date: '', retention_time: '',
  digital_location: '', status: 'draft', description: ''
};

const emptyVersion = {
  revision: '', file_path: '', original_filename: '', mime_type: '', checksum: '',
  change_summary: '', reviewed_by_id: '', effective_date: '', status: 'draft'
};

function optional(value) {
  return value === '' || value === undefined ? null : value;
}

function formatDate(value, includeTime = false) {
  if (!value) return 'No definida';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return 'No definida';
  return includeTime
    ? date.toLocaleString('es-MX', { dateStyle: 'medium', timeStyle: 'short' })
    : date.toLocaleDateString('es-MX', { dateStyle: 'medium' });
}

function getRoleNames(user) {
  return (user?.roles ?? []).map((role) => String(role.name ?? '').toLowerCase());
}

function canManageDocuments(user) {
  const roles = getRoleNames(user);
  return roles.some((role) => ['administrador', 'admin', 'calidad', 'quality', 'desarrollador', 'developer'].includes(role));
}

function designerFor(type) {
  const designers = {
    quotation_template: 'Diseñador de Cotizaciones',
    work_order_template: 'Diseñador de Ordenes de Trabajo',
    field_sheet_template: 'Diseñador de Hojas de Campo',
    certificate_master: 'Diseñador de Certificados',
    procedure: 'Gestor de archivo controlado',
    manual: 'Gestor de archivo controlado'
  };
  return designers[type] ?? 'Diseñador especializado de documentos';
}

function toDocumentForm(document) {
  return {
    code: document?.code ?? '',
    name: document?.name ?? '',
    document_type: document?.document_type ?? 'format',
    quality_level: document?.quality_level ?? '',
    current_revision: document?.current_revision ?? '',
    issue_date: document?.issue_date ?? '',
    last_review_date: document?.last_review_date ?? '',
    effective_date: document?.effective_date ?? '',
    retention_time: document?.retention_time ?? '',
    digital_location: document?.digital_location ?? '',
    status: document?.status ?? 'draft',
    description: document?.description ?? ''
  };
}

function DefinitionList({ items }) {
  return (
    <dl className="document-detail-list">
      {items.map(([label, value]) => (
        <div key={label}>
          <dt>{label}</dt>
          <dd>{value || 'No definida'}</dd>
        </div>
      ))}
    </dl>
  );
}

function DocumentLibraryPage({ user = null }) {
  const [documents, setDocuments] = useState([]);
  const [selectedDocument, setSelectedDocument] = useState(null);
  const [activeTab, setActiveTab] = useState('information');
  const [filters, setFilters] = useState({ q: '', status: '', type: '' });
  const [documentForm, setDocumentForm] = useState(emptyDocument);
  const [versionForm, setVersionForm] = useState(emptyVersion);
  const [isDocumentFormOpen, setIsDocumentFormOpen] = useState(false);
  const [isVersionFormOpen, setIsVersionFormOpen] = useState(false);
  const [isMasterFormOpen, setIsMasterFormOpen] = useState(false);
  const [masterForm, setMasterForm] = useState({ code: '', name: '', description: '', revision: '1.0', effectiveDate: '', expiresOn: '', file: null });
  const [catalogView, setCatalogView] = useState('documents');
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const { closeConfirm, confirmDialog, handleConfirm, openConfirm } = useConfirmDialog();
  const canManage = canManageDocuments(user);

  async function loadDocuments(preferredId = null) {
    setError('');
    setIsLoading(true);
    try {
      const result = await listControlledDocuments();
      const next = Array.isArray(result) ? result : [];
      setDocuments(next);
      const targetId = preferredId ?? selectedDocument?.id;
      if (targetId) setSelectedDocument(next.find((item) => item.id === targetId) ?? null);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    loadDocuments();
  }, []);

  useEffect(() => {
    function closeOnEscape(event) {
      if (event.key !== 'Escape') return;
      if (isVersionFormOpen) setIsVersionFormOpen(false);
      else if (isDocumentFormOpen) setIsDocumentFormOpen(false);
      else setSelectedDocument(null);
    }
    window.addEventListener('keydown', closeOnEscape);
    return () => window.removeEventListener('keydown', closeOnEscape);
  }, [isDocumentFormOpen, isVersionFormOpen]);

  const filteredDocuments = useMemo(() => {
    const query = filters.q.trim().toLowerCase();
    return documents.filter((item) => {
      const searchable = [item.code, item.name, item.document_type, typeLabels[item.document_type], item.current_revision, item.status, statusLabels[item.status]]
        .filter(Boolean).join(' ').toLowerCase();
      return (catalogView !== 'masters' || item.document_type === 'certificate_master')
        && (!query || searchable.includes(query))
        && (!filters.status || item.status === filters.status)
        && (!filters.type || item.document_type === filters.type);
    });
  }, [documents, filters, catalogView]);

  const activeCount = documents.filter((item) => item.status === 'active').length;
  const draftCount = documents.filter((item) => item.status === 'draft').length;
  const obsoleteCount = documents.filter((item) => ['obsolete', 'archived', 'suspended'].includes(item.status)).length;
  const activeVersion = selectedDocument?.versions?.find((version) => version.status === 'active') ?? null;

  function openDocument(document) {
    setSelectedDocument(document);
    setActiveTab('information');
    setDocumentForm(toDocumentForm(document));
  }

  function openCreateForm() {
    setDocumentForm(emptyDocument);
    setIsDocumentFormOpen(true);
  }

  async function saveMaster(event) {
    event.preventDefault();
    if (!masterForm.file) { setError('Selecciona un archivo XLSX.'); return; }
    setIsSaving(true); setError('');
    try {
      const saved = await createCertificateMaster(masterForm);
      setNotice('Plantilla Maestra registrada como borrador. Activa su versión cuando esté vigente.');
      setIsMasterFormOpen(false);
      setMasterForm({ code: '', name: '', description: '', revision: '1.0', effectiveDate: '', expiresOn: '', file: null });
      await loadDocuments(saved.id);
    } catch (requestError) { setError(requestError.message); } finally { setIsSaving(false); }
  }

  async function downloadVersion(version) {
    try {
      const { blob, filename } = await downloadControlledDocumentVersion(selectedDocument.id, version.id);
      const url = URL.createObjectURL(blob); const link = document.createElement('a'); link.href = url; link.download = filename || version.original_filename; link.click(); URL.revokeObjectURL(url);
    } catch (requestError) { setError(requestError.message); }
  }

  function openEditForm() {
    setDocumentForm(toDocumentForm(selectedDocument));
    setIsDocumentFormOpen(true);
  }

  async function saveDocument(event) {
    event.preventDefault();
    setIsSaving(true);
    setError('');
    try {
      const payload = {
        ...documentForm,
        quality_level: optional(documentForm.quality_level),
        current_revision: optional(documentForm.current_revision),
        issue_date: optional(documentForm.issue_date),
        last_review_date: optional(documentForm.last_review_date),
        effective_date: optional(documentForm.effective_date),
        retention_time: optional(documentForm.retention_time),
        digital_location: optional(documentForm.digital_location),
        description: optional(documentForm.description)
      };
      const saved = selectedDocument
        ? await updateControlledDocument(selectedDocument.id, payload)
        : await createControlledDocument(payload);
      setNotice(selectedDocument ? 'Documento actualizado.' : 'Documento registrado.');
      setIsDocumentFormOpen(false);
      await loadDocuments(saved.id);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsSaving(false);
    }
  }

  async function saveVersion(event) {
    event.preventDefault();
    setIsSaving(true);
    setError('');
    try {
      await createControlledDocumentVersion(selectedDocument.id, {
        revision: versionForm.revision,
        file_path: optional(versionForm.file_path),
        original_filename: optional(versionForm.original_filename),
        mime_type: optional(versionForm.mime_type),
        checksum: optional(versionForm.checksum),
        change_summary: optional(versionForm.change_summary),
        reviewed_by_id: versionForm.reviewed_by_id ? Number(versionForm.reviewed_by_id) : null,
        effective_date: optional(versionForm.effective_date),
        status: versionForm.status
      });
      setVersionForm(emptyVersion);
      setIsVersionFormOpen(false);
      setNotice('Version documental registrada.');
      await loadDocuments(selectedDocument.id);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsSaving(false);
    }
  }

  function activateVersion(version) {
    openConfirm({
      title: 'Activar version documental',
      message: `La revision ${version.revision} quedara como version vigente de ${selectedDocument.code}.`,
      confirmText: 'Activar version',
      onConfirm: async () => {
        try {
          await activateControlledDocumentVersion(selectedDocument.id, version.id);
          setNotice(`La revision ${version.revision} se encuentra vigente.`);
          await loadDocuments(selectedDocument.id);
        } catch (requestError) {
          setError(requestError.message);
        }
      }
    });
  }

  function archiveDocument() {
    openConfirm({
      title: 'Archivar documento',
      message: `El documento ${selectedDocument.code} quedara obsoleto. Sus versiones se conservaran.`,
      confirmText: 'Marcar obsoleto',
      variant: 'danger',
      onConfirm: async () => {
        try {
          await archiveControlledDocument(selectedDocument.id, { status: 'obsolete', comment: 'Archivado desde Control Documental' });
          setNotice('Documento marcado como obsoleto.');
          await loadDocuments(selectedDocument.id);
        } catch (requestError) {
          setError(requestError.message);
        }
      }
    });
  }

  const historyItems = useMemo(() => {
    if (!selectedDocument) return [];
    const events = [
      { date: selectedDocument.created_at, title: 'Documento creado', detail: `${selectedDocument.code} se registro en Control Documental.` },
      selectedDocument.updated_at && selectedDocument.updated_at !== selectedDocument.created_at
        ? { date: selectedDocument.updated_at, title: 'Documento actualizado', detail: 'La metadata documental fue actualizada.' }
        : null,
      ...(selectedDocument.versions ?? []).flatMap((version) => [
        { date: version.created_at || version.uploaded_at, title: 'Version registrada', detail: `Revision ${version.revision} · ${statusLabels[version.status] ?? version.status}` },
        version.approved_at ? { date: version.approved_at, title: version.status === 'active' ? 'Version activada' : 'Version aprobada', detail: `Revision ${version.revision}` } : null
      ])
    ].filter(Boolean);
    return events.sort((a, b) => new Date(b.date) - new Date(a.date));
  }, [selectedDocument]);

  return (
    <section className="module-workspace document-control-workspace">
      <header className="module-workspace__hero clients-hero document-control-hero">
        <span className="module-workspace__icon"><Files size={28} /></span>
        <div>
          <p>Sistema de calidad</p>
          <h1>Control Documental</h1>
          <span>Catalogo central de formatos, revisiones, versiones y vigencias del sistema.</span>
        </div>
        {canManage && catalogView === 'documents' ? <button className="primary-button" type="button" onClick={openCreateForm}><Plus size={17} /> Registrar documento</button> : null}
      </header>

      {error ? <div className="form-error dashboard-error">{error}</div> : null}
      {notice ? <div className="form-notice dashboard-error">{notice}</div> : null}

      <section className="operations-band document-control-summary">
        <div className="operations-band__metric"><strong>{isLoading ? '-' : documents.length}</strong><span>Documentos registrados</span></div>
        <div className="operations-band__metric"><strong>{isLoading ? '-' : activeCount}</strong><span>Documentos vigentes</span></div>
        <div className="operations-band__metric"><strong>{isLoading ? '-' : draftCount}</strong><span>Documentos en borrador</span></div>
        <div className="operations-band__metric"><strong>{isLoading ? '-' : obsoleteCount}</strong><span>Documentos obsoletos</span></div>
      </section>

      <section className="clients-list-panel document-catalog-panel">
        <div className="section-heading document-catalog-heading">
          <div><p>Catalogo vigente</p><h2>{catalogView === 'masters' ? 'Plantillas Maestras' : 'Lista Maestra de Documentos'}</h2><span>{filteredDocuments.length} {catalogView === 'masters' ? `${filteredDocuments.length === 1 ? 'plantilla registrada' : 'plantillas registradas'}` : 'documentos registrados'}</span></div>
          <div className="document-catalog-filters">
            <label className="document-search"><Search size={16} /><input aria-label="Buscar documentos" placeholder="Buscar codigo, nombre, tipo, revision o estado" value={filters.q} onChange={(event) => setFilters({ ...filters, q: event.target.value })} /></label>
            <select aria-label="Filtrar por estado" value={filters.status} onChange={(event) => setFilters({ ...filters, status: event.target.value })}>
              <option value="">Todos los estados</option>
              {Object.entries(statusLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </select>
            {catalogView !== 'masters' ? <select aria-label="Filtrar por tipo" value={filters.type} onChange={(event) => setFilters({ ...filters, type: event.target.value })}>
              <option value="">Todos los tipos</option>
              {documentTypes.map((type) => <option key={type} value={type}>{typeLabels[type]}</option>)}
            </select> : <span className="document-filter-context">Maestro de certificado</span>}
          </div>
        </div>

        <div className="document-subnav" aria-label="Submódulos de Control Documental"><div className="document-subnav__tabs" role="tablist"><button aria-selected={catalogView === 'documents'} className={catalogView === 'documents' ? 'is-active' : ''} onClick={() => { setCatalogView('documents'); setFilters((current) => ({ ...current, type: '' })); }} role="tab" type="button">Lista Maestra</button><button aria-selected={catalogView === 'masters'} className={catalogView === 'masters' ? 'is-active' : ''} onClick={() => { setCatalogView('masters'); setFilters((current) => ({ ...current, type: 'certificate_master' })); }} role="tab" type="button">Plantillas Maestras</button></div>{catalogView === 'masters' && canManage ? <button className="primary-button document-subnav__action" onClick={() => setIsMasterFormOpen(true)} type="button"><Plus size={16} /> Nueva plantilla</button> : null}</div>

        <div className="clients-table document-catalog-table" role="table" aria-label="Lista Maestra de Documentos">
          <div className="clients-table__head document-catalog-grid" role="row">
            <span>Codigo</span><span>Documento</span><span>Revision vigente</span><span>Estado</span><span>Tipo</span><span>Vigencia</span><span>Versiones</span>
          </div>
          {filteredDocuments.map((document) => (
            <div
              key={document.id}
              className={`clients-table__row clients-table__row--clickable document-catalog-grid document-catalog-row ${selectedDocument?.id === document.id ? 'is-selected' : ''}`}
              role="row"
              tabIndex={0}
              onClick={() => openDocument(document)}
              onKeyDown={(event) => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); openDocument(document); } }}
            >
              <span role="cell"><strong>{document.code}</strong></span>
              <span role="cell" className="document-name-cell"><strong>{document.name}</strong><small>{document.quality_level || 'Clasificacion no definida'}</small></span>
              <span role="cell">{document.current_revision ? `Rev. ${document.current_revision}` : '—'}</span>
              <span role="cell"><span className={`status-pill status-pill--${document.status}`}>{statusLabels[document.status] ?? document.status}</span></span>
              <span role="cell"><span className={`document-type-mark document-type-mark--${document.document_type}`}><i />{compactTypeLabels[document.document_type] ?? 'Otro'}</span></span>
              <span role="cell">{document.effective_date ? formatDate(document.effective_date) : '—'}</span>
              <span role="cell">{document.versions?.length ?? 0}</span>
            </div>
          ))}
          {!isLoading && !filteredDocuments.length ? <div className="document-empty-state"><BookOpenCheck size={30} /><strong>Sin documentos coincidentes</strong><span>Ajusta la busqueda o los filtros.</span></div> : null}
        </div>
      </section>

      {selectedDocument ? (
        <div className="modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setSelectedDocument(null); }}>
          <section className="client-modal document-detail-modal" role="dialog" aria-modal="true" aria-labelledby="document-detail-title">
            <header className="document-detail-header">
              <div className="document-identity-card">
                <div className="document-identity-main"><p>{selectedDocument.code}</p><h2 id="document-detail-title">{selectedDocument.name}</h2></div>
                <div className="document-identity-facts">
                  <span><small>Estado</small><strong className={`status-pill status-pill--${selectedDocument.status}`}>{statusLabels[selectedDocument.status] ?? selectedDocument.status}</strong></span>
                  <span><small>Revision vigente</small><strong>{selectedDocument.current_revision || '—'}</strong></span>
                  <span><small>Versiones</small><strong>{selectedDocument.versions?.length ?? 0}</strong></span>
                  <span><small>Area responsable</small><strong>Pendiente de asignacion</strong></span>
                </div>
              </div>
              <div className="document-detail-actions">
                {canManage ? <button className="ghost-button" type="button" onClick={openEditForm}><Pencil size={15} /> Editar</button> : null}
                {canManage && !['obsolete', 'suspended'].includes(selectedDocument.status) ? <button className="document-obsolete-button" type="button" onClick={archiveDocument}><Archive size={15} /> Marcar obsoleto</button> : null}
                <button className="ghost-button document-close-button" type="button" aria-label="Cerrar ficha" onClick={() => setSelectedDocument(null)}><X size={18} /> Cerrar</button>
              </div>
            </header>

            <nav className="document-detail-tabs" aria-label="Ficha documental">
              {detailTabs.map(([key, label]) => <button key={key} className={activeTab === key ? 'is-active' : ''} type="button" onClick={() => setActiveTab(key)}>{label}</button>)}
            </nav>

            <div className="document-detail-content">
              {activeTab === 'information' ? (
                <div className="document-information-panel">
                  <section className="document-info-group"><header><p>Identidad documental</p><h3>Clasificacion y control</h3></header><DefinitionList items={[
                    ['Codigo', selectedDocument.code], ['Tipo', typeLabels[selectedDocument.document_type] ?? selectedDocument.document_type],
                    ['Estado', statusLabels[selectedDocument.status] ?? selectedDocument.status],
                    ['Nivel de calidad', selectedDocument.quality_level || 'No definido'],
                    ['Area responsable', 'Pendiente de asignacion'],
                    ['Responsable de registro', selectedDocument.created_by_id ? `Usuario ${selectedDocument.created_by_id}` : 'No definido']
                  ]} /></section>
                  <section className="document-info-group"><header><p>Ciclo documental</p><h3>Revision y vigencia</h3></header><DefinitionList items={[
                    ['Revision vigente', selectedDocument.current_revision || 'No publicada'],
                    ['Fecha de emision', formatDate(selectedDocument.issue_date)],
                    ['Ultima revision', formatDate(selectedDocument.last_review_date)],
                    ['Entrada en vigor', formatDate(selectedDocument.effective_date)],
                    ['Retencion', selectedDocument.retention_time || 'No definida'],
                    ['Ubicacion digital', selectedDocument.digital_location || 'No definida']
                  ]} /></section>
                  <article className="document-description"><span>Descripcion</span><p>{selectedDocument.description || 'Sin descripcion registrada.'}</p></article>
                </div>
              ) : null}

              {activeTab === 'versions' ? (
                <section>
                  <div className="document-tab-heading"><div><p>Control de revisiones</p><h3>{selectedDocument.versions?.length || 0} versiones</h3></div>{canManage ? <button className="primary-button" type="button" onClick={() => setIsVersionFormOpen(true)}><FilePlus2 size={16} /> Registrar version</button> : null}</div>
                  <div className="document-versions-grid">
                    {(selectedDocument.versions ?? []).map((version) => (
                      <article key={version.id} className={version.status === 'active' ? 'document-version-card is-active' : 'document-version-card'}>
                        <header><div><span>Revision</span><strong>{version.revision}</strong></div><span className={`status-pill status-pill--${version.status}`}>{statusLabels[version.status] ?? version.status}</span></header>
                        <DefinitionList items={[
                          ['Archivo', version.original_filename || version.file_path || 'Referencia no definida'],
                          ['MIME', version.mime_type || 'No definido'], ['Checksum', version.checksum || 'No definido'],
                          ['Registrada', formatDate(version.created_at || version.uploaded_at, true)],
                          ['Entrada en vigor', formatDate(version.effective_date)], ['Aprobada', formatDate(version.approved_at, true)],
                          ['Revisor', version.reviewed_by_id ? `Usuario ${version.reviewed_by_id}` : 'No definido'],
                          ['Aprobador', version.approved_by_id ? `Usuario ${version.approved_by_id}` : 'No definido']
                        ]} />
                        <p>{version.change_summary || 'Sin resumen de cambios.'}</p>
                        {version.file_path ? <button className="secondary-button" type="button" onClick={() => downloadVersion(version)}>Descargar XLSX</button> : null}
                        {canManage && version.status !== 'active' ? <button className="secondary-button" type="button" onClick={() => activateVersion(version)}><CheckCircle2 size={15} /> Activar version</button> : null}
                      </article>
                    ))}
                    {!selectedDocument.versions?.length ? <div className="document-empty-state"><FilePlus2 size={30} /><strong>Sin versiones</strong><span>Este documento todavia no tiene revisiones registradas.</span></div> : null}
                  </div>
                </section>
              ) : null}

              {activeTab === 'history' ? (
                <div className="document-history">
                  {historyItems.map((item, index) => <article key={`${item.title}-${item.date}-${index}`}><span><Clock3 size={16} /></span><div><time>{formatDate(item.date, true)}</time><strong>{item.title}</strong><p>{item.detail}</p></div></article>)}
                </div>
              ) : null}

              {activeTab === 'activity' ? (
                <ActivityPanel
                  entityId={selectedDocument.id}
                  entityType="document"
                />
              ) : null}

              {activeTab === 'publication' ? (
                <section className="document-publication-panel">
                  <div className={activeVersion ? 'document-publication-state is-active' : 'document-publication-state'}>
                    {activeVersion ? <CheckCircle2 size={32} /> : <Clock3 size={32} />}
                    <div><span>Estado de publicacion</span><div className="document-publication-badges"><strong className={`status-pill status-pill--${selectedDocument.status}`}>{statusLabels[selectedDocument.status] ?? selectedDocument.status}</strong><em>{activeVersion ? 'Disponible para referencia documental' : 'No disponible para operacion'}</em></div><h3>{activeVersion ? `La revision ${activeVersion.revision} se encuentra vigente.` : 'Este documento todavia no tiene una version activa.'}</h3><p>{activeVersion ? 'La revision activa esta disponible como referencia documental vigente.' : 'Registra una version y activala para establecer la revision vigente.'}</p></div>
                  </div>
                  <DefinitionList items={[
                    ['Estado del documento', statusLabels[selectedDocument.status] ?? selectedDocument.status],
                    ['Revision vigente', selectedDocument.current_revision || 'Sin revision publicada'],
                    ['Version activa', activeVersion ? `Revision ${activeVersion.revision}` : 'No existe'],
                    ['Entrada en vigor', formatDate(activeVersion?.effective_date || selectedDocument.effective_date)],
                    ['Disponibilidad futura', activeVersion ? 'Disponible' : 'No disponible']
                  ]} />
                </section>
              ) : null}

              {activeTab === 'designer' ? (
                <section className="document-designer-placeholder">
                  <span><Files size={34} /></span><p>Proximamente</p><h3>Diseñador documental</h3>
                  <p>Permitira administrar la composicion visual mediante componentes documentales validados, sin sustituir los datos ni procesos operativos.</p>
                  <div className="document-designer-facts"><span><small>Objetivo</small><strong>{designerFor(selectedDocument.document_type)}</strong></span><span><small>Estado</small><strong>Disponible proximamente</strong></span></div>
                  <button className="primary-button" type="button" disabled>Abrir diseñador <em>Proximamente</em></button>
                </section>
              ) : null}
            </div>
          </section>
        </div>
      ) : null}

      {isDocumentFormOpen ? (
        <div className="modal-backdrop" role="presentation">
          <form className="client-modal document-form-modal" onSubmit={saveDocument}>
            <header className="document-detail-header"><div><p>Control Documental</p><h2>{selectedDocument ? 'Editar documento' : 'Registrar documento'}</h2></div><button className="icon-button" type="button" onClick={() => setIsDocumentFormOpen(false)}><X size={20} /></button></header>
            <div className="document-form-grid">
              <label>Codigo documental<input required maxLength={80} value={documentForm.code} onChange={(event) => setDocumentForm({ ...documentForm, code: event.target.value })} /></label>
              <label>Nombre<input required maxLength={255} value={documentForm.name} onChange={(event) => setDocumentForm({ ...documentForm, name: event.target.value })} /></label>
              <label>Tipo<select value={documentForm.document_type} onChange={(event) => setDocumentForm({ ...documentForm, document_type: event.target.value })}>{documentTypes.map((type) => <option key={type} value={type}>{typeLabels[type]}</option>)}</select></label>
              <label>Nivel de calidad<input value={documentForm.quality_level} onChange={(event) => setDocumentForm({ ...documentForm, quality_level: event.target.value })} /></label>
              {selectedDocument ? (
                <>
                  <label>Estado<select value={documentForm.status} onChange={(event) => setDocumentForm({ ...documentForm, status: event.target.value })}><option value="draft">Borrador</option><option value="active">Vigente</option><option value="obsolete">Obsoleto</option><option value="suspended">Suspendido</option></select></label>
                  <label>Revision vigente<input value={documentForm.current_revision} onChange={(event) => setDocumentForm({ ...documentForm, current_revision: event.target.value })} /></label>
                  <label>Fecha de emision<input type="date" value={documentForm.issue_date} onChange={(event) => setDocumentForm({ ...documentForm, issue_date: event.target.value })} /></label>
                  <label>Ultima revision<input type="date" value={documentForm.last_review_date} onChange={(event) => setDocumentForm({ ...documentForm, last_review_date: event.target.value })} /></label>
                  <label>Entrada en vigor<input type="date" value={documentForm.effective_date} onChange={(event) => setDocumentForm({ ...documentForm, effective_date: event.target.value })} /></label>
                  <label>Retencion<input value={documentForm.retention_time} onChange={(event) => setDocumentForm({ ...documentForm, retention_time: event.target.value })} /></label>
                  <label className="document-form-wide">Ubicacion digital<input value={documentForm.digital_location} onChange={(event) => setDocumentForm({ ...documentForm, digital_location: event.target.value })} /></label>
                </>
              ) : null}
              <label className="document-form-wide">Descripcion<textarea rows={4} value={documentForm.description} onChange={(event) => setDocumentForm({ ...documentForm, description: event.target.value })} /></label>
            </div>
            <footer className="document-form-actions"><button className="ghost-button" type="button" onClick={() => setIsDocumentFormOpen(false)}>Cancelar</button><button className="primary-button" type="submit" disabled={isSaving}>{isSaving ? 'Guardando...' : selectedDocument ? 'Guardar cambios' : 'Registrar documento'}</button></footer>
          </form>
        </div>
      ) : null}

      {isVersionFormOpen ? (
        <div className="modal-backdrop" role="presentation">
          <form className="client-modal document-form-modal document-version-form-modal" onSubmit={saveVersion}>
            <header className="document-detail-header"><div><p>{selectedDocument.code}</p><h2>Registrar version documental</h2></div><button className="icon-button" type="button" onClick={() => setIsVersionFormOpen(false)}><X size={20} /></button></header>
            <p className="document-reference-note">Registra la referencia documental asociada a esta revision. La gestion del archivo se habilitara proximamente.</p>
            <div className="document-form-grid">
              <label>Revision<input required maxLength={80} value={versionForm.revision} onChange={(event) => setVersionForm({ ...versionForm, revision: event.target.value })} /></label>
              <label>Estado inicial<select value={versionForm.status} onChange={(event) => setVersionForm({ ...versionForm, status: event.target.value })}><option value="draft">Borrador</option><option value="active">Activar al registrar</option></select></label>
              <label>Ruta de referencia<input value={versionForm.file_path} onChange={(event) => setVersionForm({ ...versionForm, file_path: event.target.value })} /></label>
              <label>Nombre original<input value={versionForm.original_filename} onChange={(event) => setVersionForm({ ...versionForm, original_filename: event.target.value })} /></label>
              <label>Tipo MIME<input value={versionForm.mime_type} onChange={(event) => setVersionForm({ ...versionForm, mime_type: event.target.value })} /></label>
              <label>Checksum de referencia<input value={versionForm.checksum} onChange={(event) => setVersionForm({ ...versionForm, checksum: event.target.value })} /></label>
              <label>Entrada en vigor<input type="date" value={versionForm.effective_date} onChange={(event) => setVersionForm({ ...versionForm, effective_date: event.target.value })} /></label>
              <label>ID de revisor<input inputMode="numeric" value={versionForm.reviewed_by_id} onChange={(event) => setVersionForm({ ...versionForm, reviewed_by_id: event.target.value })} /></label>
              <label className="document-form-wide">Resumen de cambios<textarea rows={4} value={versionForm.change_summary} onChange={(event) => setVersionForm({ ...versionForm, change_summary: event.target.value })} /></label>
            </div>
            <footer className="document-form-actions"><button className="ghost-button" type="button" onClick={() => setIsVersionFormOpen(false)}>Cancelar</button><button className="primary-button" type="submit" disabled={isSaving}>{isSaving ? 'Registrando...' : 'Registrar version'}</button></footer>
          </form>
        </div>
      ) : null}

      {isMasterFormOpen ? <div className="modal-backdrop"><form className="client-modal document-form-modal" onSubmit={saveMaster}><header className="document-detail-header"><div><p>Control Documental</p><h2>Nueva Plantilla Maestra</h2></div><button className="icon-button" onClick={() => setIsMasterFormOpen(false)} type="button"><X size={20} /></button></header><div className="document-form-grid"><label>Código<input required value={masterForm.code} onChange={(event) => setMasterForm({ ...masterForm, code: event.target.value })} /></label><label>Nombre<input required value={masterForm.name} onChange={(event) => setMasterForm({ ...masterForm, name: event.target.value })} /></label><label>Versión<input required value={masterForm.revision} onChange={(event) => setMasterForm({ ...masterForm, revision: event.target.value })} /></label><label>Inicio de vigencia<input required type="date" value={masterForm.effectiveDate} onChange={(event) => setMasterForm({ ...masterForm, effectiveDate: event.target.value })} /></label><label>Caducidad<input type="date" value={masterForm.expiresOn} onChange={(event) => setMasterForm({ ...masterForm, expiresOn: event.target.value })} /></label><label>Archivo XLSX<input accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" required type="file" onChange={(event) => setMasterForm({ ...masterForm, file: event.target.files?.[0] || null })} /></label><label className="document-form-wide">Descripción<textarea rows={3} value={masterForm.description} onChange={(event) => setMasterForm({ ...masterForm, description: event.target.value })} /></label></div><footer className="document-form-actions"><button className="ghost-button" onClick={() => setIsMasterFormOpen(false)} type="button">Cancelar</button><button aria-label="Guardar Plantilla Maestra" className="primary-button" disabled={isSaving} title="Guardar Plantilla Maestra" type="submit">{isSaving ? 'Guardando...' : <Plus size={17} />}</button></footer></form></div> : null}

      <ConfirmDialog
        cancelText={confirmDialog?.cancelText}
        confirmText={confirmDialog?.confirmText}
        isLoading={confirmDialog?.isConfirming}
        isOpen={Boolean(confirmDialog)}
        message={confirmDialog?.message}
        onClose={closeConfirm}
        onConfirm={handleConfirm}
        title={confirmDialog?.title}
        variant={confirmDialog?.variant}
      />
    </section>
  );
}

export default DocumentLibraryPage;
