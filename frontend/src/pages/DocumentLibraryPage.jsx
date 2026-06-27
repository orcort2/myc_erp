import { BookOpenCheck, Check, FilePlus2, Plus, Search } from 'lucide-react';
import React, { useEffect, useMemo, useState } from 'react';

import {
  activateControlledDocumentVersion,
  approveDocumentInterpretation,
  approveTechnicalProfile,
  createControlledDocument,
  createControlledDocumentVersion,
  createDocumentInterpretation,
  createTechnicalProfile,
  listControlledDocuments,
  listDocumentInterpretations,
  listTechnicalProfiles,
  resolveTechnicalProfiles,
  updateControlledDocument,
  updateDocumentInterpretation,
  updateTechnicalProfile
} from '../services/api.js';

const emptyDocumentForm = {
  code: '',
  name: '',
  document_type: 'procedure',
  quality_level: '',
  current_revision: '',
  issue_date: '',
  last_review_date: '',
  effective_date: '',
  retention_time: '',
  digital_location: '',
  status: 'draft',
  description: ''
};

const emptyVersionForm = {
  documentId: '',
  revision: '',
  file_path: '',
  original_filename: '',
  mime_type: '',
  checksum: '',
  change_summary: '',
  effective_date: '',
  status: 'draft'
};

const emptyInterpretationForm = {
  id: null,
  document_id: '',
  document_version_id: '',
  name: '',
  interpretation_type: 'procedure_interpretation',
  magnitude: '',
  equipment_type: '',
  service_type: 'calibration',
  calibration_scope: 'accredited',
  dataText: '{\n  "rules": []\n}',
  status: 'draft'
};

const emptyProfileForm = {
  id: null,
  code: '',
  name: '',
  magnitude: '',
  equipment_type: '',
  service_type: 'calibration',
  calibration_scope: 'accredited',
  procedure_document_id: '',
  procedure_interpretation_id: '',
  field_sheet_template_document_id: '',
  certificate_template_document_id: '',
  uncertainty_source_document_id: '',
  rulesText: '{\n  "validation": []\n}',
  notes: '',
  status: 'draft'
};

const documentTypes = [
  'manual',
  'procedure',
  'format',
  'record',
  'policy',
  'uncertainty_calculation',
  'certificate_master',
  'field_sheet_template',
  'work_order_template',
  'quotation_template',
  'external_standard',
  'other'
];

function nullable(value) {
  return value === '' || value === undefined ? null : value;
}

function parseJson(text, label) {
  if (!text.trim()) return null;
  try {
    return JSON.parse(text);
  } catch {
    throw new Error(`${label} no es JSON valido.`);
  }
}

function compactDate(value) {
  if (!value) return 'Sin fecha';
  return new Date(value).toLocaleDateString('es-MX');
}

