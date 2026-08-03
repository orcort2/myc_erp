import { Download, Eye, FileCheck2, ShieldCheck } from 'lucide-react';
import React, { useEffect, useMemo, useState } from 'react';

import ConfirmDialog from '../components/ConfirmDialog.jsx';
import WorkOrderFlowGroups from '../components/WorkOrderFlowGroups.jsx';
import { getCertificateStatusLabel, certificateTypeLabels } from '../constants/statuses.js';
import {
  changeCertificateStatus,
  downloadAuthenticatedCertificatePdf,
  downloadOriginalCertificatePdf,
  getCertificate,
  getCertificateReleaseReadiness,
  listCertificates,
  listClients,
  listEquipment,
  listServiceOrders
} from '../services/api.js';
import { formatDate, formatDateTime, getClientDisplayName } from '../utils/formatters.js';
import { getCertificateReleasePresentation } from '../utils/etsStages.js';
import useConfirmDialog from '../utils/useConfirmDialog.js';
import { hasPermission } from '../utils/accessControl.js';

function triggerDownload(blob, filename) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

export default function CertificatesPage({ user = null }) {
  const [certificates, setCertificates] = useState([]);
  const [orders, setOrders] = useState([]);
  const [equipment, setEquipment] = useState([]);
  const [clients, setClients] = useState([]);
  const [readinessByOrderId, setReadinessByOrderId] = useState(new Map());
  const [activeTab, setActiveTab] = useState('available');
  const [selectedCertificate, setSelectedCertificate] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [loadingAction, setLoadingAction] = useState('');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const { confirmDialog, openConfirm, closeConfirm, handleConfirm } = useConfirmDialog();
  const canRelease = hasPermission(user, 'release.manage');

  const ordersById = useMemo(() => new Map(orders.map((item) => [item.id, item])), [orders]);
  const equipmentById = useMemo(() => new Map(equipment.map((item) => [item.id, item])), [equipment]);
  const clientsById = useMemo(() => new Map(clients.map((item) => [item.id, item])), [clients]);
  const authenticatedCertificates = useMemo(
    () => certificates.filter((item) => item.authenticated_pdf_path && ['authenticated', 'released_to_client', 'released'].includes(item.status)),
    [certificates]
  );
  const displayedCertificates = useMemo(
    () => authenticatedCertificates.filter((item) => activeTab === 'released' ? ['released_to_client', 'released'].includes(item.status) : !['released_to_client', 'released'].includes(item.status)),
    [activeTab, authenticatedCertificates]
  );

  async function loadData() {
    setError('');
    setIsLoading(true);
    try {
      const [certificateItems, orderItems, equipmentItems, clientItems] = await Promise.all([
        listCertificates(), listServiceOrders(), listEquipment(), listClients()
      ]);
      const safeCertificates = Array.isArray(certificateItems) ? certificateItems : [];
      const safeOrders = Array.isArray(orderItems) ? orderItems : [];
      setCertificates(safeCertificates);
      setOrders(safeOrders);
      setEquipment(Array.isArray(equipmentItems) ? equipmentItems : []);
      setClients(Array.isArray(clientItems) ? clientItems : []);
      const authenticatedOrderIds = [...new Set(safeCertificates.filter((item) => item.authenticated_pdf_path).map((item) => item.service_order_id))];
      const readinessEntries = await Promise.all(authenticatedOrderIds.map(async (orderId) => {
        try {
          return [orderId, await getCertificateReleaseReadiness(orderId)];
        } catch (requestError) {
          return [orderId, { release_allowed: false, reason: requestError.message }];
        }
      }));
      setReadinessByOrderId(new Map(readinessEntries));
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => { loadData(); }, []);

  function context(certificate) {
    const order = ordersById.get(certificate.service_order_id);
    return {
      order,
      item: equipmentById.get(certificate.equipment_id),
      client: order ? clientsById.get(order.client_id) : null
    };
  }

  function releaseGroupState(items) {
    const readiness = readinessByOrderId.get(items[0]?.service_order_id);
    return getCertificateReleasePresentation({
      released: items.every((item) => ['released_to_client', 'released'].includes(item.status)),
      releaseReadiness: readiness,
    });
  }

  async function openAuthenticatedPdf(certificate) {
    const pdfWindow = window.open('', '_blank');
    if (!pdfWindow) {
      setError('El navegador bloqueó la vista del PDF. Permite ventanas emergentes.');
      return;
    }
    try {
      const { blob } = await downloadAuthenticatedCertificatePdf(certificate.id, certificate.folio, certificate.authentication_code);
      const url = URL.createObjectURL(blob);
      pdfWindow.location.replace(url);
      window.setTimeout(() => URL.revokeObjectURL(url), 5 * 60 * 1000);
    } catch (requestError) {
      pdfWindow.close();
      setError(requestError.message);
    }
  }

  async function downloadAuthenticated(certificate) {
    setLoadingAction(`${certificate.id}-download`);
    try {
      const { blob, filename } = await downloadAuthenticatedCertificatePdf(certificate.id, certificate.folio, certificate.authentication_code);
      triggerDownload(blob, filename);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoadingAction('');
    }
  }

  async function openOriginalPdf(certificate) {
    const pdfWindow = window.open('', '_blank');
    if (!pdfWindow) return;
    try {
      const { blob } = await downloadOriginalCertificatePdf(certificate.id, certificate.final_pdf_original_filename);
      const url = URL.createObjectURL(blob);
      pdfWindow.location.replace(url);
      window.setTimeout(() => URL.revokeObjectURL(url), 5 * 60 * 1000);
    } catch (requestError) {
      pdfWindow.close();
      setError(requestError.message);
    }
  }

  async function openAuthentication(certificate) {
    try {
      setSelectedCertificate(await getCertificate(certificate.id));
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  function releaseCertificate(certificate) {
    const readiness = readinessByOrderId.get(certificate.service_order_id);
    if (!readiness?.release_allowed) {
      setError(readiness?.reason || 'Aún se está validando la condición financiera del ETS.');
      return;
    }
    openConfirm({
      title: 'Liberar certificado',
      message: `El certificado ${certificate.folio} quedará disponible para el cliente.`,
      confirmText: 'Liberar',
      variant: 'danger',
      onConfirm: async () => {
        setLoadingAction(`${certificate.id}-release`);
        try {
          await changeCertificateStatus(certificate.id, 'release-to-client');
          setNotice(`Certificado ${certificate.folio} liberado`);
          await loadData();
        } catch (requestError) {
          setError(requestError.message);
        } finally {
          setLoadingAction('');
        }
      }
    });
  }

  function renderCertificate(certificate) {
    const { client, item } = context(certificate);
    const released = ['released_to_client', 'released'].includes(certificate.status);
    const readiness = readinessByOrderId.get(certificate.service_order_id);
    const releasePresentation = getCertificateReleasePresentation({ released, releaseReadiness: readiness });
    return (
      <article className="flow-certificate-card" key={certificate.id}>
        <button className="flow-certificate-card__primary" onClick={() => openAuthenticatedPdf(certificate)} type="button">
          <div className="flow-certificate-card__title"><div><span>Certificado autenticado</span><strong>{certificate.folio}</strong></div><mark className={`quotation-status status-${certificate.status}`}>{getCertificateStatusLabel(certificate)}</mark></div>
          <dl><div><dt>Cliente</dt><dd>{getClientDisplayName(client)}</dd></div><div><dt>Equipo</dt><dd>{item?.name || '-'}</dd></div><div><dt>Serie</dt><dd>{item?.serial_number || item?.internal_id || '-'}</dd></div><div><dt>Tipo</dt><dd>{certificateTypeLabels[certificate.certificate_type] ?? certificate.certificate_type}</dd></div><div><dt>Autenticación</dt><dd>{certificate.authentication_code || '-'}</dd></div><div><dt>Fecha</dt><dd>{formatDateTime(certificate.authenticated_pdf_generated_at)}</dd></div></dl>
          <span className="flow-primary-hint"><Eye size={15} /> Ver PDF autenticado</span>
        </button>
        <div className={releasePresentation.status === 'blocked' ? 'flow-release-blocked' : 'flow-release-ready'}>{releasePresentation.message}</div>
        <div className="toolbar-actions">
          <button className="table-button" disabled={Boolean(loadingAction)} onClick={() => downloadAuthenticated(certificate)} type="button"><Download size={14} /> Descargar</button>
          <button className="table-button" onClick={() => openAuthentication(certificate)} type="button"><ShieldCheck size={14} /> Ver autenticación</button>
          {released ? <span className="flow-action-complete">Liberado</span> : canRelease ? <button className="table-button table-button--primary" disabled={Boolean(loadingAction) || !releasePresentation.canRelease} onClick={() => releaseCertificate(certificate)} title={releasePresentation.canRelease ? 'Liberar al cliente' : releasePresentation.message} type="button">Liberar</button> : null}
        </div>
      </article>
    );
  }

  return (
    <section className="module-workspace certificates-workspace">
      <div className="module-workspace__hero clients-hero"><span className="module-workspace__icon"><FileCheck2 size={28} /></span><div><p>Entrega documental</p><h1>Certificados</h1><span>Consulta certificados autenticados y administra exclusivamente su liberación.</span></div></div>
      {error ? <div className="form-error dashboard-error">{error}</div> : null}
      {notice ? <div className="form-notice dashboard-error">{notice}</div> : null}
      <section className="operations-band certificates-summary">
        <div className="operations-band__metric"><strong>{isLoading ? '-' : authenticatedCertificates.filter((item) => item.status === 'authenticated').length}</strong><span>Listos para liberar</span></div>
        <div className="operations-band__metric"><strong>{isLoading ? '-' : authenticatedCertificates.filter((item) => ['released_to_client', 'released'].includes(item.status)).length}</strong><span>Liberados</span></div>
        <div className="operations-band__metric"><strong>{isLoading ? '-' : authenticatedCertificates.length}</strong><span>Total autenticados</span></div>
      </section>
      <div className="module-tabs" role="tablist"><button className={activeTab === 'available' ? 'module-tab is-active' : 'module-tab'} onClick={() => setActiveTab('available')} type="button">Listos para liberar</button><button className={activeTab === 'released' ? 'module-tab is-active' : 'module-tab'} onClick={() => setActiveTab('released')} type="button">Liberados</button></div>
      <section className="clients-list-panel">
        <div className="section-heading"><div><p>ETS y Órdenes de Trabajo</p><h2>{displayedCertificates.length} certificados {activeTab === 'released' ? 'liberados' : 'listos para liberar'}</h2></div></div>
        {isLoading ? <div className="clients-empty">Cargando certificados autenticados...</div> : <WorkOrderFlowGroups emptyMessage="No hay certificados autenticados en esta vista." equipmentById={equipmentById} getGroupState={releaseGroupState} items={displayedCertificates} orders={orders} renderItem={renderCertificate} />}
      </section>

      {selectedCertificate ? (
        <div className="modal-backdrop" role="presentation"><section className="client-modal quotation-detail-modal certificate-detail-modal" aria-modal="true" role="dialog">
          <div className="quotation-detail-header"><div><p>Autenticación</p><h2>{selectedCertificate.folio}</h2><span>{getCertificateStatusLabel(selectedCertificate)}</span></div><button className="icon-text-button" onClick={() => setSelectedCertificate(null)} type="button">Cerrar</button></div>
          <section className="quotation-section"><div className="quotation-section__title"><p>Sello digital</p><h3>Datos de autenticación</h3></div><div className="quotation-commercial-grid service-order-info-grid">
            <article><span>Código</span><strong>{selectedCertificate.authentication_code || '-'}</strong></article><article><span>Fecha</span><strong>{formatDateTime(selectedCertificate.authenticated_pdf_generated_at)}</strong></article><article><span>Autenticado por</span><strong>{selectedCertificate.authenticated_by_id ? `Usuario #${selectedCertificate.authenticated_by_id}` : 'Sistema'}</strong></article><article><span>Aprobado por</span><strong>{selectedCertificate.quality_reviewed_by_id ? `Usuario #${selectedCertificate.quality_reviewed_by_id}` : '-'}</strong></article><article><span>Liberado por</span><strong>{selectedCertificate.released_to_client_by_id ? `Usuario #${selectedCertificate.released_to_client_by_id}` : '-'}</strong></article><article><span>Fecha liberación</span><strong>{formatDate(selectedCertificate.released_on)}</strong></article><article className="form-field--wide"><span>Hash</span><strong className="certificate-hash">{selectedCertificate.authentication_hash || '-'}</strong></article>
          </div></section>
          <section className="quotation-section"><div className="quotation-section__title"><p>Auditoría</p><h3>Archivos conservados</h3></div><div className="quotation-history-list"><article><strong>PDF autenticado</strong><span>{selectedCertificate.authenticated_pdf_path ? 'Disponible' : 'No disponible'}</span></article><article><strong>PDF original actual</strong><span>{selectedCertificate.final_pdf_original_filename || 'No disponible'}</span></article><article><strong>Match</strong><span>{selectedCertificate.match_status}</span></article>{(selectedCertificate.pdf_versions || []).map((version) => <article key={version.id}><strong>PDF versión {version.version_number}{version.is_current ? ' · actual' : ''}</strong><span>{version.original_filename || 'PDF'} · {formatDateTime(version.uploaded_at)}{version.change_reason ? ` · ${version.change_reason}` : ''}</span></article>)}</div><div className="toolbar-actions"><button className="table-button table-button--primary" onClick={() => openAuthenticatedPdf(selectedCertificate)} type="button">Ver PDF autenticado</button><button className="table-button" disabled={!selectedCertificate.final_pdf_path} onClick={() => openOriginalPdf(selectedCertificate)} type="button">Ver PDF original (auditoría)</button></div></section>
        </section></div>
      ) : null}
      <ConfirmDialog cancelText={confirmDialog?.cancelText} confirmText={confirmDialog?.confirmText} isLoading={Boolean(confirmDialog?.isConfirming)} isOpen={Boolean(confirmDialog)} message={confirmDialog?.message} onClose={closeConfirm} onConfirm={handleConfirm} title={confirmDialog?.title} variant={confirmDialog?.variant} />
    </section>
  );
}
