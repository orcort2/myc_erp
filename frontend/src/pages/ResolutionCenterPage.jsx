import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Clock3,
  Eye,
  FileSearch,
  Filter,
  LoaderCircle,
  Network,
  Plus,
  RefreshCw,
  Search,
  ShieldCheck,
  X
} from 'lucide-react';
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import ResolutionActivityPanel from '../components/activity/ResolutionActivityPanel.jsx';

import {
  createCenterResolution,
  getCenterResolution,
  getResolutionCenterCapabilities,
  getResolutionCenterIndicators,
  listCenterResolutions,
  listResolutionDefinitions,
  runCenterResolutionStage
} from '../services/api.js';
import {
  ACTIVE_RESOLUTION_STATES,
  buildResolutionParameters,
  canRunResolutionStage,
  resolutionParameterFields,
  shouldPollResolutions
} from '../utils/resolutionCenter.js';
import './resolution-center.css';

const STAGE_LABELS = {
  'prepare-context': 'Preparar contexto',
  analyze: 'Analizar',
  'build-plan': 'Construir plan',
  simulate: 'Simular',
  authorize: 'Autorizar',
  execute: 'Enviar a ejecución'
};

function badgeTone(status = '') {
  if (['completed', 'succeeded', 'compensated', 'success'].includes(status)) return 'success';
  if (['blocked', 'failed', 'compensation_failed'].includes(status)) return 'danger';
  if (['retry_wait', 'pending_authorization', 'revalidating'].includes(status)) return 'warning';
  if (['claimed', 'executing', 'ready_for_execution'].includes(status)) return 'info';
  return 'neutral';
}

function StatusBadge({ children }) {
  return <span className={`resolution-badge resolution-badge--${badgeTone(children)}`}>{children || '—'}</span>;
}

function formatDate(value) {
  return value ? new Intl.DateTimeFormat('es-MX', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value)) : '—';
}

function formatDuration(seconds) {
  if (seconds === null || seconds === undefined) return '—';
  if (seconds < 60) return `${seconds} s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)} min`;
  return `${Math.floor(seconds / 3600)} h ${Math.floor((seconds % 3600) / 60)} min`;
}

function DynamicParameterField({ definition, name, onChange, value }) {
  const schema = definition.parameter_schema.properties[name];
  const required = definition.parameter_schema.required?.includes(name);
  const common = {
    id: `resolution-parameter-${name}`,
    maxLength: schema.maxLength,
    minLength: schema.minLength,
    onChange: (event) => onChange(name, event.target.value),
    placeholder: schema.placeholder,
    required,
    value: value ?? ''
  };
  return (
    <label htmlFor={common.id}>
      {schema.title || name}
      {schema['ui:widget'] === 'textarea'
        ? <textarea {...common} rows={schema['ui:rows'] || 3} />
        : schema.enum
          ? <select {...common}>{schema.enum.map((option) => <option key={option} value={option}>{option}</option>)}</select>
          : <input {...common} type={schema.type === 'number' || schema.type === 'integer' ? 'number' : 'text'} />}
      {schema.description ? <small>{schema.description}</small> : null}
    </label>
  );
}

