import React from 'react';

import './SettingsSidebar.css';

function SettingsSidebar({ navigation, activeSectionId, onSectionChange }) {
  return (
    <nav className="settings-sidebar" aria-label="Categorías de ajustes">
      <header className="settings-sidebar__header">
        <span className="settings-sidebar__eyebrow">Centro de administración</span>
        <h2>Ajustes</h2>
      </header>

      <div className="settings-sidebar__list">
        {navigation.map((section) => {
          const Icon = section.icon;
          const isActive = section.id === activeSectionId;

          return (
            <button
              key={section.id}
              type="button"
              className={`settings-sidebar__item ${isActive ? 'is-active' : ''}`}
              aria-current={isActive ? 'page' : undefined}
              onClick={() => onSectionChange(section)}
            >
              <span className="settings-sidebar__icon" aria-hidden="true">
                {Icon ? <Icon size={18} strokeWidth={2} /> : null}
              </span>
              <span className="settings-sidebar__label">{section.title}</span>
            </button>
          );
        })}
      </div>
    </nav>
  );
}

export default SettingsSidebar;
