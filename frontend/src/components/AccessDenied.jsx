import React from 'react';

function AccessDenied() {
  return (
    <section className="module-workspace" role="alert">
      <div className="empty-state">
        <strong>Acceso denegado</strong>
        <span>No tienes permisos para consultar este módulo o ejecutar esta acción.</span>
      </div>
    </section>
  );
}

export default AccessDenied;
