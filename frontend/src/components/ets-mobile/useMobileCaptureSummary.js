import { useCallback, useEffect, useState } from 'react';

import { getCapturePackageSummary } from '../../services/api.js';

// Loader ÚNICO del resumen de Captura LAB de un ETS MYC Mobile. La página lo
// eleva para que la pestaña Captura, la franja de etapas del Resumen y el
// panel de Captura compartan la misma autoridad (sin dos consultas
// independientes). GET sin efectos: nunca muta el lifecycle del ETS.
export default function useMobileCaptureSummary(serviceOrderId) {
  const [state, setState] = useState({ serviceOrderId: null, summary: null, error: '' });

  const refresh = useCallback(async () => {
    if (!serviceOrderId) return null;
    try {
      const summary = await getCapturePackageSummary(serviceOrderId);
      setState({ serviceOrderId, summary, error: '' });
      return summary;
    } catch (requestError) {
      setState((current) => ({
        serviceOrderId,
        summary: current.serviceOrderId === serviceOrderId ? current.summary : null,
        error: requestError.message,
      }));
      return null;
    }
  }, [serviceOrderId]);

  useEffect(() => {
    setState({ serviceOrderId, summary: null, error: '' });
    refresh();
  }, [refresh, serviceOrderId]);

  // Nunca expone el resumen de otro ETS mientras se consulta el actual.
  const current = state.serviceOrderId === serviceOrderId;
  return {
    summary: current ? state.summary : null,
    error: current ? state.error : '',
    refresh,
  };
}
