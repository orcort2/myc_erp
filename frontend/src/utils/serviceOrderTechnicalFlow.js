// Presentación del flujo técnico del ETS (web). La autoridad es el backend:
// `calibration_flow_managed_by_mobile` es la proyección de su política técnica
// 2026 (ETS nuevo sólo de calibración ejecutado en MYC Mobile, sin OT ERP).

// Capacidades del ETS a partir de sus partidas ACTIVAS, igual que la política
// backend (is_calibration_only): una partida inactiva no abre verticales.
export function getServiceOrderCapabilities(order) {
  const items = (Array.isArray(order?.items) ? order.items : []).filter(
    (item) => item.is_active !== false
  );

  const hasRepair = items.some(
    (item) => item.operational_category === 'repair'
  );

  const hasSale = items.some(
    (item) => item.operational_category === 'sale'
  );

  const hasMaintenance = items.some(
    (item) => item.operational_category === 'maintenance'
  );

  const hasDirectCalibration = items.some(
    (item) => item.operational_category === 'calibration'
  );

  const hasVerification = items.some(
    (item) => item.operational_category === 'verification'
  );

  const hasEmbeddedCalibration = items.some((item) => {
    if (item.operational_category !== 'sale') {
      return false;
    }

    const saleConfiguration =
      item.service_snapshot?.sale_configuration_snapshot;

    return Boolean(
      saleConfiguration?.included_calibration_catalog_item_id ||
      saleConfiguration?.included_calibration_snapshot
    );
  });

  return {
    hasSale,
    hasMaintenance,
    hasRepair,
    hasDirectCalibration,
    hasVerification,
    hasEmbeddedCalibration,
    // Proyección backend (política técnica 2026): ETS nuevo sólo de
    // calibración ejecutado en MYC Mobile; sin OT/equipos/hojas ERP.
    managedByMobileCalibration: Boolean(order?.calibration_flow_managed_by_mobile),
  };
}

export function isMobileCalibrationOrder(order) {
  return Boolean(order?.calibration_flow_managed_by_mobile);
}

// Nunca "OT-null", "OT-undefined" ni "OT -".
export function getWorkOrderLabel(order) {
  const number = order?.work_order_number;
  if (number !== null && number !== undefined) {
    return `OT ${number}`;
  }
  return isMobileCalibrationOrder(order) ? 'OT MYC Mobile' : 'Sin OT';
}

// Pestañas del ETS. Un ETS de calibración MYC Mobile no muestra Equipos ni
// Hojas de Campo ERP como flujo operativo; el ERP retoma en Captura, Calidad,
// Certificados y Facturación. Históricos y mixtos conservan la composición.
export function buildServiceOrderTabs(capabilities) {
  const {
    hasSale,
    hasMaintenance,
    hasRepair,
    hasDirectCalibration,
    hasVerification,
    managedByMobileCalibration,
  } = capabilities;
  const hasProductiveEquipment =
    hasSale || hasMaintenance || hasRepair || hasDirectCalibration || hasVerification;
  return [
    ['info', 'Resumen'],
    ...(hasMaintenance ? [['maintenance', 'Mantenimiento']] : []),
    ...(hasRepair ? [['repair', 'Reparación']] : []),
    ...(hasSale ? [['sale', 'Venta']] : []),
    ...(!managedByMobileCalibration && hasProductiveEquipment ? [['equipment', 'Equipos']] : []),
    ...(hasDirectCalibration || hasVerification
      ? [
          ...(managedByMobileCalibration ? [] : [['field-sheet', 'Hojas de Campo']]),
          ['capture', 'Captura'],
          ['quality', 'Calidad'],
          ['certificates', 'Certificados'],
        ]
      : []),
    ['billing', 'Facturacion'],
    ['documents', 'Documentos'],
    ['notes', 'Actividad'],
    ['history', 'Historial'],
  ];
}

// Estado mostrado en Resumen a partir del vínculo ETS ↔ raíz LAB.
export function describeMobileExecution(state) {
  if (state?.status === 'linked' && state.link) {
    return {
      title: `OT MYC Mobile ${state.link.root_folio}`,
      detail: `${state.link.group_work_order_count} OT en el grupo · Vínculo activo`,
    };
  }
  if (state?.status === 'loading') return { title: 'Consultando vínculo…', detail: null };
  if (state?.status === 'error') return { title: 'No fue posible consultar el vínculo', detail: null };
  return { title: 'Esperando OT MYC Mobile', detail: null };
}

// Guard defensivo: sólo se navega a pestañas visibles para el ETS actual
// (p. ej. un ETS de calibración MYC Mobile nunca abre equipment/field-sheet).
export function canOpenServiceOrderTab(tabs, tab) {
  return Array.isArray(tabs) && tabs.some(([key]) => key === tab);
}
