import React from 'react';
import { ChevronRight } from 'lucide-react';

import SettingsSidebar from '../navigation/SettingsSidebar.jsx';
import SettingsSubnav from '../navigation/SettingsSubnav.jsx';

import './SettingsLayout.css';

function SettingsLayout({
  navigation,
  activeSection,
  activeChild,
  onSectionChange,
  onChildChange,
  user,
}) {
  if (!activeSection) {
    return null;
  }

  const CurrentComponent = activeChild?.component ?? activeSection.component;
  const currentTitle = activeChild?.title ?? activeSection.title;

  return (
    <section className="settings-layout" aria-label="Centro de ajustes">
      <aside className="settings-layout__categories">
        <SettingsSidebar
          navigation={navigation}
          activeSectionId={activeSection.id}
          onSectionChange={onSectionChange}
        />
      </aside>

      <aside className="settings-layout__options">
        <SettingsSubnav
          section={activeSection}
          activeChildId={activeChild?.id}
          onChildChange={onChildChange}
        />
      </aside>

      <main className="settings-layout__content">
        <header className="settings-layout__content-header">
          <div className="settings-layout__breadcrumb" aria-label="Ruta actual">
            <span>Ajustes</span>
            <ChevronRight size={14} aria-hidden="true" />
            <span>{activeSection.title}</span>
            {activeChild ? (
              <>
                <ChevronRight size={14} aria-hidden="true" />
                <span>{activeChild.shortTitle ?? activeChild.title}</span>
              </>
            ) : null}
          </div>
          <h1>{currentTitle}</h1>
          {(activeChild?.description ?? activeSection.description) ? (
            <p>{activeChild?.description ?? activeSection.description}</p>
          ) : null}
        </header>

        <div className="settings-layout__body">
          {CurrentComponent ? (
            <CurrentComponent
              user={user}
              section={activeSection}
              child={activeChild}
            />
          ) : null}
        </div>
      </main>
    </section>
  );
}

export default SettingsLayout;
