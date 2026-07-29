import React from 'react';
import { Settings2 } from 'lucide-react';

function ComingSoon({ section }) {
  return (
    <div className="settings-coming-soon">
      <span className="settings-coming-soon__icon" aria-hidden="true">
        <Settings2 size={24} />
      </span>
      <div>
        <h2>Sección preparada</h2>
        <p>
          {section?.title ?? 'Esta categoría'} ya forma parte de la arquitectura del Centro de Ajustes.
          Sus parámetros se incorporarán progresivamente sin alterar la operación actual.
        </p>
      </div>
    </div>
  );
}

export default ComingSoon;
