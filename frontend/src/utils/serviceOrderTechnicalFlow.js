// Presentación del flujo técnico del ETS (web). La autoridad es el backend:
// `calibration_flow_managed_by_mobile` es la proyección de su política técnica
// 2026 (ETS nuevo sólo de calibración ejecutado en MYC Mobile, sin OT ERP).

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
