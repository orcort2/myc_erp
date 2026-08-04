import { Award, Download } from 'lucide-react';
import React, { useState } from 'react';

import PortalEmptyState from '../components/PortalEmptyState.jsx';
import PortalStatusBadge from '../components/PortalStatusBadge.jsx';
import { CERTIFICATE_STATUS, formatPortalDate, presentationFor } from '../presentation/clientPortalPresentation.js';

export default function ClientPortalCertificates({ downloadCertificate, items, loading }) {
  const [downloadingId, setDownloadingId] = useState(null);
  const [error, setError] = useState('');

  async function handleDownload(certificate) {
    setError('');
    setDownloadingId(certificate.id);
    try {
      await downloadCertificate(certificate);
    } catch (downloadError) {
      setError(downloadError.message);
    } finally {
      setDownloadingId(null);
    }
  }

  return (
    <div className="client-portal-page">
      <header className="client-portal-page-header"><div><span className="client-portal-eyebrow">Documentación</span><h1>Mis certificados</h1><p>Descarga únicamente los certificados autenticados y liberados para tu organización.</p></div><Award size={28} /></header>
      {error ? <div className="portal-error" role="alert">{error}</div> : null}
      {loading ? <div className="portal-loading">Cargando certificados...</div> : items.length ? (
        <div className="portal-certificate-grid">
          {items.map((certificate) => (
            <article className="portal-certificate-card" key={certificate.id}>
              <span className="portal-certificate-card__icon"><Award size={24} /></span>
              <div><small>Certificado</small><h2>{certificate.folio}</h2><p>{certificate.title || `Certificado ${certificate.certificate_type}`}</p><div className="portal-certificate-card__meta"><PortalStatusBadge presentation={presentationFor(CERTIFICATE_STATUS, certificate.status, 'Disponible')} /><span>{formatPortalDate(certificate.released_on ?? certificate.released_to_client_at)}</span></div></div>
              <button className="portal-primary-button" disabled={downloadingId === certificate.id} onClick={() => handleDownload(certificate)} type="button"><Download size={18} />{downloadingId === certificate.id ? 'Descargando...' : 'Descargar PDF'}</button>
            </article>
          ))}
        </div>
      ) : <PortalEmptyState title="No hay certificados disponibles" description="Los documentos aparecerán después de ser autenticados y liberados por MYC." />}
    </div>
  );
}
