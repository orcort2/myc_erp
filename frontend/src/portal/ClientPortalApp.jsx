import React, { useEffect, useMemo, useState } from 'react';

import {
  downloadClientPortalCertificate,
  getClientPortalCertificates,
  getClientPortalQuotations,
  getClientPortalServiceOrders,
  getClientPortalCompany,
  getClientPortalEquipment,
  getClientPortalInvoices,
  getClientPortalPayments,
} from '../services/api.js';
import { navigate } from '../utils/routing.js';
import ClientPortalLayout from './ClientPortalLayout.jsx';
import ClientPortalCertificates from './pages/ClientPortalCertificates.jsx';
import ClientPortalHome from './pages/ClientPortalHome.jsx';
import ClientPortalProfile from './pages/ClientPortalProfile.jsx';
import ClientPortalQuotations from './pages/ClientPortalQuotations.jsx';
import ClientPortalServices from './pages/ClientPortalServices.jsx';
import ClientPortalRecords from './pages/ClientPortalRecords.jsx';
import ClientPortalUsers from './pages/ClientPortalUsers.jsx';

import './client-portal.css';

const allowedPaths = new Set(['/portal', '/portal/empresa', '/portal/cotizaciones', '/portal/servicios', '/portal/equipos', '/portal/certificados', '/portal/facturas', '/portal/pagos', '/portal/usuarios', '/portal/perfil']);

export default function ClientPortalApp({ path, onLogout, user }) {
  const [quotations, setQuotations] = useState([]);
  const [serviceOrders, setServiceOrders] = useState([]);
  const [certificates, setCertificates] = useState([]);
  const [company, setCompany] = useState([]);
  const [equipment, setEquipment] = useState([]);
  const [invoices, setInvoices] = useState([]);
  const [payments, setPayments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!allowedPaths.has(path)) {
      navigate('/portal');
    }
  }, [path]);

  useEffect(() => {
    let mounted = true;
    const has = (permission) => user?.permissions?.includes(permission);
    Promise.all([
      has('quotations.view') ? getClientPortalQuotations() : [],
      has('services.view') ? getClientPortalServiceOrders() : [],
      has('certificates.view') ? getClientPortalCertificates() : [],
      has('client.view') ? getClientPortalCompany() : null,
      has('equipment.view') ? getClientPortalEquipment() : [],
      has('invoices.view') ? getClientPortalInvoices() : [],
      has('payments.view') ? getClientPortalPayments() : [],
    ])
      .then(([quotationItems, serviceItems, certificateItems, companyItem, equipmentItems, invoiceItems, paymentItems]) => {
        if (!mounted) return;
        setQuotations(quotationItems ?? []);
        setServiceOrders(serviceItems ?? []);
        setCertificates(certificateItems ?? []);
        setCompany(companyItem ? [companyItem] : []);
        setEquipment(equipmentItems ?? []);
        setInvoices(invoiceItems ?? []);
        setPayments(paymentItems ?? []);
        setError('');
      })
      .catch((requestError) => mounted && setError(requestError.message))
      .finally(() => mounted && setLoading(false));
    return () => { mounted = false; };
  }, [user]);

  const content = useMemo(() => {
    if (error) return <div className="client-portal-page"><div className="portal-error" role="alert"><strong>No pudimos cargar tu portal.</strong><span>{error}</span></div></div>;
    if (path === '/portal/cotizaciones') return <ClientPortalQuotations items={quotations} loading={loading} />;
    if (path === '/portal/servicios') return <ClientPortalServices items={serviceOrders} loading={loading} />;
    if (path === '/portal/certificados') return <ClientPortalCertificates items={certificates} loading={loading} downloadCertificate={downloadClientPortalCertificate} />;
    if (path === '/portal/perfil') return <ClientPortalProfile user={user} />;
    if (path === '/portal/usuarios' && user?.permissions?.includes('users.view')) return <ClientPortalUsers permissions={user.permissions} />;
    if (path === '/portal/empresa') return <ClientPortalRecords title="Mi empresa" eyebrow="Organización" description="Datos autorizados de la empresa vinculada." items={company} loading={loading} renderTitle={(item) => item.commercial_name || item.legal_name} renderMeta={(item) => <><span>RFC: {item.rfc || 'Sin RFC'}</span><span>{item.email}</span></>} />;
    if (path === '/portal/equipos') return <ClientPortalRecords title="Mis equipos" eyebrow="Operación" description="Equipos incluidos en tus servicios." items={equipment} loading={loading} renderTitle={(item) => item.name} renderMeta={(item) => <><span>{item.brand} {item.model}</span><span>Serie: {item.serial_number || 'Sin serie'}</span><span>{item.status}</span></>} />;
    if (path === '/portal/facturas') return <ClientPortalRecords title="Mis facturas" eyebrow="Facturación" description="Comprobantes emitidos para tu organización." items={invoices} loading={loading} renderTitle={(item) => item.folio} renderMeta={(item) => <><span>{item.status}</span><span>Saldo: {item.balance_due} {item.currency}</span></>} />;
    if (path === '/portal/pagos') return <ClientPortalRecords title="Mis pagos" eyebrow="Cartera" description="Pagos registrados para tus facturas." items={payments} loading={loading} renderTitle={(item) => item.invoice_folio} renderMeta={(item) => <><span>{item.paid_on}</span><span>{item.amount}</span><span>{item.status}</span></>} />;
    return <ClientPortalHome certificates={certificates} loading={loading} quotations={quotations} serviceOrders={serviceOrders} user={user} />;
  }, [certificates, company, equipment, error, invoices, loading, path, payments, quotations, serviceOrders, user]);

  return <ClientPortalLayout currentPath={allowedPaths.has(path) ? path : '/portal'} onLogout={onLogout} user={user}>{content}</ClientPortalLayout>;
}
