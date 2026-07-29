import React from 'react';
import { Building2 } from 'lucide-react';

function CompanyIdentity() {
  return (
    <div className="settings-coming-soon">
      <span className="settings-coming-soon__icon" aria-hidden="true">
        <Building2 size={24} />
      </span>
      <div>
        <h2>Identidad institucional</h2>
        <p>
          La arquitectura de esta sección está lista. En el siguiente sprint incorporaremos la
          información general, contacto, ubicación, responsables e identidad documental.
        </p>
      </div>
    </div>
  );
}

export default CompanyIdentity;