function DocumentLibraryPage() {
  const [activeTab, setActiveTab] = useState('documents');
  const [documents, setDocuments] = useState([]);
  const [interpretations, setInterpretations] = useState([]);
  const [profiles, setProfiles] = useState([]);
  const [documentForm, setDocumentForm] = useState(emptyDocumentForm);
  const [editingDocumentId, setEditingDocumentId] = useState(null);
  const [versionForm, setVersionForm] = useState(emptyVersionForm);
  const [interpretationForm, setInterpretationForm] = useState(emptyInterpretationForm);
  const [profileForm, setProfileForm] = useState(emptyProfileForm);
  const [resolveForm, setResolveForm] = useState({
    magnitude: '',
    equipment_type: '',
    service_type: 'calibration',
    calibration_scope: 'accredited'
  });
  const [resolvedProfiles, setResolvedProfiles] = useState([]);
  const [filters, setFilters] = useState({ q: '', status: '', document_type: '' });
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [isLoading, setIsLoading] = useState(true);

  const activeDocuments = useMemo(
    () => documents.filter((item) => item.status === 'active').length,
    [documents]
  );
  const approvedInterpretations = useMemo(
    () => interpretations.filter((item) => item.status === 'approved').length,
    [interpretations]
  );
  const activeProfiles = useMemo(
    () => profiles.filter((item) => item.status === 'active').length,
    [profiles]
  );

  async function loadData() {
    setError('');
    setIsLoading(true);
    try {
      const [docsResult, interpretationsResult, profilesResult] = await Promise.all([
        listControlledDocuments(filters),
        listDocumentInterpretations(),
        listTechnicalProfiles()
      ]);
      setDocuments(Array.isArray(docsResult) ? docsResult : []);
      setInterpretations(Array.isArray(interpretationsResult) ? interpretationsResult : []);
      setProfiles(Array.isArray(profilesResult) ? profilesResult : []);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  function editDocument(item) {
    setEditingDocumentId(item.id);
    setDocumentForm({
      code: item.code ?? '',
      name: item.name ?? '',
      document_type: item.document_type ?? 'other',
      quality_level: item.quality_level ?? '',
      current_revision: item.current_revision ?? '',
      issue_date: item.issue_date ?? '',
      last_review_date: item.last_review_date ?? '',
      effective_date: item.effective_date ?? '',
      retention_time: item.retention_time ?? '',
      digital_location: item.digital_location ?? '',
      status: item.status ?? 'draft',
      description: item.description ?? ''
    });
    setVersionForm((current) => ({ ...current, documentId: item.id }));
  }

  async function saveDocument(event) {
    event.preventDefault();
    setError('');
    try {
      const payload = {
        ...documentForm,
        quality_level: nullable(documentForm.quality_level),
        current_revision: nullable(documentForm.current_revision),
        issue_date: nullable(documentForm.issue_date),
        last_review_date: nullable(documentForm.last_review_date),
        effective_date: nullable(documentForm.effective_date),
        retention_time: nullable(documentForm.retention_time),
        digital_location: nullable(documentForm.digital_location),
        description: nullable(documentForm.description)
      };
      await (editingDocumentId
        ? updateControlledDocument(editingDocumentId, payload)
        : createControlledDocument(payload));
      setDocumentForm(emptyDocumentForm);
      setEditingDocumentId(null);
      setNotice(editingDocumentId ? 'Documento actualizado' : 'Documento creado');
      await loadData();
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  async function saveVersion(event) {
    event.preventDefault();
    setError('');
    try {
      await createControlledDocumentVersion(versionForm.documentId, {
        revision: versionForm.revision,
        file_path: nullable(versionForm.file_path),
        original_filename: nullable(versionForm.original_filename),
        mime_type: nullable(versionForm.mime_type),
        checksum: nullable(versionForm.checksum),
        change_summary: nullable(versionForm.change_summary),
        effective_date: nullable(versionForm.effective_date),
        status: versionForm.status
      });
      setVersionForm(emptyVersionForm);
      setNotice('Version registrada');
      await loadData();
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  async function activateVersion(documentId, versionId) {
    setError('');
    try {
      await activateControlledDocumentVersion(documentId, versionId);
      setNotice('Version activa actualizada');
      await loadData();
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  function editInterpretation(item) {
    setInterpretationForm({
      id: item.id,
      document_id: item.document_id,
      document_version_id: item.document_version_id ?? '',
      name: item.name ?? '',
      interpretation_type: item.interpretation_type ?? 'general',
      magnitude: item.magnitude ?? '',
      equipment_type: item.equipment_type ?? '',
      service_type: item.service_type ?? 'calibration',
      calibration_scope: item.calibration_scope ?? 'accredited',
      dataText: JSON.stringify(item.data ?? {}, null, 2),
      status: item.status ?? 'draft'
    });
  }

  async function saveInterpretation(event) {
    event.preventDefault();
    setError('');
    try {
      const payload = {
        document_id: Number(interpretationForm.document_id),
        document_version_id: interpretationForm.document_version_id ? Number(interpretationForm.document_version_id) : null,
        name: interpretationForm.name,
        interpretation_type: interpretationForm.interpretation_type,
        magnitude: nullable(interpretationForm.magnitude),
        equipment_type: nullable(interpretationForm.equipment_type),
        service_type: nullable(interpretationForm.service_type),
        calibration_scope: nullable(interpretationForm.calibration_scope),
        data: parseJson(interpretationForm.dataText, 'Data'),
        status: interpretationForm.status
      };
      await (interpretationForm.id
        ? updateDocumentInterpretation(interpretationForm.id, payload)
        : createDocumentInterpretation(payload));
      setInterpretationForm(emptyInterpretationForm);
      setNotice('Interpretacion guardada');
      await loadData();
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  async function approveInterpretation(item) {
    setError('');
    try {
      await approveDocumentInterpretation(item.id);
      setNotice('Interpretacion aprobada');
      await loadData();
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  function editProfile(item) {
    setProfileForm({
      id: item.id,
      code: item.code ?? '',
      name: item.name ?? '',
      magnitude: item.magnitude ?? '',
      equipment_type: item.equipment_type ?? '',
      service_type: item.service_type ?? 'calibration',
      calibration_scope: item.calibration_scope ?? 'accredited',
      procedure_document_id: item.procedure_document_id ?? '',
      procedure_interpretation_id: item.procedure_interpretation_id ?? '',
      field_sheet_template_document_id: item.field_sheet_template_document_id ?? '',
      certificate_template_document_id: item.certificate_template_document_id ?? '',
      uncertainty_source_document_id: item.uncertainty_source_document_id ?? '',
      rulesText: JSON.stringify(item.rules ?? {}, null, 2),
      notes: item.notes ?? '',
      status: item.status ?? 'draft'
    });
  }

  async function saveProfile(event) {
    event.preventDefault();
    setError('');
    try {
      const payload = {
        code: profileForm.code,
        name: profileForm.name,
        magnitude: profileForm.magnitude,
        equipment_type: profileForm.equipment_type,
        service_type: profileForm.service_type,
        calibration_scope: profileForm.calibration_scope,
        procedure_document_id: profileForm.procedure_document_id ? Number(profileForm.procedure_document_id) : null,
        procedure_interpretation_id: profileForm.procedure_interpretation_id ? Number(profileForm.procedure_interpretation_id) : null,
        field_sheet_template_document_id: profileForm.field_sheet_template_document_id ? Number(profileForm.field_sheet_template_document_id) : null,
        certificate_template_document_id: profileForm.certificate_template_document_id ? Number(profileForm.certificate_template_document_id) : null,
        uncertainty_source_document_id: profileForm.uncertainty_source_document_id ? Number(profileForm.uncertainty_source_document_id) : null,
        rules: parseJson(profileForm.rulesText, 'Rules'),
        notes: nullable(profileForm.notes),
        status: profileForm.status,
        allowed_patterns: []
      };
      await (profileForm.id
        ? updateTechnicalProfile(profileForm.id, payload)
        : createTechnicalProfile(payload));
      setProfileForm(emptyProfileForm);
      setNotice('Perfil tecnico guardado');
      await loadData();
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  async function approveProfile(item) {
    setError('');
    try {
      await approveTechnicalProfile(item.id);
      setNotice('Perfil tecnico aprobado');
      await loadData();
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  async function resolveProfiles(event) {
    event.preventDefault();
    setError('');
    try {
      const result = await resolveTechnicalProfiles(resolveForm);
      setResolvedProfiles(Array.isArray(result) ? result : []);
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  return (
    <section className="module-workspace document-library-workspace">
      <div className="module-workspace__hero clients-hero">
        <span className="module-workspace__icon">
          <BookOpenCheck size={28} />
        </span>
        <div>
          <p>Sistema de calidad</p>
          <h1>Biblioteca Documental</h1>
          <span>Documentos controlados, interpretaciones ejecutables y perfiles tecnicos de calibracion.</span>
        </div>
      </div>

      {error ? <div className="form-error dashboard-error">{error}</div> : null}
      {notice ? <div className="form-notice dashboard-error">{notice}</div> : null}

      <section className="operations-band certificates-summary">
        <div className="operations-band__metric">
          <strong>{isLoading ? '-' : documents.length}</strong>
          <span>Documentos</span>
        </div>
        <div className="operations-band__metric">
          <strong>{isLoading ? '-' : activeDocuments}</strong>
          <span>Activos</span>
        </div>
        <div className="operations-band__metric">
          <strong>{isLoading ? '-' : approvedInterpretations}</strong>
          <span>Interpretaciones aprobadas</span>
        </div>
        <div className="operations-band__metric">
          <strong>{isLoading ? '-' : activeProfiles}</strong>
          <span>Perfiles activos</span>
        </div>
      </section>

      <div className="module-tabs" role="tablist" aria-label="Biblioteca documental">
        {[
          ['documents', 'Documentos'],
          ['interpretations', 'Interpretaciones'],
          ['profiles', 'Perfiles Tecnicos']
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

      {activeTab === 'documents' ? (
        <div className="document-library-grid">
          <section className="clients-list-panel">
            <div className="section-heading">
              <div>
                <p>Lista maestra</p>
                <h2>{documents.length} documentos</h2>
              </div>
              <div className="toolbar-actions document-library-filters">
                <input placeholder="Buscar" value={filters.q} onChange={(event) => setFilters({ ...filters, q: event.target.value })} />
                <select value={filters.document_type} onChange={(event) => setFilters({ ...filters, document_type: event.target.value })}>
                  <option value="">Tipo</option>
                  {documentTypes.map((type) => <option key={type} value={type}>{type}</option>)}
                </select>
                <select value={filters.status} onChange={(event) => setFilters({ ...filters, status: event.target.value })}>
                  <option value="">Estado</option>
                  <option value="draft">draft</option>
                  <option value="active">active</option>
                  <option value="obsolete">obsolete</option>
                  <option value="suspended">suspended</option>
                </select>
                <button type="button" className="secondary-button" onClick={loadData}><Search size={16} /> Filtrar</button>
              </div>
            </div>
            <div className="clients-table certificates-table">
              <table>
                <thead>
                  <tr>
                    <th>Codigo</th>
                    <th>Nombre</th>
                    <th>Tipo</th>
                    <th>Revision</th>
                    <th>Estado</th>
                    <th>Nivel</th>
                    <th>Ultima revision</th>
                    <th>Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {documents.map((item) => (
                    <tr key={item.id}>
                      <td>{item.code}</td>
                      <td>{item.name}</td>
                      <td>{item.document_type}</td>
                      <td>{item.current_revision ?? 'Sin revision'}</td>
                      <td><span className={`status-pill status-pill--${item.status}`}>{item.status}</span></td>
                      <td>{item.quality_level ?? '-'}</td>
                      <td>{compactDate(item.last_review_date)}</td>
                      <td><button type="button" className="ghost-button" onClick={() => editDocument(item)}>Editar</button></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className="clients-list-panel document-library-panel">
            <form className="document-library-form" onSubmit={saveDocument}>
              <div className="section-heading"><div><p>Metadata</p><h2>{editingDocumentId ? 'Editar documento' : 'Nuevo documento'}</h2></div></div>
              <input required placeholder="Codigo" value={documentForm.code} onChange={(event) => setDocumentForm({ ...documentForm, code: event.target.value })} />
              <input required placeholder="Nombre" value={documentForm.name} onChange={(event) => setDocumentForm({ ...documentForm, name: event.target.value })} />
              <select value={documentForm.document_type} onChange={(event) => setDocumentForm({ ...documentForm, document_type: event.target.value })}>
                {documentTypes.map((type) => <option key={type} value={type}>{type}</option>)}
              </select>
              <input placeholder="Nivel de calidad" value={documentForm.quality_level} onChange={(event) => setDocumentForm({ ...documentForm, quality_level: event.target.value })} />
              <input placeholder="Revision vigente" value={documentForm.current_revision} onChange={(event) => setDocumentForm({ ...documentForm, current_revision: event.target.value })} />
              <select value={documentForm.status} onChange={(event) => setDocumentForm({ ...documentForm, status: event.target.value })}>
                <option value="draft">draft</option>
                <option value="active">active</option>
                <option value="obsolete">obsolete</option>
                <option value="suspended">suspended</option>
              </select>
              <textarea rows={3} placeholder="Descripcion" value={documentForm.description} onChange={(event) => setDocumentForm({ ...documentForm, description: event.target.value })} />
              <button className="primary-button" type="submit"><Plus size={16} /> Guardar documento</button>
            </form>

            <form className="document-library-form" onSubmit={saveVersion}>
              <div className="section-heading"><div><p>Versiones</p><h2>Registrar version</h2></div></div>
              <select required value={versionForm.documentId} onChange={(event) => setVersionForm({ ...versionForm, documentId: event.target.value })}>
                <option value="">Documento</option>
                {documents.map((item) => <option key={item.id} value={item.id}>{item.code} - {item.name}</option>)}
              </select>
              <input required placeholder="Revision" value={versionForm.revision} onChange={(event) => setVersionForm({ ...versionForm, revision: event.target.value })} />
              <input placeholder="Ruta de archivo" value={versionForm.file_path} onChange={(event) => setVersionForm({ ...versionForm, file_path: event.target.value })} />
              <input placeholder="Nombre original" value={versionForm.original_filename} onChange={(event) => setVersionForm({ ...versionForm, original_filename: event.target.value })} />
              <textarea rows={2} placeholder="Resumen de cambio" value={versionForm.change_summary} onChange={(event) => setVersionForm({ ...versionForm, change_summary: event.target.value })} />
              <select value={versionForm.status} onChange={(event) => setVersionForm({ ...versionForm, status: event.target.value })}>
                <option value="draft">draft</option>
                <option value="active">active</option>
              </select>
              <button className="secondary-button" type="submit"><FilePlus2 size={16} /> Registrar version</button>
            </form>

            <div className="document-version-list">
              {documents.flatMap((doc) => doc.versions.map((version) => (
                <button key={`${doc.id}-${version.id}`} type="button" onClick={() => activateVersion(doc.id, version.id)}>
                  <span>{doc.code} rev. {version.revision}</span>
                  <strong>{version.status}</strong>
                </button>
              )))}
            </div>
          </section>
        </div>
      ) : null}

      {activeTab === 'interpretations' ? (
        <div className="document-library-grid">
          <section className="clients-list-panel">
            <div className="section-heading"><div><p>Interpretacion ejecutable</p><h2>{interpretations.length} interpretaciones</h2></div></div>
            <div className="clients-table certificates-table">
              <table>
                <thead><tr><th>Nombre</th><th>Tipo</th><th>Magnitud</th><th>Equipo</th><th>Estado</th><th>Version</th><th>Acciones</th></tr></thead>
                <tbody>
                  {interpretations.map((item) => (
                    <tr key={item.id}>
                      <td>{item.name}</td>
                      <td>{item.interpretation_type}</td>
                      <td>{item.magnitude ?? '-'}</td>
                      <td>{item.equipment_type ?? '-'}</td>
                      <td><span className={`status-pill status-pill--${item.status}`}>{item.status}</span></td>
                      <td>{item.version}</td>
                      <td>
                        <button type="button" className="ghost-button" onClick={() => editInterpretation(item)}>Editar</button>
                        <button type="button" className="ghost-button" onClick={() => approveInterpretation(item)}><Check size={14} /> Aprobar</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
          <section className="clients-list-panel document-library-panel">
            <form className="document-library-form" onSubmit={saveInterpretation}>
              <div className="section-heading"><div><p>Captura</p><h2>{interpretationForm.id ? 'Editar interpretacion' : 'Nueva interpretacion'}</h2></div></div>
              <select required value={interpretationForm.document_id} onChange={(event) => setInterpretationForm({ ...interpretationForm, document_id: event.target.value, document_version_id: '' })}>
                <option value="">Documento</option>
                {documents.map((item) => <option key={item.id} value={item.id}>{item.code} - {item.name}</option>)}
              </select>
              <input required placeholder="Nombre" value={interpretationForm.name} onChange={(event) => setInterpretationForm({ ...interpretationForm, name: event.target.value })} />
              <input placeholder="Magnitud" value={interpretationForm.magnitude} onChange={(event) => setInterpretationForm({ ...interpretationForm, magnitude: event.target.value })} />
              <input placeholder="Tipo de equipo" value={interpretationForm.equipment_type} onChange={(event) => setInterpretationForm({ ...interpretationForm, equipment_type: event.target.value })} />
              <select value={interpretationForm.interpretation_type} onChange={(event) => setInterpretationForm({ ...interpretationForm, interpretation_type: event.target.value })}>
                <option value="procedure_interpretation">procedure_interpretation</option>
                <option value="uncertainty_model_source">uncertainty_model_source</option>
                <option value="certificate_template_source">certificate_template_source</option>
                <option value="field_sheet_template_source">field_sheet_template_source</option>
                <option value="general">general</option>
              </select>
              <textarea rows={7} value={interpretationForm.dataText} onChange={(event) => setInterpretationForm({ ...interpretationForm, dataText: event.target.value })} />
              <button className="primary-button" type="submit"><Plus size={16} /> Guardar interpretacion</button>
            </form>
          </section>
        </div>
      ) : null}

      {activeTab === 'profiles' ? (
        <div className="document-library-grid">
          <section className="clients-list-panel">
            <div className="section-heading"><div><p>Perfil tecnico de calibracion</p><h2>{profiles.length} perfiles</h2></div></div>
            <div className="clients-table certificates-table">
              <table>
                <thead><tr><th>Codigo</th><th>Nombre</th><th>Magnitud</th><th>Equipo</th><th>Alcance</th><th>Estado</th><th>Acciones</th></tr></thead>
                <tbody>
                  {profiles.map((item) => (
                    <tr key={item.id}>
                      <td>{item.code}</td>
                      <td>{item.name}</td>
                      <td>{item.magnitude}</td>
                      <td>{item.equipment_type}</td>
                      <td>{item.calibration_scope}</td>
                      <td><span className={`status-pill status-pill--${item.status}`}>{item.status}</span></td>
                      <td>
                        <button type="button" className="ghost-button" onClick={() => editProfile(item)}>Editar</button>
                        <button type="button" className="ghost-button" onClick={() => approveProfile(item)}><Check size={14} /> Aprobar</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
          <section className="clients-list-panel document-library-panel">
            <form className="document-library-form" onSubmit={saveProfile}>
              <div className="section-heading"><div><p>Configuracion</p><h2>{profileForm.id ? 'Editar perfil' : 'Nuevo perfil'}</h2></div></div>
              <input required placeholder="Codigo" value={profileForm.code} onChange={(event) => setProfileForm({ ...profileForm, code: event.target.value })} />
              <input required placeholder="Nombre" value={profileForm.name} onChange={(event) => setProfileForm({ ...profileForm, name: event.target.value })} />
              <input required placeholder="Magnitud" value={profileForm.magnitude} onChange={(event) => setProfileForm({ ...profileForm, magnitude: event.target.value })} />
              <input required placeholder="Tipo de equipo" value={profileForm.equipment_type} onChange={(event) => setProfileForm({ ...profileForm, equipment_type: event.target.value })} />
              <select value={profileForm.calibration_scope} onChange={(event) => setProfileForm({ ...profileForm, calibration_scope: event.target.value })}>
                <option value="accredited">accredited</option>
                <option value="traceable">traceable</option>
                <option value="linked_lab">linked_lab</option>
                <option value="special">special</option>
              </select>
              <select value={profileForm.procedure_document_id} onChange={(event) => setProfileForm({ ...profileForm, procedure_document_id: event.target.value })}>
                <option value="">Procedimiento documental</option>
                {documents.map((item) => <option key={item.id} value={item.id}>{item.code}</option>)}
              </select>
              <textarea rows={6} value={profileForm.rulesText} onChange={(event) => setProfileForm({ ...profileForm, rulesText: event.target.value })} />
              <button className="primary-button" type="submit"><Plus size={16} /> Guardar perfil</button>
            </form>
            <form className="document-library-form" onSubmit={resolveProfiles}>
              <div className="section-heading"><div><p>Resolver</p><h2>Perfil aplicable</h2></div></div>
              <input required placeholder="Magnitud" value={resolveForm.magnitude} onChange={(event) => setResolveForm({ ...resolveForm, magnitude: event.target.value })} />
              <input required placeholder="Tipo de equipo" value={resolveForm.equipment_type} onChange={(event) => setResolveForm({ ...resolveForm, equipment_type: event.target.value })} />
              <select value={resolveForm.calibration_scope} onChange={(event) => setResolveForm({ ...resolveForm, calibration_scope: event.target.value })}>
                <option value="accredited">accredited</option>
                <option value="traceable">traceable</option>
                <option value="linked_lab">linked_lab</option>
                <option value="special">special</option>
              </select>
              <button className="secondary-button" type="submit"><Search size={16} /> Resolver</button>
              <div className="document-version-list">
                {resolvedProfiles.map((item) => <span key={item.id}>{item.code} - {item.name}</span>)}
              </div>
            </form>
          </section>
        </div>
      ) : null}
    </section>
  );
}

export default DocumentLibraryPage;