function CreateResolutionDialog({ definitions, onClose, onCreated }) {
  const [definitionKey, setDefinitionKey] = useState(
    definitions[0] ? `${definitions[0].resolution_type}@${definitions[0].version}` : ''
  );
  const definition = definitions.find(
    (item) => `${item.resolution_type}@${item.version}` === definitionKey
  ) ?? definitions[0];
  const [form, setForm] = useState({
    subject_id: '',
    title: definitions[0]?.labels?.create_title || '',
    priority: 'normal',
    parameters: {}
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const parameterFields = resolutionParameterFields(definition);

  function selectDefinition(value) {
    const selected = definitions.find(
      (item) => `${item.resolution_type}@${item.version}` === value
    );
    setDefinitionKey(value);
    setForm((current) => ({
      ...current,
      title: selected?.labels?.create_title || '',
      parameters: {}
    }));
  }

  function setParameter(name, value) {
    setForm((current) => ({
      ...current,
      parameters: { ...current.parameters, [name]: value }
    }));
  }

  async function submit(event) {
    event.preventDefault();
    if (!definition) return;
    setSubmitting(true);
    setError('');
    try {
      const payload = {
        resolution_type: definition.resolution_type,
        definition_version: definition.version,
        subject_type: definition.object_type,
        subject_id: form.subject_id.trim(),
        title: form.title.trim(),
        reason: String(form.parameters.reason || form.title).trim(),
        priority: form.priority,
        parameters: buildResolutionParameters(definition, form.parameters)
      };
      const created = await createCenterResolution(payload, crypto.randomUUID());
      onCreated(created.public_id);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="resolution-modal-layer" role="presentation">
      <form className="resolution-create-dialog" onSubmit={submit}>
        <header>
          <div>
            <span className="resolution-eyebrow">Flujo guiado</span>
            <h2>Nueva resolución</h2>
          </div>
          <button aria-label="Cerrar" className="resolution-icon-button" onClick={onClose} type="button"><X size={19} /></button>
        </header>
        {definition ? (
          <>
            <label>
              Tipo de resolución
              <select onChange={(event) => selectDefinition(event.target.value)} value={definitionKey}>
                {definitions.map((item) => (
                  <option key={`${item.resolution_type}@${item.version}`} value={`${item.resolution_type}@${item.version}`}>
                    {item.name} · v{item.version}
                  </option>
                ))}
              </select>
            </label>
            <section className="resolution-definition-card">
              <ShieldCheck size={22} />
              <div>
                <strong>{definition.name}</strong>
                <p>{definition.description}</p>
                <small>{definition.domain} · v{definition.version} · riesgo {definition.risk_level}</small>
                <small>Simulación: {definition.supports_simulation ? 'sí' : 'no'} · Compensación: {definition.supports_compensation ? 'sí' : 'no'}</small>
              </div>
            </section>
            <div className="resolution-form-grid">
              <label>
                {definition.labels?.subject || definition.object_type}
                <input required onChange={(event) => setForm({ ...form, subject_id: event.target.value })} placeholder={definition.labels?.subject_placeholder || `ID de ${definition.object_type}`} value={form.subject_id} />
              </label>
              <label>
                Prioridad
                <select onChange={(event) => setForm({ ...form, priority: event.target.value })} value={form.priority}>
                  <option value="low">Baja</option>
                  <option value="normal">Normal</option>
                  <option value="high">Alta</option>
                  <option value="critical">Crítica</option>
                </select>
              </label>
            </div>
            <label>
              Título
              <input maxLength="240" required onChange={(event) => setForm({ ...form, title: event.target.value })} value={form.title} />
            </label>
            {parameterFields.map(({ name }) => (
              <DynamicParameterField
                definition={definition}
                key={name}
                name={name}
                onChange={setParameter}
                value={form.parameters[name]}
              />
            ))}
            {definition.warnings?.length ? <aside className="resolution-warning">
              <AlertTriangle size={18} />
              <span>{definition.warnings.join(' ')}</span>
            </aside> : null}
          </>
        ) : <p>No existen definiciones habilitadas.</p>}
        {error ? <p className="resolution-error">{error}</p> : null}
        <footer>
          <button className="secondary-button" onClick={onClose} type="button">Cancelar</button>
          <button className="primary-button" disabled={submitting || !definition} type="submit">
            {submitting ? <LoaderCircle className="spin" size={17} /> : <Plus size={17} />}
            Crear resolución
          </button>
        </footer>
      </form>
    </div>
  );
}

function DetailSection({ title, children }) {
  return <section className="resolution-detail-section"><h3>{title}</h3>{children}</section>;
}

function ResolutionDetailDialog({ capabilities, detail, loading, onClose, onRefresh, onStage }) {
  const [running, setRunning] = useState('');
  const [error, setError] = useState('');

  async function run(stage) {
    setRunning(stage);
    setError('');
    try {
      const payload = stage === 'authorize' ? { comment: 'Autorización desde Centro de Resoluciones' } : null;
      await onStage(stage, payload, stage === 'execute' ? crypto.randomUUID() : null);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setRunning('');
    }
  }

  const available = (detail?.capabilities ?? []).filter(
    (stage) => canRunResolutionStage(stage, capabilities)
  );

  return (
    <div className="resolution-modal-layer">
      <article className="resolution-detail-dialog">
        <header className="resolution-detail-header">
          <div>
            <span className="resolution-eyebrow">Expediente consolidado</span>
            <h2>{detail?.summary.title ?? 'Cargando resolución'}</h2>
            <p>{detail?.summary.public_id}</p>
          </div>
          <div className="resolution-header-actions">
            <button className="resolution-icon-button" onClick={onRefresh} type="button"><RefreshCw size={18} /></button>
            <button className="resolution-icon-button" onClick={onClose} type="button"><X size={20} /></button>
          </div>
        </header>
        {loading || !detail ? (
          <div className="resolution-loading"><LoaderCircle className="spin" /> Cargando expediente…</div>
        ) : (
          <div className="resolution-detail-body">
            <div className="resolution-detail-main">
              <DetailSection title="Resumen">
                <div className="resolution-summary-grid">
                  <span><small>Estado</small><StatusBadge>{detail.summary.lifecycle_status}</StatusBadge></span>
                  <span><small>Ejecución</small><StatusBadge>{detail.summary.distributed_status}</StatusBadge></span>
                  <span><small>Solicitante</small><strong>{detail.summary.requester || '—'}</strong></span>
                  <span><small>Autorizador</small><strong>{detail.summary.authorizer || '—'}</strong></span>
                  <span><small>Creación</small><strong>{formatDate(detail.summary.created_at)}</strong></span>
                  <span><small>Resultado</small><strong>{detail.summary.result || 'Pendiente'}</strong></span>
                </div>
                <p>{detail.description || detail.reason}</p>
              </DetailSection>
              <DetailSection title="Objeto afectado">
                <div className="resolution-object-card">
                  <FileSearch size={20} />
                  <div><strong>{detail.subject.label || `${detail.subject.type} ${detail.subject.id}`}</strong><small>{detail.subject.type} · {detail.subject.id}</small></div>
                  {detail.subject.route ? <a className="secondary-button" href={detail.subject.route}>Abrir objeto</a> : null}
                </div>
              </DetailSection>
              <DetailSection title="Parámetros utilizados">
                <dl className="resolution-result-details">
                  {Object.entries(detail.parameters).map(([key, value]) => (
                    <div key={key}><dt>{key}</dt><dd>{String(value)}</dd></div>
                  ))}
                </dl>
              </DetailSection>
              {detail.analysis ? <DetailSection title="Análisis">
                <div className="resolution-result-card">
                  <ShieldCheck size={21} />
                  <div><strong>{detail.analysis.status}</strong><p>{detail.analysis.findings.join(' · ') || 'Sin hallazgos'}</p></div>
                </div>
                {detail.analysis.blockers.length ? <p className="resolution-error">{detail.analysis.blockers.join(' · ')}</p> : null}
              </DetailSection> : null}
              {detail.plan ? <DetailSection title="Plan y simulación">
                <p><strong>{detail.plan.summary}</strong></p>
                <ul>{detail.plan.steps.map((step) => <li key={step.sequence}>{step.sequence}. {step.description} <StatusBadge>{step.criticality}</StatusBadge></li>)}</ul>
                {detail.simulation ? <div className="resolution-simulation">
                  <strong>Simulación: {detail.simulation.status}</strong>
                  <p>{detail.simulation.expected_changes.join(' · ') || 'Sin cambios previstos'}</p>
                </div> : null}
              </DetailSection> : null}
              <DetailSection title="Línea de tiempo">
                <ol className="resolution-timeline">
                  {detail.lifecycle.map((entry, index) => (
                    <li key={`${entry.occurred_at}-${entry.event_type}-${index}`}>
                      <span className={`resolution-timeline__dot resolution-timeline__dot--${entry.category}`} />
                      <div><strong>{entry.label}</strong><small>{formatDate(entry.occurred_at)}{entry.actor ? ` · ${entry.actor}` : ''}</small></div>
                      {entry.status ? <StatusBadge>{entry.status}</StatusBadge> : null}
                    </li>
                  ))}
                </ol>
              </DetailSection>
              {detail.result ? <DetailSection title="Resultado">
                <div className="resolution-result-card"><CheckCircle2 size={21} /><div><strong>{detail.result.status}</strong><p>{detail.result.summary}</p></div></div>
                <dl className="resolution-result-details">
                  <div><dt>Entidades creadas</dt><dd>{detail.result.created_entities?.length ? detail.result.created_entities.join(' · ') : 'Ninguna'}</dd></div>
                  <div><dt>Entidades modificadas</dt><dd>{detail.result.modified_entities?.length ? detail.result.modified_entities.join(' · ') : 'Ninguna'}</dd></div>
                  <div><dt>Advertencias</dt><dd>{detail.result.warnings?.length ? detail.result.warnings.join(' · ') : 'Ninguna'}</dd></div>
                  <div><dt>Pasos fallidos</dt><dd>{detail.result.failed_steps?.length ? detail.result.failed_steps.join(' · ') : 'Ninguno'}</dd></div>
                </dl>
              </DetailSection> : null}
              <DetailSection title="Ejecución, intentos y recuperación">
                {detail.attempts.length ? <ol className="resolution-evidence-list">
                  {detail.attempts.map((attempt) => (
                    <li key={attempt.attempt_number}>
                      <strong>Intento {attempt.attempt_number}</strong>
                      <StatusBadge>{attempt.status}</StatusBadge>
                      <small>{formatDate(attempt.started_at)}</small>
                    </li>
                  ))}
                </ol> : <p className="resolution-muted">Aún no existen intentos de ejecución.</p>}
                {detail.recovery.map((event, index) => (
                  <p key={`${event.occurred_at}-${index}`}><strong>{event.event_type}</strong> · {formatDate(event.occurred_at)}</p>
                ))}
              </DetailSection>
              <DetailSection title="Compensaciones">
                {detail.compensations.length ? detail.compensations.map((item) => (
                  <div className="resolution-result-card" key={item.plan_id}>
                    <RefreshCw size={20} />
                    <div><strong>{item.strategy}</strong><p>{item.reason}</p><StatusBadge>{item.execution?.status || 'planificada'}</StatusBadge></div>
                  </div>
                )) : <p className="resolution-muted">No se ha requerido compensación.</p>}
              </DetailSection>
              <DetailSection title="Evidencias y auditoría">
                <p className="resolution-muted">Historial append-only · {detail.evidence.security_decisions.length} decisiones · {detail.evidence.context_snapshots.length} snapshots · {detail.evidence.references.length} evidencias</p>
                <ol className="resolution-evidence-list">
                  {detail.evidence.security_decisions.map((decision, index) => (
                    <li key={`${decision.action}-${decision.evaluated_at}-${index}`}>
                      <strong>{decision.action}</strong>
                      <StatusBadge>{decision.outcome}</StatusBadge>
                      <small>{formatDate(decision.evaluated_at)}</small>
                      {decision.evidence_hash ? <code>{decision.evidence_hash}</code> : null}
                    </li>
                  ))}
                  {detail.evidence.context_snapshots.map((snapshot) => (
                    <li key={`snapshot-${snapshot.sequence}`}>
                      <strong>Snapshot {snapshot.snapshot_type} · v{snapshot.version}</strong>
                      <span>Secuencia {snapshot.sequence}</span>
                      <small>{formatDate(snapshot.captured_at)}</small>
                      {snapshot.context_hash ? <code>{snapshot.context_hash}</code> : null}
                    </li>
                  ))}
                  {detail.evidence.revalidations.map((item, index) => (
                    <li key={`revalidation-${item.revalidated_at}-${index}`}>
                      <strong>Revalidación</strong>
                      <StatusBadge>{item.outcome}</StatusBadge>
                      <small>{formatDate(item.revalidated_at)}</small>
                      {item.revalidation_hash ? <code>{item.revalidation_hash}</code> : null}
                    </li>
                  ))}
                </ol>
              </DetailSection>
              <DetailSection title="Actividad interna">
                <ResolutionActivityPanel publicId={detail.summary.public_id} />
              </DetailSection>
            </div>
            <aside className="resolution-detail-aside">
              <h3>Operación</h3>
              {available.length ? available.map((stage) => (
                <button disabled={Boolean(running)} key={stage} onClick={() => run(stage)} type="button">
                  {running === stage ? <LoaderCircle className="spin" size={17} /> : <ArrowRight size={17} />}
                  {STAGE_LABELS[stage]}
                </button>
              )) : <p>Sin acciones disponibles en el estado actual.</p>}
              {error ? <p className="resolution-error">{error}</p> : null}
              <hr />
              <h3>Estado distribuido</h3>
              {detail.distributed ? (
                <dl>
                  <div><dt>Estado</dt><dd><StatusBadge>{detail.distributed.status}</StatusBadge></dd></div>
                  <div><dt>Intentos</dt><dd>{detail.distributed.attempt_count}/{detail.distributed.max_attempts}</dd></div>
                  {detail.distributed.worker ? <div><dt>Worker</dt><dd>{detail.distributed.worker}</dd></div> : null}
                  {detail.distributed.lease_expires_at ? <div><dt>Fin de lease</dt><dd>{formatDate(detail.distributed.lease_expires_at)}</dd></div> : null}
                  {detail.distributed.effect_started_at ? <div><dt>Inicio de efecto</dt><dd>{formatDate(detail.distributed.effect_started_at)}</dd></div> : null}
                  {detail.distributed.last_error_code ? <div><dt>Error</dt><dd>{detail.distributed.last_error_code}</dd></div> : null}
                </dl>
              ) : <p>Aún no se ha enviado a la cola.</p>}
            </aside>
          </div>
        )}
      </article>
    </div>
  );
}

export default function ResolutionCenterPage() {
  const [items, setItems] = useState([]);
  const [nextCursor, setNextCursor] = useState(null);
  const [filters, setFilters] = useState({
    search: '',
    requester: '',
    authorizer: '',
    resolution_type: '',
    subject_type: '',
    subject_id: '',
    lifecycle_status: '',
    distributed_status: '',
    result: '',
    created_from: '',
    created_to: '',
    has_retries: '',
    blocked: '',
    compensated: ''
  });
  const [capabilities, setCapabilities] = useState(null);
  const [definitions, setDefinitions] = useState([]);
  const [indicators, setIndicators] = useState(null);
  const [selectedId, setSelectedId] = useState('');
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
  const [error, setError] = useState('');
  const loadingRef = useRef(false);

  const query = useMemo(() => ({
    ...Object.fromEntries(
      Object.entries(filters).map(([key, value]) => [
        key,
        typeof value === 'string' ? value.trim() || undefined : value
      ])
    )
  }), [filters]);

  const loadList = useCallback(async ({ append = false } = {}) => {
    if (loadingRef.current) return;
    loadingRef.current = true;
    setError('');
    try {
      const [payload, indicatorPayload] = await Promise.all([
        listCenterResolutions({
          ...query,
          cursor: append ? nextCursor : undefined,
          limit: 40
        }),
        getResolutionCenterIndicators()
      ]);
      setItems((current) => append ? [...current, ...payload.items] : payload.items);
      setNextCursor(payload.next_cursor);
      setIndicators(indicatorPayload);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      loadingRef.current = false;
      setLoading(false);
    }
  }, [nextCursor, query]);

  const loadDetail = useCallback(async (publicId) => {
    if (!publicId) return;
    setDetailLoading(true);
    try {
      setDetail(await getCenterResolution(publicId));
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setDetailLoading(false);
    }
  }, []);

  useEffect(() => {
    Promise.all([getResolutionCenterCapabilities(), listResolutionDefinitions()])
      .then(([permissionPayload, definitionPayload]) => {
        setCapabilities(permissionPayload);
        setDefinitions(definitionPayload);
      })
      .catch((requestError) => setError(requestError.message));
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => loadList(), 250);
    return () => window.clearTimeout(timer);
  }, [query]);

  const hasActive = items.some(
    (item) => ACTIVE_RESOLUTION_STATES.has(item.lifecycle_status)
  );
  useEffect(() => {
    if (!hasActive) return undefined;
    const timer = window.setInterval(() => {
      if (shouldPollResolutions(items, document.visibilityState)) {
        loadList();
        if (selectedId) loadDetail(selectedId);
      }
    }, 10000);
    return () => window.clearInterval(timer);
  }, [hasActive, items, loadDetail, loadList, selectedId]);

  async function openDetail(publicId) {
    setSelectedId(publicId);
    setDetail(null);
    await loadDetail(publicId);
  }

  async function runStage(stage, payload, idempotencyKey) {
    await runCenterResolutionStage(selectedId, stage, payload, idempotencyKey);
    await Promise.all([loadDetail(selectedId), loadList()]);
  }

  return (
    <section className="resolution-center-page">
      <header className="module-workspace__hero clients-hero resolution-center-hero">
        <span className="module-workspace__icon"><Network size={28} /></span>
        <div>
          <p>Consola institucional</p>
          <h1>Centro de Resoluciones</h1>
          <span>Consulta, prepara, autoriza y sigue resoluciones operadas por el Motor real.</span>
        </div>
        {capabilities?.can_create ? <button className="primary-button" onClick={() => setCreateOpen(true)} type="button"><Plus size={18} /> Nueva resolución</button> : null}
      </header>

      {indicators ? <section aria-label="Indicadores del Motor" className="resolution-indicators">
        {[
          ['Pendientes', indicators.pending],
          ['Autorizadas', indicators.authorized],
          ['Ejecutándose', indicators.executing],
          ['Finalizadas', indicators.completed],
          ['Fallidas', indicators.failed],
          ['Bloqueadas', indicators.blocked],
          ['Compensadas', indicators.compensated],
          ['Con reintentos', indicators.with_retries]
        ].map(([label, value]) => <article key={label}><small>{label}</small><strong>{value}</strong></article>)}
      </section> : null}

      <div className="resolution-toolbar">
        <label className="resolution-search"><Search size={18} /><input onChange={(event) => setFilters({ ...filters, search: event.target.value })} placeholder="ID, certificado, ETS, factura, cliente…" value={filters.search} /></label>
        <label><Filter size={16} /><select onChange={(event) => setFilters({ ...filters, lifecycle_status: event.target.value })} value={filters.lifecycle_status}><option value="">Todos los estados</option><option value="draft">Borrador</option><option value="pending_authorization">Por autorizar</option><option value="ready_for_execution">Lista para ejecutar</option><option value="executing">Ejecutando</option><option value="completed">Completada</option><option value="blocked">Bloqueada</option><option value="failed">Fallida</option></select></label>
        <label><AlertTriangle size={16} /><select onChange={(event) => setFilters({ ...filters, blocked: event.target.value })} value={filters.blocked}><option value="">Todas</option><option value="true">Sólo bloqueadas</option><option value="false">Excluir bloqueadas</option></select></label>
        <button className="resolution-icon-button" onClick={() => loadList()} type="button"><RefreshCw size={18} /></button>
      </div>
      <details className="resolution-advanced-filters">
        <summary>Filtros avanzados</summary>
        <div className="resolution-filter-grid">
          <label>Solicitante<input onChange={(event) => setFilters({ ...filters, requester: event.target.value })} placeholder="Nombre, correo o actor" value={filters.requester} /></label>
          <label>Autorizador<input onChange={(event) => setFilters({ ...filters, authorizer: event.target.value })} placeholder="Nombre, correo o actor" value={filters.authorizer} /></label>
          <label>Tipo<select onChange={(event) => setFilters({ ...filters, resolution_type: event.target.value })} value={filters.resolution_type}><option value="">Todos</option>{definitions.map((definition) => <option key={`${definition.resolution_type}@${definition.version}`} value={definition.resolution_type}>{definition.name}</option>)}</select></label>
          <label>Tipo de objeto<input onChange={(event) => setFilters({ ...filters, subject_type: event.target.value })} placeholder="certificate, ETS…" value={filters.subject_type} /></label>
          <label>ID del objeto<input onChange={(event) => setFilters({ ...filters, subject_id: event.target.value })} value={filters.subject_id} /></label>
          <label>Estado distribuido<select onChange={(event) => setFilters({ ...filters, distributed_status: event.target.value })} value={filters.distributed_status}><option value="">Todos</option><option value="queued">En cola</option><option value="claimed">Reclamada</option><option value="retry_wait">Reintentando</option><option value="succeeded">Completada</option><option value="failed">Fallida</option><option value="blocked">Bloqueada</option></select></label>
          <label>Resultado<input onChange={(event) => setFilters({ ...filters, result: event.target.value })} placeholder="succeeded, failed…" value={filters.result} /></label>
          <label>Desde<input onChange={(event) => setFilters({ ...filters, created_from: event.target.value ? `${event.target.value}T00:00:00` : '' })} type="date" value={filters.created_from.slice(0, 10)} /></label>
          <label>Hasta<input onChange={(event) => setFilters({ ...filters, created_to: event.target.value ? `${event.target.value}T23:59:59` : '' })} type="date" value={filters.created_to.slice(0, 10)} /></label>
          <label>Reintentos<select onChange={(event) => setFilters({ ...filters, has_retries: event.target.value })} value={filters.has_retries}><option value="">Todos</option><option value="true">Con reintentos</option><option value="false">Sin reintentos</option></select></label>
          <label>Compensación<select onChange={(event) => setFilters({ ...filters, compensated: event.target.value })} value={filters.compensated}><option value="">Todas</option><option value="true">Compensadas</option><option value="false">No compensadas</option></select></label>
          <button className="secondary-button" onClick={() => setFilters(Object.fromEntries(Object.keys(filters).map((key) => [key, ''])))} type="button">Limpiar filtros</button>
        </div>
      </details>

      {error ? <div className="resolution-page-error"><AlertTriangle size={18} />{error}</div> : null}
      <div className="resolution-table-card">
        {loading ? <div className="resolution-loading"><LoaderCircle className="spin" /> Cargando resoluciones…</div> : items.length ? (
          <div className="resolution-table-scroll">
            <table>
              <thead><tr><th>Resolución</th><th>Objeto</th><th>Actores</th><th>Estados</th><th>Fechas</th><th>Intentos</th><th>Resultado</th><th /></tr></thead>
              <tbody>{items.map((item) => (
                <tr key={item.public_id} onClick={() => openDetail(item.public_id)}>
                  <td><strong>{item.title}</strong><small>{item.public_id}</small><small>{item.resolution_type}</small></td>
                  <td><strong>{item.subject_label || item.subject_id}</strong><small>{item.subject_type}</small></td>
                  <td><strong>{item.requester || '—'}</strong><small>Autoriza: {item.authorizer || '—'}</small></td>
                  <td><StatusBadge>{item.lifecycle_status}</StatusBadge><small>Ejecución: {item.execution_status || '—'}</small><StatusBadge>{item.distributed_status}</StatusBadge></td>
                  <td><small>Creada: {formatDate(item.created_at)}</small><small>Autorizada: {formatDate(item.authorized_at)}</small><small>Inicio: {formatDate(item.started_at)}</small><small>Fin: {formatDate(item.completed_at)}</small><small>Duración: {formatDuration(item.duration_seconds)}</small></td>
                  <td>{item.attempt_count}{item.has_retries ? <Clock3 size={14} /> : null}</td>
                  <td>{item.result || 'Pendiente'}</td>
                  <td><button aria-label="Abrir expediente" className="resolution-icon-button" type="button"><Eye size={17} /></button></td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        ) : <div className="resolution-empty"><FileSearch size={34} /><h2>Sin resoluciones</h2><p>No hay resultados para los filtros actuales.</p></div>}
        {nextCursor ? <button className="resolution-load-more" onClick={() => loadList({ append: true })} type="button">Cargar más</button> : null}
      </div>

      {createOpen ? <CreateResolutionDialog definitions={definitions} onClose={() => setCreateOpen(false)} onCreated={(publicId) => { setCreateOpen(false); loadList(); openDetail(publicId); }} /> : null}
      {selectedId ? <ResolutionDetailDialog capabilities={capabilities} detail={detail} loading={detailLoading} onClose={() => { setSelectedId(''); setDetail(null); }} onRefresh={() => loadDetail(selectedId)} onStage={runStage} /> : null}
    </section>
  );
}
