const completedFieldSheetStatuses = new Set(['completed', 'under_review', 'approved']);
const terminalEquipmentStatuses = new Set(['cancelled', 'not_done']);
const captureFinishedStatuses = new Set([
  'ready_for_quality', 'quality_review', 'match_validated', 'quality_approved', 'approved',
  'authenticated', 'released_to_client', 'released'
]);
const qualityFinishedStatuses = new Set(['authenticated', 'released_to_client', 'released']);

function stage(status, label, reason, metrics = {}) {
  return { status, label, reason, metrics, ready: status === 'done' || status === 'available' };
}

export function getExpectedEquipmentCount(order, equipmentCount = 0) {
  const fromItems = (order?.items ?? []).reduce((total, item) => total + Number(item.quantity || 0), 0);
  const declared = Number(order?.total_equipment || 0);
  return Math.max(fromItems, declared, equipmentCount ? 0 : 0);
}

export function getEquipmentStageStatus({ order, equipment = [] }) {
  const registered = equipment.filter((item) => item.is_active !== false && item.status !== 'cancelled').length;
  const expected = getExpectedEquipmentCount(order, registered);
  if (!registered) return stage('pending', 'PENDIENTE', 'Aún no hay equipos registrados.', { registered, expected });
  if (!expected || registered >= expected) {
    return stage('done', 'LISTA', 'Todos los equipos esperados fueron registrados.', { registered, expected: expected || registered });
  }
  return stage('active', 'EN PROCESO', 'Faltan equipos por registrar respecto al alcance vigente.', { registered, expected });
}

export function getFieldSheetStageStatus({ equipment = [], fieldSheets = [], equipmentStage }) {
  const requiredEquipment = equipment.filter((item) => item.is_active !== false && !terminalEquipmentStatuses.has(item.status));
  const activeSheetsByEquipment = new Map(
    fieldSheets.filter((sheet) => sheet.is_active !== false).map((sheet) => [sheet.equipment_id, sheet])
  );
  const completed = requiredEquipment.filter((item) => completedFieldSheetStatuses.has(activeSheetsByEquipment.get(item.id)?.status)).length;
  const created = requiredEquipment.filter((item) => activeSheetsByEquipment.has(item.id)).length;
  if (!requiredEquipment.length) return stage('pending', 'PENDIENTE', 'No hay equipos que requieran hoja de campo.', { required: 0, created, completed });
  if (completed === requiredEquipment.length) return stage('done', 'LISTA', 'Todas las hojas requeridas están completadas.', { required: requiredEquipment.length, created, completed });
  if (!created && equipmentStage.status !== 'done') return stage('blocked', 'BLOQUEADA', 'Primero completa el registro de equipos.', { required: requiredEquipment.length, created, completed });
  return stage(created ? 'active' : 'pending', created ? 'EN PROCESO' : 'PENDIENTE', 'Faltan hojas por crear o completar.', { required: requiredEquipment.length, created, completed });
}

export function getCaptureStageStatus({ certificates = [], fieldSheetStage }) {
  if (!certificates.length) {
    return stage(fieldSheetStage.status === 'done' ? 'pending' : 'blocked', fieldSheetStage.status === 'done' ? 'PENDIENTE' : 'BLOQUEADA', 'No existen certificados esperados para captura.', { expected: 0, finished: 0 });
  }
  const finished = certificates.filter((certificate) => captureFinishedStatuses.has(certificate.status)).length;
  if (finished === certificates.length) return stage('done', 'LISTA', 'Todos los PDFs fueron enviados a Calidad.', { expected: certificates.length, finished });
  return stage('active', 'EN PROCESO', 'Falta cargar o enviar uno o más certificados a Calidad.', { expected: certificates.length, finished });
}

export function getQualityStageStatus({ certificates = [] }) {
  if (!certificates.length) return stage('pending', 'PENDIENTE', 'No hay certificados enviados a Calidad.', { expected: 0, authenticated: 0 });
  const authenticated = certificates.filter((certificate) => qualityFinishedStatuses.has(certificate.status)).length;
  if (authenticated === certificates.length) return stage('done', 'LISTA', 'Todos los certificados fueron aprobados y autenticados.', { expected: certificates.length, authenticated });
  const sent = certificates.filter((certificate) => ['ready_for_quality', 'quality_review', 'match_validated', 'quality_approved', 'authenticated'].includes(certificate.status)).length;
  return stage(sent ? 'active' : 'pending', sent ? 'EN PROCESO' : 'PENDIENTE', sent ? 'Hay certificados pendientes de revisión, aprobación o autenticación.' : 'Captura aún no ha enviado certificados a Calidad.', { expected: certificates.length, authenticated, sent });
}

export function getCertificateStageStatus({ certificates = [], releaseReadiness = null }) {
  if (!certificates.length) return stage('pending', 'PENDIENTE', 'No existen certificados para liberar.', { expected: 0, released: 0 });
  const released = certificates.filter((certificate) => certificate.status === 'released_to_client' || certificate.client_visible).length;
  if (released === certificates.length) return stage('done', 'LISTA', 'Todos los certificados fueron liberados al cliente.', { expected: certificates.length, released });
  const authenticated = certificates.every((certificate) => qualityFinishedStatuses.has(certificate.status));
  if (!authenticated) return stage('pending', 'PENDIENTE', 'Falta autenticar uno o más certificados.', { expected: certificates.length, released });
  if (releaseReadiness && !releaseReadiness.release_allowed) {
    return stage('blocked', 'PENDIENTE DE LIBERACIÓN', releaseReadiness.reason, { expected: certificates.length, released, payment: releaseReadiness.payment_status });
  }
  return stage('available', 'DISPONIBLE', releaseReadiness?.reason || 'Certificados autenticados listos para liberación.', { expected: certificates.length, released, payment: releaseReadiness?.payment_status || 'pending_check' });
}
