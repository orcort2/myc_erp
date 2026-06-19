import React from 'react';

import { formatModuleDateTime } from '../utils/formatters.js';

function ModulePage({ module, timestamp }) {
  const Icon = module.icon;

  return (
    <section className="module-workspace">
      <div className="module-workspace__hero">
        <span className="module-workspace__icon">
          <Icon size={28} />
        </span>
        <div>
          <p>Modulo MYC SYSTEM</p>
          <h1>{module.name}</h1>
          <span>{module.description}</span>
        </div>
        <time className="module-workspace__time" dateTime={timestamp.toISOString()}>
          {formatModuleDateTime(timestamp)}
        </time>
      </div>

      <div className="module-workspace__panel">
        <h2>{module.status}</h2>
        <p>
          Vista preparada para conectar el flujo funcional del modulo. La navegacion lateral ya
          queda disponible aqui sin ocupar espacio en el dashboard principal.
        </p>
      </div>
    </section>
  );
}

export default ModulePage;