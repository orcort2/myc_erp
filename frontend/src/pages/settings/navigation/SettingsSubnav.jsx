import React from 'react';
import { ChevronRight } from 'lucide-react';

import './SettingsSubnav.css';

function SettingsSubnav({ section, activeChildId, onChildChange }) {
  const children = section?.children ?? [];

  return (
    <nav className="settings-subnav" aria-label={`Opciones de ${section?.title ?? 'ajustes'}`}>
      <header className="settings-subnav__header">
        <h3>{section?.title}</h3>
        {section?.description ? <p>{section.description}</p> : null}
      </header>

      {children.length ? (
        <div className="settings-subnav__list">
          {children.map((child) => {
            const isActive = child.id === activeChildId;

            return (
              <button
                key={child.id}
                type="button"
                className={`settings-subnav__item ${isActive ? 'is-active' : ''}`}
                aria-current={isActive ? 'page' : undefined}
                onClick={() => onChildChange(child)}
              >
                <span className="settings-subnav__copy">
                  <strong>{child.shortTitle ?? child.title}</strong>
                  {child.description ? <small>{child.description}</small> : null}
                </span>
                <ChevronRight size={17} aria-hidden="true" />
              </button>
            );
          })}
        </div>
      ) : (
        <div className="settings-subnav__empty">
          <span>Sin opciones adicionales</span>
          <p>El contenido de esta categoría se mostrará directamente en el panel principal.</p>
        </div>
      )}
    </nav>
  );
}

export default SettingsSubnav;
