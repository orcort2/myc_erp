import { BadgeCheck, ChevronDown, ChevronRight, ClipboardList } from 'lucide-react';
import React, { useEffect, useMemo, useState } from 'react';

import { certificateStatusLabels, fieldSheetStatusLabels } from '../constants/statuses.js';
import {
  downloadFieldSheetPdf,
  getFieldSheetPdfUrl,
  listCertificates,
  listClients,
  listEquipment,
  listFieldSheets,
  listServiceOrders,
  reviewFieldSheet
} from '../services/api.js';
import { formatDateTime, getClientDisplayName } from '../utils/formatters.js';
import { getFieldSheetTemplateLabel } from '../utils/fieldSheets.js';
import { navigate } from '../utils/routing.js';

const EMPTY_SHEET_FILTERS = {
  clientId: '', certificate: '', serial: '', internalId: '', instrument: '',
  template: '', status: '', dateFrom: '', dateTo: ''
};

const EMPTY_WORK_ORDER_FILTERS = {
  workOrder: '', clientId: '', ets: '', status: '', dateFrom: '', dateTo: '', technician: ''
};

function includesText(value, search) {
  return String(value ?? '').toLocaleLowerCase('es').includes(String(search ?? '').trim().toLocaleLowerCase('es'));
}

function dateMatches(value, from, to) {
  if (!from && !to) return true;
  if (!value) return false;
  const day = String(value).slice(0, 10);
  return (!from || day >= from) && (!to || day <= to);
}

function latestDate(values) {
  const timestamps = values.filter(Boolean).map((value) => new Date(value).getTime()).filter(Number.isFinite);
  return timestamps.length ? new Date(Math.max(...timestamps)).toISOString() : null;
}

function sheetActionLabel(sheet) {
  return ['draft', 'in_progress', 'returned_to_technician', 'rejected'].includes(sheet.status)
    ? 'Continuar captura'
    : 'Abrir hoja';
}

