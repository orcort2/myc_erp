import { Network } from 'lucide-react';
import React, { useEffect, useMemo, useState } from 'react';

import {
  listCertificates,
  listClients,
  listEquipment,
  listFieldSheets,
  listQuotations,
  listServiceOrders
} from '../services/api.js';
import { certificateStatusLabels } from '../constants/statuses.js';

function label(value, fallback = 'No disponible') {
  return value === null || value === undefined || value === '' ? fallback : value;
}

function FlowItem({ title, value, detail, missing }) {
  return (
    <div className="pattern-selection-panel">
      <strong>{title}</strong>
      <span>{value}</span>
      {detail ? <small>{detail}</small> : null}
      {missing ? <span className="status-pill status-pill--danger">{missing}</span> : null}
    </div>
  );
}

export default function FlowTestPage() {
  const [clients, setClients] = useState([]);
  const [quotations, setQuotations] = useState([]);
  const [orders, setOrders] = useState([]);
  const [equipment, setEquipment] = useState([]);
  const [fieldSheets, setFieldSheets] = useState([]);
  const [certificates, setCertificates] = useState([]);
  const [selectedOrderId, setSelectedOrderId] = useState('');
  const [selectedEquipmentId, setSelectedEquipmentId] = useState('');
  const [selectedFieldSheetId, setSelectedFieldSheetId] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(true);

  const selectedOrder = useMemo(
    () => orders.find((item) => String(item.id) === String(selectedOrderId)) ?? null,
    [orders, selectedOrderId]
  );
  const selectedEquipment = useMemo(
    () => equipment.find((item) => String(item.id) === String(selectedEquipmentId)) ?? null,
    [equipment, selectedEquipmentId]
  );
  const selectedFieldSheet = useMemo(
    () => fieldSheets.find((item) => String(item.id) === String(selectedFieldSheetId)) ?? null,
    [fieldSheets, selectedFieldSheetId]
  );
  const selectedCertificate = useMemo(
    () =>
      certificates.find((item) => item.field_sheet_id && String(item.field_sheet_id) === String(selectedFieldSheetId)) ??
      certificates.find((item) => String(item.equipment_id) === String(selectedEquipmentId)) ??
      null,
    [certificates, selectedEquipmentId, selectedFieldSheetId]
  );
  const selectedClient = useMemo(
    () => clients.find((item) => item.id === selectedOrder?.client_id) ?? selectedOrder?.client ?? null,
    [clients, selectedOrder]
  );
  const selectedQuotation = useMemo(
    () => quotations.find((item) => item.id === selectedOrder?.quotation_id) ?? selectedOrder?.quotation ?? null,
    [quotations, selectedOrder]
  );
  const orderEquipment = useMemo(
    () => equipment.filter((item) => String(item.service_order_id) === String(selectedOrderId)),
    [equipment, selectedOrderId]
  );
  const equipmentSheets = useMemo(
    () => fieldSheets.filter((item) => String(item.equipment_id) === String(selectedEquipmentId)),
    [fieldSheets, selectedEquipmentId]
  );
  const missingMessages = useMemo(() => {
    const messages = [];
    if (!selectedClient) messages.push('No hay cliente seleccionado para la orden.');
    if (!selectedQuotation) messages.push('La orden no tiene cotizacion seleccionada.');
    if (!selectedOrder) messages.push('Selecciona una orden de servicio.');
    if (!selectedEquipment) messages.push('Selecciona un equipo.');
    if (!selectedFieldSheet) messages.push('Selecciona una hoja de campo.');
    if (selectedFieldSheet && !selectedFieldSheet.calibration_procedure_id) messages.push('La hoja no tiene procedimiento asignado.');
    if (!selectedCertificate) messages.push('No existe certificado esperado para esta hoja/equipo.');
    if (selectedCertificate && !selectedCertificate.expected_folio) messages.push('El certificado no tiene folio esperado.');
    if (selectedCertificate && ['expected', 'field_sheet_ready', 'capture_pending'].includes(selectedCertificate.status)) messages.push('Captura aun no inicia o no termina.');
    if (selectedCertificate && !['ready_for_quality', 'quality_review', 'quality_approved', 'approved', 'authenticated', 'released_to_client'].includes(selectedCertificate.status)) messages.push('Calidad aun no recibe/aprueba el certificado.');
    if (selectedCertificate && ['quality_approved', 'approved'].includes(selectedCertificate.status)) messages.push('El Master esta aprobado y pendiente de autenticacion.');
    if (selectedCertificate && ['authenticated', 'released_to_client'].includes(selectedCertificate.status) && !selectedCertificate.authenticated_pdf_path) messages.push('La autenticacion no conserva un PDF accesible.');
    if (selectedCertificate && !selectedCertificate.client_visible) messages.push('El certificado no esta liberado al cliente.');
    return [...new Set(messages)];
  }, [selectedCertificate, selectedClient, selectedEquipment, selectedFieldSheet, selectedOrder, selectedQuotation]);

  async function loadData() {
    setError('');
    setIsLoading(true);
    try {
      const [clientsResult, quotationsResult, ordersResult, equipmentResult, sheetsResult, certificatesResult] = await Promise.all([
        listClients(),
        listQuotations(),
        listServiceOrders(),
        listEquipment(),
        listFieldSheets(),
        listCertificates()
      ]);
      const orderItems = Array.isArray(ordersResult) ? ordersResult : [];
      setClients(Array.isArray(clientsResult) ? clientsResult : []);
      setQuotations(Array.isArray(quotationsResult) ? quotationsResult : []);
      setOrders(orderItems);
      setEquipment(Array.isArray(equipmentResult) ? equipmentResult : []);
      setFieldSheets(Array.isArray(sheetsResult) ? sheetsResult : []);
      setCertificates(Array.isArray(certificatesResult) ? certificatesResult : []);
      if (!selectedOrderId && orderItems[0]) setSelectedOrderId(String(orderItems[0].id));
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    if (orderEquipment.length && !orderEquipment.some((item) => String(item.id) === String(selectedEquipmentId))) {
      setSelectedEquipmentId(String(orderEquipment[0].id));
    }
  }, [orderEquipment, selectedEquipmentId]);

  useEffect(() => {
    if (equipmentSheets.length && !equipmentSheets.some((item) => String(item.id) === String(selectedFieldSheetId))) {
      setSelectedFieldSheetId(String(equipmentSheets[0].id));
    }
  }, [equipmentSheets, selectedFieldSheetId]);

  return (
    <section className="module-workspace service-orders-workspace">
      <div className="module-workspace__hero clients-hero">
        <span className="module-workspace__icon"><Network size={28} /></span>
        <div>
          <p>Auditoria interna</p>
          <h1>Prueba de flujo</h1>
          <span>Cliente, cotizacion, orden, equipo, hoja, captura, calidad, PDF y liberacion.</span>
        </div>
      </div>

      {error ? <div className="form-error dashboard-error">{error}</div> : null}

      <section className="clients-list-panel">
        <div className="section-heading">
          <div>
            <p>Seleccion</p>
            <h2>{isLoading ? 'Cargando flujo...' : 'Cadena operativa externa'}</h2>
          </div>
          <div className="toolbar-actions">
            <select value={selectedOrderId} onChange={(event) => setSelectedOrderId(event.target.value)}>
              <option value="">Orden</option>
              {orders.map((item) => (
                <option key={item.id} value={item.id}>OT {item.work_order_number} - {item.folio}</option>
              ))}
            </select>
            <select value={selectedEquipmentId} onChange={(event) => setSelectedEquipmentId(event.target.value)}>
              <option value="">Equipo</option>
              {orderEquipment.map((item) => (
                <option key={item.id} value={item.id}>{item.name} {item.serial_number ? `- ${item.serial_number}` : ''}</option>
              ))}
            </select>
            <select value={selectedFieldSheetId} onChange={(event) => setSelectedFieldSheetId(event.target.value)}>
              <option value="">Hoja</option>
              {equipmentSheets.map((item) => (
                <option key={item.id} value={item.id}>Hoja #{item.id} - {item.status}</option>
              ))}
            </select>
          </div>
        </div>
      </section>

      <div className="flow-test-grid">
        <FlowItem title="Cliente" value={label(selectedClient?.business_name ?? selectedClient?.name)} missing={!selectedClient ? 'Falta cliente' : ''} />
        <FlowItem title="Cotizacion" value={label(selectedQuotation?.folio)} detail={selectedQuotation?.status} missing={!selectedQuotation ? 'Falta cotizacion' : ''} />
        <FlowItem title="Orden de servicio" value={selectedOrder ? `OT ${selectedOrder.work_order_number}` : 'Sin orden'} detail={selectedOrder?.status} missing={!selectedOrder ? 'Falta orden' : ''} />
        <FlowItem title="Equipo" value={label(selectedEquipment?.name)} detail={selectedEquipment?.serial_number} missing={!selectedEquipment ? 'Falta equipo' : ''} />
        <FlowItem title="Hoja de campo" value={selectedFieldSheet ? `Hoja #${selectedFieldSheet.id}` : 'Sin hoja'} detail={selectedFieldSheet?.status} missing={!selectedFieldSheet ? 'Falta hoja' : ''} />
        <FlowItem title="Folio esperado" value={label(selectedCertificate?.expected_folio ?? selectedCertificate?.folio)} missing={!selectedCertificate ? 'Sin certificado esperado' : ''} />
        <FlowItem title="Captura" value={selectedCertificate ? certificateStatusLabels[selectedCertificate.status] ?? selectedCertificate.status : 'Sin certificado'} missing={selectedCertificate && ['expected', 'field_sheet_ready', 'capture_pending'].includes(selectedCertificate.status) ? 'Pendiente captura' : ''} />
        <FlowItem title="Calidad" value={selectedCertificate ? certificateStatusLabels[selectedCertificate.status] ?? selectedCertificate.status : 'Sin certificado'} detail={selectedCertificate?.quality_rejection_reason} missing={selectedCertificate && selectedCertificate.status === 'quality_rejected' ? 'Rechazado' : ''} />
        <FlowItem title="Master aprobado" value={selectedCertificate && ['quality_approved', 'approved', 'authenticated', 'released_to_client'].includes(selectedCertificate.status) ? 'Sí' : 'Pendiente'} detail="Compuerta de autenticación" missing={selectedCertificate && !['quality_approved', 'approved', 'authenticated', 'released_to_client'].includes(selectedCertificate.status) ? 'Sin aprobación' : ''} />
        <FlowItem title="PDF autenticado" value={label(selectedCertificate?.authenticated_pdf_original_filename)} detail={selectedCertificate?.authenticated_at} missing={selectedCertificate && ['authenticated', 'released_to_client'].includes(selectedCertificate.status) && !selectedCertificate.authenticated_pdf_path ? 'Sin archivo' : ''} />
        <FlowItem title="Liberado cliente" value={selectedCertificate?.client_visible ? 'Visible' : 'No visible'} detail={selectedCertificate?.released_to_client_at} missing={selectedCertificate && !selectedCertificate.client_visible ? 'No liberado' : ''} />
        <FlowItem title="Incertidumbre" value="Experimental / no bloqueante" detail="El flujo principal no depende del motor." />
      </div>

      <section className="clients-list-panel">
        <div className="section-heading">
          <div>
            <p>Diagnostico</p>
            <h2>{missingMessages.length ? `${missingMessages.length} mensajes` : 'Flujo listo para cliente'}</h2>
          </div>
        </div>
        {missingMessages.length ? (
          <div className="document-version-list">
            {missingMessages.map((message) => <span key={message}>{message}</span>)}
          </div>
        ) : (
          <div className="clients-empty">Certificado PDF externo listo y visible para cliente.</div>
        )}
      </section>
    </section>
  );
}
