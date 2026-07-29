import React, { useState } from 'react';

import {
  getDefaultChild,
  getDefaultSection,
  settingsNavigation,
} from './settings/navigation/settingsNavigation.js';
import SettingsLayout from './settings/shared/SettingsLayout.jsx';

function SettingsPage({ user = null }) {
  const initialSection = getDefaultSection();
  const [activeSection, setActiveSection] = useState(initialSection);
  const [activeChild, setActiveChild] = useState(getDefaultChild(initialSection));

  function handleSectionChange(section) {
    setActiveSection(section);
    setActiveChild(getDefaultChild(section));
  }

  function handleChildChange(child) {
    setActiveChild(child);
  }

  return (
    <section className="module-workspace settings-workspace">
      <div className="module-workspace__hero">
        <div>
          <p>Ajustes</p>
          <h1>Administración del ERP</h1>
          <span>Configura la empresa, los usuarios y los parámetros seguros de operación.</span>
        </div>
      </div>

      <SettingsLayout
        navigation={settingsNavigation}
        activeSection={activeSection}
        activeChild={activeChild}
        onSectionChange={handleSectionChange}
        onChildChange={handleChildChange}
        user={user}
      />
    </section>
  );
}

export default SettingsPage;
