import React, { useState } from 'react';

import AuditSettingsPanel from './settings/AuditSettingsPanel.jsx';
import UsersSettingsPanel from './settings/UsersSettingsPanel.jsx';

const SETTINGS_TABS = [
  { id: 'users', label: 'Usuarios' },
  { id: 'audit', label: 'Auditoria' }
];

function SettingsPage() {
  const [activeTab, setActiveTab] = useState('users');

  return (
    <section className="module-workspace">
      <div className="module-workspace__hero">
        <div>
          <p>Configuración</p>
          <h1>Usuarios y auditoría</h1>
          <span>Administración de acceso y trazabilidad operativa</span>
        </div>
      </div>

      <section className="settings-card">
        <div className="settings-tabs" role="tablist" aria-label="Configuración">
          {SETTINGS_TABS.map((tab) => (
            <button
              key={tab.id}
              aria-selected={activeTab === tab.id}
              className={`settings-tab ${activeTab === tab.id ? 'is-active' : ''}`}
              onClick={() => setActiveTab(tab.id)}
              role="tab"
              type="button"
            >
              {tab.label}
            </button>
          ))}
        </div>

        {activeTab === 'users' ? <UsersSettingsPanel /> : <AuditSettingsPanel />}
      </section>
    </section>
  );
}

export default SettingsPage;
