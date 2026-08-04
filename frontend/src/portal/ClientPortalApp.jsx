import React, { useEffect, useMemo, useState } from 'react';

import {
  downloadClientPortalCertificate,
  getClientPortalCertificates,
  getClientPortalQuotations,
  getClientPortalServiceOrders,
} from '../services/api.js';
import { navigate } from '../utils/routing.js';
import ClientPortalLayout from './ClientPortalLayout.jsx';
import ClientPortalCertificates from './pages/ClientPortalCertificates.jsx';
import ClientPortalHome from './pages/ClientPortalHome.jsx';
import ClientPortalProfile from './pages/ClientPortalProfile.jsx';
import ClientPortalQuotations from './pages/ClientPortalQuotations.jsx';
import ClientPortalServices from './pages/ClientPortalServices.jsx';

import './client-portal.css';

const allowedPaths = new Set(['/portal', '/portal/cotizaciones', '/portal/servicios', '/portal/certificados', '/portal/perfil']);

export default function ClientPortalApp({ path, onLogout, user }) {
  const [quotations, setQuotations] = useState([]);
  const [serviceOrders, setServiceOrders] = useState([]);
  const [certificates, setCertificates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!allowedPaths.has(path)) {
      navigate('/portal');
    }
  }, [path]);

  useEffect(() => {
    let mounted = true;
    Promise.all([
      getClientPortalQuotations(),
      getClientPortalServiceOrders(),
      getClientPortalCertificates(),
    ])
      .then(([quotationItems, serviceItems, certificateItems]) => {
        if (!mounted) return;
        setQuotations(quotationItems ?? []);
        setServiceOrders(serviceItems ?? []);
        setCertificates(certificateItems ?? []);
      })
      .catch((requestError) => mounted && setError(requestError.message))
      .finally(() => mounted && setLoading(false));
    return () => { mounted = false; };
  }, []);

  const content = useMemo(() => {
    if (error) return <div className="client-portal-page"><div className="portal-error" role="alert"><strong>No pudimos cargar tu portal.</strong><span>{error}</span></div></div>;
    if (path === '/portal/cotizaciones') return <ClientPortalQuotations items={quotations} loading={loading} />;
    if (path === '/portal/servicios') return <ClientPortalServices items={serviceOrders} loading={loading} />;
    if (path === '/portal/certificados') return <ClientPortalCertificates items={certificates} loading={loading} downloadCertificate={downloadClientPortalCertificate} />;
    if (path === '/portal/perfil') return <ClientPortalProfile user={user} />;
    return <ClientPortalHome certificates={certificates} loading={loading} quotations={quotations} serviceOrders={serviceOrders} user={user} />;
  }, [certificates, error, loading, path, quotations, serviceOrders, user]);

  return <ClientPortalLayout currentPath={allowedPaths.has(path) ? path : '/portal'} onLogout={onLogout} user={user}>{content}</ClientPortalLayout>;
}
