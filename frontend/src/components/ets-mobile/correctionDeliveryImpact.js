// Decisión administrativa de una corrección sobre un equipo YA ENTREGADO.
// Lenguaje de consecuencias, no de gravedad técnica. Los valores viajan tal
// cual como `delivery_impact` al endpoint de solicitud de corrección.
export const DELIVERY_IMPACT_OPTIONS = [
  {
    value: 'none',
    label: 'La corrección no afecta la entrega',
    description: 'La entrega y su acuse siguen vigentes sin cambios. Sólo se corrige el registro técnico.',
  },
  {
    value: 'documentation_reissue',
    label: 'Requiere reemisión documental',
    description:
      'La entrega sigue vigente, pero la documentación entregada deberá reemitirse. Queda un pendiente registrado para este equipo.',
  },
  {
    value: 'delivery_invalidated',
    label: 'La entrega de este equipo queda invalidada',
    description:
      'Se registrará la invalidación administrativa de este equipo y se retirará la vigencia del acuse final del grupo. La entrega histórica se conserva; los demás equipos no recibirán un impacto.',
  },
];

export function isEquipmentDelivered(equipment) {
  return Boolean(equipment?.delivery?.delivered);
}

export function deliveryImpactError(equipment, deliveryImpact) {
  if (isEquipmentDelivered(equipment) && !deliveryImpact) {
    return 'Indica cómo afecta la corrección a la entrega de este equipo.';
  }
  return '';
}

// Nunca incluye valores técnicos: el ERP no edita la hoja.
// `cohortRevision` es el token opaco de cohorte que el backend proyectó al abrir el
// diálogo; se reenvía tal cual (la semántica pertenece al backend).
export function buildCorrectionPayload({ reason, signaturePolicy, equipment, deliveryImpact, cohortRevision }) {
  const payload = { reason: reason.trim(), signature_policy: signaturePolicy };
  if (cohortRevision) payload.expected_cohort_revision = cohortRevision;
  if (isEquipmentDelivered(equipment)) payload.delivery_impact = deliveryImpact;
  return payload;
}
