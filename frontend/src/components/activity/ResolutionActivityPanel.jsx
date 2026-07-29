import { useEffect, useState } from 'react';

import { getResolutionActivityTarget } from '../../services/api.js';
import ActivityPanel from './ActivityPanel.jsx';

export default function ResolutionActivityPanel({ publicId }) {
  const [target, setTarget] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    setTarget(null);
    setError('');
    if (!publicId) {
      return () => {
        active = false;
      };
    }
    getResolutionActivityTarget(publicId)
      .then((result) => {
        if (active) setTarget(result);
      })
      .catch((requestError) => {
        if (active) {
          setError(
            requestError?.message
              || 'No fue posible abrir la Actividad de la resolución.',
          );
        }
      });
    return () => {
      active = false;
    };
  }, [publicId]);

  if (error) {
    return <div className="activity-error" role="alert">{error}</div>;
  }
  if (!target) {
    return <div className="activity-loading" role="status">Cargando actividad…</div>;
  }
  return (
    <ActivityPanel
      entityId={target.entity_id}
      entityType="resolution"
    />
  );
}