function FieldSheetsPage() {
  const [fieldSheets, setFieldSheets] = useState([]);
  const [equipment, setEquipment] = useState([]);
  const [serviceOrders, setServiceOrders] = useState([]);
  const [clients, setClients] = useState([]);
  const [certificates, setCertificates] = useState([]);
  const [viewMode, setViewMode] = useState('sheets');
  const [sheetFilters, setSheetFilters] = useState(EMPTY_SHEET_FILTERS);
  const [workOrderFilters, setWorkOrderFilters] = useState(EMPTY_WORK_ORDER_FILTERS);
  const [expandedWorkOrders, setExpandedWorkOrders] = useState(() => new Set());
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  const equipmentById = useMemo(() => new Map(equipment.map((item) => [item.id, item])), [equipment]);
  const ordersById = useMemo(() => new Map(serviceOrders.map((order) => [order.id, order])), [serviceOrders]);
  const clientsById = useMemo(() => new Map(clients.map((client) => [client.id, client])), [clients]);

  const activeCertificatesByEquipmentId = useMemo(() => {
    const map = new Map();
    certificates.filter((item) => item.is_active !== false).forEach((item) => {
      const current = map.get(item.equipment_id);
      if (!current || new Date(item.updated_at || 0) > new Date(current.updated_at || 0)) map.set(item.equipment_id, item);
    });
    return map;
  }, [certificates]);

  const activeFieldSheetsByEquipmentId = useMemo(() => {
    const map = new Map();
    fieldSheets.filter((sheet) => sheet.is_active !== false).forEach((sheet) => {
      const current = map.get(sheet.equipment_id);
      if (!current || new Date(sheet.updated_at || 0) > new Date(current.updated_at || 0)) map.set(sheet.equipment_id, sheet);
    });
    return map;
  }, [fieldSheets]);

  const templateOptions = useMemo(() => [...new Set(fieldSheets.map((sheet) => sheet.template_key).filter(Boolean))]
    .sort((left, right) => getFieldSheetTemplateLabel(left).localeCompare(getFieldSheetTemplateLabel(right), 'es')), [fieldSheets]);

  function getSheetContext(sheet) {
    const item = equipmentById.get(sheet.equipment_id);
    const order = item ? ordersById.get(item.service_order_id) : null;
    const client = order ? clientsById.get(order.client_id) : null;
    const certificate = item ? activeCertificatesByEquipmentId.get(item.id) : null;
    return { item, order, client, certificate };
  }

  const displayedFieldSheets = useMemo(() => fieldSheets.filter((sheet) => {
    if (sheet.is_active === false) return false;
    const { item, order, client, certificate } = getSheetContext(sheet);
    const folio = sheet.reserved_certificate_folio || certificate?.expected_folio || certificate?.folio || '';
    return (!sheetFilters.clientId || String(order?.client_id) === sheetFilters.clientId)
      && includesText(folio, sheetFilters.certificate)
      && includesText(item?.serial_number, sheetFilters.serial)
      && includesText(item?.internal_id, sheetFilters.internalId)
      && includesText(item?.name, sheetFilters.instrument)
      && (!sheetFilters.template || sheet.template_key === sheetFilters.template)
      && (!sheetFilters.status || sheet.status === sheetFilters.status)
      && dateMatches(sheet.updated_at || sheet.created_at, sheetFilters.dateFrom, sheetFilters.dateTo)
      && Boolean(client || order || item);
  }), [activeCertificatesByEquipmentId, clientsById, equipmentById, fieldSheets, ordersById, sheetFilters]);

  const workOrderGroups = useMemo(() => {
    const groups = [];
    serviceOrders.filter((order) => order.is_active !== false).forEach((order) => {
      const orderEquipment = equipment.filter((item) => item.is_active !== false && item.service_order_id === order.id);
      const realWorkOrders = (order.work_orders ?? []).filter((workOrder) => workOrder.is_active !== false);
      const workOrders = realWorkOrders.length ? realWorkOrders : [{
        id: null,
        service_order_id: order.id,
        work_order_number: order.work_order_number,
        status: order.status,
        created_at: order.created_at,
        updated_at: order.updated_at,
        isLegacy: true
      }];

      workOrders.forEach((workOrder) => {
        const items = orderEquipment.filter((item) => workOrder.id
          ? item.work_order_id === workOrder.id || (!item.work_order_id && item.work_order_number === workOrder.work_order_number)
          : !item.work_order_id || item.work_order_number === workOrder.work_order_number);
        const rows = items.map((item) => ({
          item,
          sheet: activeFieldSheetsByEquipmentId.get(item.id) ?? null,
          certificate: activeCertificatesByEquipmentId.get(item.id) ?? null
        }));
        const created = rows.filter((row) => row.sheet).length;
        const approved = rows.filter((row) => row.sheet?.status === 'approved').length;
        const capture = rows.filter((row) => ['draft', 'in_progress', 'returned_to_technician', 'rejected'].includes(row.sheet?.status)).length;
        const review = rows.filter((row) => ['completed', 'under_review'].includes(row.sheet?.status)).length;
        const pending = Math.max(items.length - created, 0);
        let overallKey = 'pending';
        let overallLabel = 'Pendiente';
        if (items.length && approved === items.length) [overallKey, overallLabel] = ['approved', 'Aprobada'];
        else if (review) [overallKey, overallLabel] = ['review', 'En revisión'];
        else if (capture) [overallKey, overallLabel] = ['capture', 'En captura'];
        else if (created) [overallKey, overallLabel] = ['progress', 'En avance'];
        const client = clientsById.get(order.client_id);
        groups.push({
          key: workOrder.id ? `work-order-${workOrder.id}` : `legacy-${order.id}-${workOrder.work_order_number}`,
          workOrder,
          order,
          client,
          rows,
          equipmentCount: items.length,
          created,
          approved,
          capture,
          review,
          pending,
          overallKey,
          overallLabel,
          progress: items.length ? Math.round((created / items.length) * 100) : 0,
          lastUpdated: latestDate([workOrder.updated_at, order.updated_at, ...rows.map((row) => row.sheet?.updated_at)])
        });
      });
    });
    return groups.sort((left, right) => Number(right.workOrder.work_order_number || 0) - Number(left.workOrder.work_order_number || 0));
  }, [activeCertificatesByEquipmentId, activeFieldSheetsByEquipmentId, clientsById, equipment, serviceOrders]);

  const displayedWorkOrders = useMemo(() => workOrderGroups.filter((group) => (
    includesText(group.workOrder.work_order_number, workOrderFilters.workOrder)
    && (!workOrderFilters.clientId || String(group.order.client_id) === workOrderFilters.clientId)
    && includesText(group.order.folio, workOrderFilters.ets)
    && (!workOrderFilters.status || group.overallKey === workOrderFilters.status)
    && dateMatches(group.lastUpdated || group.workOrder.created_at, workOrderFilters.dateFrom, workOrderFilters.dateTo)
    && includesText(group.order.technician_name, workOrderFilters.technician)
  )), [workOrderFilters, workOrderGroups]);

  async function loadData() {
    setError('');
    setIsLoading(true);
    try {
      const [sheetsResult, equipmentResult, ordersResult, clientsResult, certificatesResult] = await Promise.all([
        listFieldSheets(), listEquipment(), listServiceOrders(), listClients(), listCertificates()
      ]);
      setFieldSheets(Array.isArray(sheetsResult) ? sheetsResult : []);
      setEquipment(Array.isArray(equipmentResult) ? equipmentResult : []);
      setServiceOrders(Array.isArray(ordersResult) ? ordersResult : []);
      setClients(Array.isArray(clientsResult) ? clientsResult : []);
      setCertificates(Array.isArray(certificatesResult) ? certificatesResult : []);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => { loadData(); }, []);

  function updateSheetFilter(field, value) {
    setSheetFilters((current) => ({ ...current, [field]: value }));
  }

  function updateWorkOrderFilter(field, value) {
    setWorkOrderFilters((current) => ({ ...current, [field]: value }));
  }

  function toggleWorkOrder(key) {
    setExpandedWorkOrders((current) => {
      const next = new Set(current);
      if (next.has(key)) next.delete(key); else next.add(key);
      return next;
    });
  }

  function openOperationalSheet(item) {
    window.sessionStorage.setItem('myc:openFieldSheetEquipmentId', String(item.id));
    navigate('/dashboard#servicios');
  }

  function openFieldSheetPdf(fieldSheetId, mode = 'view') {
    const pdfWindow = window.open(getFieldSheetPdfUrl(fieldSheetId), '_blank', 'noopener,noreferrer');
    if (mode === 'print' && pdfWindow) pdfWindow.addEventListener('load', () => { pdfWindow.focus(); pdfWindow.print(); });
  }

  async function handleDownloadPdf(sheet) {
    setError('');
    setNotice('');
    try {
      const { item } = getSheetContext(sheet);
      const { blob, filename } = await downloadFieldSheetPdf(sheet.id, sheet.work_order_number, item?.name || `hoja-${sheet.id}`);
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      setNotice(`PDF ${filename} generado correctamente`);
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  async function sendToReview(sheet) {
    setIsSaving(true);
    setError('');
    setNotice('');
    try {
      const updated = await reviewFieldSheet(sheet.id, 'Enviada a revisión desde la vista por Orden de Trabajo');
      setFieldSheets((current) => current.map((item) => item.id === updated.id ? updated : item));
      setNotice(`Hoja ${updated.reserved_certificate_folio || updated.id} enviada a revisión`);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <section className="module-workspace field-sheets-workspace">
      <div className="module-workspace__hero clients-hero">
        <span className="module-workspace__icon"><BadgeCheck size={28} /></span>
        <div><p>Trazabilidad técnica</p><h1>Hojas de Campo</h1><span>Consulta individual y operación diaria agrupada por Orden de Trabajo.</span></div>
      </div>

      {error ? <div className="form-error dashboard-error">{error}</div> : null}
      {notice ? <div className="form-notice dashboard-error">{notice}</div> : null}

      <section className="operations-band certificates-summary" aria-label="Resumen de hojas">
        <div className="operations-band__metric"><strong>{isLoading ? '-' : fieldSheets.length}</strong><span>Hojas activas</span></div>
        <div className="operations-band__metric"><strong>{isLoading ? '-' : workOrderGroups.length}</strong><span>Órdenes de Trabajo</span></div>
        <div className="operations-band__metric"><strong>{isLoading ? '-' : equipment.filter((item) => item.is_active !== false && !activeFieldSheetsByEquipmentId.has(item.id)).length}</strong><span>Equipos sin hoja</span></div>
        <div className="operations-band__metric"><strong>{isLoading ? '-' : fieldSheets.filter((sheet) => sheet.status === 'approved').length}</strong><span>Hojas aprobadas</span></div>
      </section>

      <div className="field-sheets-view-tabs" role="tablist" aria-label="Formas de visualizar Hojas de Campo">
        <button aria-selected={viewMode === 'sheets'} className={viewMode === 'sheets' ? 'is-active' : ''} onClick={() => setViewMode('sheets')} type="button"><BadgeCheck size={18} />Todas las hojas</button>
        <button aria-selected={viewMode === 'work-orders'} className={viewMode === 'work-orders' ? 'is-active' : ''} onClick={() => setViewMode('work-orders')} type="button"><ClipboardList size={18} />Órdenes de Trabajo</button>
      </div>

      {viewMode === 'sheets' ? (
        <>
          <section className="field-sheets-filter-panel" aria-label="Filtros de todas las hojas">
            <label>Cliente<select onChange={(event) => updateSheetFilter('clientId', event.target.value)} value={sheetFilters.clientId}><option value="">Todos</option>{clients.map((client) => <option key={client.id} value={client.id}>{getClientDisplayName(client)}</option>)}</select></label>
            <label>Certificado<input onChange={(event) => updateSheetFilter('certificate', event.target.value)} placeholder="Folio" value={sheetFilters.certificate} /></label>
            <label>Serie<input onChange={(event) => updateSheetFilter('serial', event.target.value)} value={sheetFilters.serial} /></label>
            <label>Identificación<input onChange={(event) => updateSheetFilter('internalId', event.target.value)} value={sheetFilters.internalId} /></label>
            <label>Instrumento<input onChange={(event) => updateSheetFilter('instrument', event.target.value)} value={sheetFilters.instrument} /></label>
            <label>Plantilla<select onChange={(event) => updateSheetFilter('template', event.target.value)} value={sheetFilters.template}><option value="">Todas</option>{templateOptions.map((key) => <option key={key} value={key}>{getFieldSheetTemplateLabel(key)}</option>)}</select></label>
            <label>Estado<select onChange={(event) => updateSheetFilter('status', event.target.value)} value={sheetFilters.status}><option value="">Todos</option>{Object.entries(fieldSheetStatusLabels).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label>
            <label>Desde<input onChange={(event) => updateSheetFilter('dateFrom', event.target.value)} type="date" value={sheetFilters.dateFrom} /></label>
            <label>Hasta<input onChange={(event) => updateSheetFilter('dateTo', event.target.value)} type="date" value={sheetFilters.dateTo} /></label>
            <button className="icon-text-button" onClick={() => setSheetFilters(EMPTY_SHEET_FILTERS)} type="button">Limpiar filtros</button>
          </section>

          <section className="clients-list-panel">
            <div className="section-heading"><div><p>Listado individual</p><h2>{isLoading ? 'Cargando...' : `${displayedFieldSheets.length} hojas`}</h2></div></div>
            <div className="field-sheets-flat-list" aria-busy={isLoading}>
              {isLoading ? <div className="clients-empty">Cargando hojas de campo...</div> : displayedFieldSheets.length ? displayedFieldSheets.map((sheet) => {
                const { item, order, client, certificate } = getSheetContext(sheet);
                const folio = sheet.reserved_certificate_folio || certificate?.expected_folio || certificate?.folio || '-';
                return <article className="field-sheet-flat-card" key={sheet.id}>
                  <div className="field-sheet-flat-card__primary"><span>{sheet.work_order_number ? `OT-${sheet.work_order_number}` : 'Sin OT'}</span><strong>{folio}</strong><small>{getClientDisplayName(client)}</small></div>
                  <dl><div><dt>Instrumento</dt><dd>{item?.name || '-'}</dd></div><div><dt>Marca / modelo</dt><dd>{[item?.brand, item?.model].filter(Boolean).join(' · ') || '-'}</dd></div><div><dt>Serie</dt><dd>{item?.serial_number || '-'}</dd></div><div><dt>Identificación</dt><dd>{item?.internal_id || '-'}</dd></div><div><dt>Plantilla</dt><dd>{getFieldSheetTemplateLabel(sheet.template_key)}</dd></div><div><dt>Fecha</dt><dd>{formatDateTime(sheet.created_at)}</dd></div><div><dt>Última actualización</dt><dd>{formatDateTime(sheet.updated_at)}</dd></div></dl>
                  <div className="field-sheet-flat-card__status"><mark className={`quotation-status status-${sheet.status}`}>{fieldSheetStatusLabels[sheet.status] ?? sheet.status}</mark>{certificate ? <small>{certificateStatusLabels[certificate.status] ?? certificate.status}</small> : null}</div>
                  <div className="field-sheet-flat-card__actions"><button className="table-button table-button--primary" onClick={() => openOperationalSheet(item)} type="button">{sheetActionLabel(sheet)}</button><button className="table-button" onClick={() => openFieldSheetPdf(sheet.id)} type="button">Ver PDF</button><button className="table-button" onClick={() => handleDownloadPdf(sheet)} type="button">Descargar</button></div>
                </article>;
              }) : <div className="clients-empty">No hay hojas que coincidan con los filtros.</div>}
            </div>
          </section>
        </>
      ) : (
        <>
          <section className="field-sheets-filter-panel field-sheets-filter-panel--work-orders" aria-label="Filtros por Orden de Trabajo">
            <label>Número de OT<input onChange={(event) => updateWorkOrderFilter('workOrder', event.target.value)} value={workOrderFilters.workOrder} /></label>
            <label>Cliente<select onChange={(event) => updateWorkOrderFilter('clientId', event.target.value)} value={workOrderFilters.clientId}><option value="">Todos</option>{clients.map((client) => <option key={client.id} value={client.id}>{getClientDisplayName(client)}</option>)}</select></label>
            <label>ETS<input onChange={(event) => updateWorkOrderFilter('ets', event.target.value)} value={workOrderFilters.ets} /></label>
            <label>Estado general<select onChange={(event) => updateWorkOrderFilter('status', event.target.value)} value={workOrderFilters.status}><option value="">Todos</option><option value="pending">Pendiente</option><option value="progress">En avance</option><option value="capture">En captura</option><option value="review">En revisión</option><option value="approved">Aprobada</option></select></label>
            <label>Técnico responsable<input onChange={(event) => updateWorkOrderFilter('technician', event.target.value)} value={workOrderFilters.technician} /></label>
            <label>Desde<input onChange={(event) => updateWorkOrderFilter('dateFrom', event.target.value)} type="date" value={workOrderFilters.dateFrom} /></label>
            <label>Hasta<input onChange={(event) => updateWorkOrderFilter('dateTo', event.target.value)} type="date" value={workOrderFilters.dateTo} /></label>
            <button className="icon-text-button" onClick={() => setWorkOrderFilters(EMPTY_WORK_ORDER_FILTERS)} type="button">Limpiar filtros</button>
          </section>

          <section className="field-sheet-work-order-list" aria-busy={isLoading}>
            <div className="section-heading"><div><p>Operación diaria del laboratorio</p><h2>{isLoading ? 'Cargando...' : `${displayedWorkOrders.length} Órdenes de Trabajo`}</h2></div></div>
            {isLoading ? <div className="clients-empty">Cargando Órdenes de Trabajo...</div> : displayedWorkOrders.length ? displayedWorkOrders.map((group) => {
              const expanded = expandedWorkOrders.has(group.key);
              return <article className={expanded ? 'field-sheet-work-order is-expanded' : 'field-sheet-work-order'} key={group.key}>
                <button aria-expanded={expanded} className="field-sheet-work-order__summary" onClick={() => toggleWorkOrder(group.key)} type="button">
                  <span className="field-sheet-work-order__chevron">{expanded ? <ChevronDown size={20} /> : <ChevronRight size={20} />}</span>
                  <div className="field-sheet-work-order__identity"><small>Orden de Trabajo</small><strong>OT-{group.workOrder.work_order_number}</strong><span>{getClientDisplayName(group.client)}</span><span>ETS: {group.order.folio}</span></div>
                  <div className="field-sheet-work-order__metrics"><span><strong>{group.equipmentCount}</strong>Equipos</span><span><strong>{group.created} / {group.equipmentCount}</strong>Hojas</span><span><strong>{group.capture}</strong>Captura</span><span><strong>{group.review}</strong>Revisión</span><span><strong>{group.approved}</strong>Aprobadas</span></div>
                  <div className="field-sheet-work-order__progress"><div><span style={{ width: `${group.progress}%` }} /></div><strong>{group.created} / {group.equipmentCount} hojas</strong><small>{group.progress}% creadas</small></div>
                  <mark className={`quotation-status status-${group.overallKey}`}>{group.overallLabel}</mark>
                </button>

                {expanded ? <div className="field-sheet-work-order__equipment">
                  {group.rows.length ? group.rows.map(({ item, sheet, certificate }) => <article className="field-sheet-equipment-row" key={item.id}>
                    <div className="field-sheet-equipment-row__identity"><strong>{item.name}</strong><span>{[item.brand, item.model].filter(Boolean).join(' · ') || 'Sin marca/modelo'}</span></div>
                    <dl><div><dt>Serie</dt><dd>{item.serial_number || '-'}</dd></div><div><dt>Identificación</dt><dd>{item.internal_id || '-'}</dd></div><div><dt>Plantilla</dt><dd>{sheet ? getFieldSheetTemplateLabel(sheet.template_key) : 'Por seleccionar'}</dd></div><div><dt>Folio certificado</dt><dd>{sheet?.reserved_certificate_folio || certificate?.expected_folio || certificate?.folio || '-'}</dd></div><div><dt>Última modificación</dt><dd>{sheet ? formatDateTime(sheet.updated_at) : '-'}</dd></div></dl>
                    <div className="field-sheet-equipment-row__status"><mark className={`quotation-status status-${sheet?.status || 'pending'}`}>{sheet ? fieldSheetStatusLabels[sheet.status] ?? sheet.status : 'Sin hoja'}</mark></div>
                    <div className="field-sheet-equipment-row__actions">
                      <button className="table-button table-button--primary" onClick={() => openOperationalSheet(item)} type="button">{sheet ? sheetActionLabel(sheet) : 'Crear hoja'}</button>
                      {sheet ? <button className="table-button" onClick={() => openFieldSheetPdf(sheet.id)} type="button">Ver PDF</button> : null}
                      {sheet?.status === 'completed' ? <button className="table-button" disabled={isSaving} onClick={() => sendToReview(sheet)} type="button">Enviar a revisión</button> : null}
                    </div>
                  </article>) : <div className="clients-empty">Esta OT todavía no tiene equipos registrados.</div>}
                </div> : null}
              </article>;
            }) : <div className="clients-empty">No hay Órdenes de Trabajo que coincidan con los filtros.</div>}
          </section>
        </>
      )}
    </section>
  );
}

export default FieldSheetsPage;
