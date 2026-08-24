/**
 * Resolución de "en qué etapa de presentación está el usuario", derivada
 * exclusivamente de RepairExecution.status/conclusion (ya persistidos por el
 * backend). No es un segundo lifecycle: es una función pura de lectura sobre
 * el estado real, usada solo para decidir qué tarjeta destacar en el modal.
 *
 * Secuencia principal real de Reparación (backend, repair_execution.py):
 *   pending_arrival -> pending_assignment -> assigned -> in_evaluation
 *     -> (dictamen) -> in_repair <-> testing -> technically_completed
 *                    \-> equipment_not_suitable (salta intervención/pruebas)
 *   -> pending_release -> closed
 *
 * "Evaluación" y "Dictamen" comparten el mismo status backend
 * (in_evaluation): el diagnóstico es opcional y no cambia el status: solo
 * concluir la evaluación (dictamen) avanza el lifecycle. Por eso ambas
 * tarjetas se destacan juntas mientras status está en {assigned,
 * in_evaluation}. Lo mismo aplica a Intervención/Pruebas: ambas comparten
 * ventana operativa (in_repair/testing) porque el ciclo prueba fallida ->
 * intervención puede requerir ver ambas a la vez.
 */

export const REPAIR_MAIN_STAGES = [
  { key: 'reception', label: 'Recepción' },
  { key: 'assignment', label: 'Asignación' },
  { key: 'evaluation', label: 'Evaluación' },
  { key: 'verdict', label: 'Dictamen' },
  { key: 'intervention', label: 'Intervención' },
  { key: 'testing', label: 'Pruebas' },
  { key: 'closure', label: 'Cierre' },
];

const STAGE_RANK = {
  pending_arrival: 0,
  pending_assignment: 1,
  assigned: 2,
  in_evaluation: 2,
  in_repair: 4,
  testing: 5,
  technically_completed: 6,
  equipment_not_suitable: 6,
  pending_release: 6,
  closed: 6,
};

/**
 * Claves de las secciones a destacar (featured) para el status actual.
 * Puede haber más de una porque Evaluación/Dictamen (y
 * Intervención/Pruebas) comparten ventana operativa real en backend.
 */
export function getFeaturedStageKeys(execution) {
  const status = execution?.status;

  if (status === 'pending_arrival') {
    return ['reception'];
  }

  if (status === 'pending_assignment') {
    return ['assignment'];
  }

  if (status === 'assigned' || status === 'in_evaluation') {
    return ['evaluation', 'verdict'];
  }

  if (status === 'in_repair' || status === 'testing') {
    return ['intervention', 'testing'];
  }

  if (
    status === 'technically_completed' ||
    status === 'equipment_not_suitable' ||
    status === 'pending_release'
  ) {
    return ['closure'];
  }

  if (status === 'closed') {
    return ['closure'];
  }

  return [];
}

/**
 * Tono de cada nodo del stepper principal: 'done' | 'active' | 'pending' |
 * 'skipped'. 'skipped' es exclusivo de intervención/pruebas cuando el
 * dictamen fue "equipment_not_suitable" (esa rama nunca se ejecuta).
 */
export function getStageTone(stageKey, execution) {
  const status = execution?.status;
  const rank = STAGE_RANK[status] ?? -1;
  const isNotSuitable = execution?.conclusion === 'equipment_not_suitable';
  const featured = getFeaturedStageKeys(execution);

  if (featured.includes(stageKey)) {
    return 'active';
  }

  switch (stageKey) {
    case 'reception':
      return rank > 0 ? 'done' : 'pending';

    case 'assignment':
      return rank > 1 ? 'done' : 'pending';

    case 'evaluation':
      return rank > 2 ? 'done' : 'pending';

    case 'verdict':
      // rank > 2 exige que el status ya haya salido de evaluación: evita
      // que un `conclusion` heredado del ciclo anterior (reopen_for_warranty
      // no lo limpia; solo un nuevo conclude_evaluation lo hace) marque
      // Dictamen como "hecho" en un ciclo de garantía que aún no ha vuelto
      // a dictaminar.
      return execution?.conclusion && rank > 2 ? 'done' : 'pending';

    case 'intervention':
      if (isNotSuitable) return 'skipped';
      return rank > 4 ? 'done' : 'pending';

    case 'testing':
      if (isNotSuitable) return 'skipped';
      return rank > 5 ? 'done' : 'pending';

    case 'closure':
      return status === 'closed' ? 'done' : 'pending';

    default:
      return 'pending';
  }
}

export function isTerminalCancelled(execution) {
  return execution?.status === 'cancelled';
}

export function isClosed(execution) {
  return execution?.status === 'closed';
}

/**
 * Una cancelación es siempre pre-intervención (cancel_execution la rechaza
 * en cuanto existe alguna intervención), así que el status-rank normal no
 * aplica: se infiere directamente de la evidencia persistida qué llegó a
 * completarse antes de cancelar, para conservar trazabilidad.
 */
export function getCancelledHistoryKeys(execution) {
  const keys = [];

  if (execution?.equipment_id) {
    keys.push('reception');
  }

  if (execution?.technician_id) {
    keys.push('assignment');
  }

  if (execution?.diagnosis_completed_at || execution?.conclusion) {
    keys.push('evaluation');
  }

  if (execution?.conclusion) {
    keys.push('verdict');
  }

  return keys;
}
