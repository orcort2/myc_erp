import React, { useEffect, useState } from 'react';

import AppLayout from '../components/AppLayout.jsx';
import BrandLockup from '../components/BrandLockup.jsx';
import { modules } from '../constants/navigation.js';
import { clearTokens, getAccessToken, getCurrentUser } from '../services/api.js';
import { formatModuleDateTime } from '../utils/formatters.js';
import { getCurrentPath, navigate } from '../utils/routing.js';
import CertificatesPage from './CertificatesPage.jsx';
import ClientsPage from './ClientsPage.jsx';
import DashboardHome from './DashboardHome.jsx';
import EquipmentPage from './EquipmentPage.jsx';
import FieldSheetsPage from './FieldSheetsPage.jsx';
import LoginPage from './LoginPage.jsx';
import ModulePage from './ModulePage.jsx';
import QualityPage from './QualityPage.jsx';
import QuotationsPage from './QuotationsPage.jsx';
import ServiceOrdersPage from './ServiceOrdersPage.jsx';
import SettingsPage from './SettingsPage.jsx';

export function App() {
  const [path, setPath] = useState(getCurrentPath);
  const [user, setUser] = useState(null);
  const [isCheckingSession, setIsCheckingSession] = useState(true);
  const [now, setNow] = useState(() => new Date());

  useEffect(() => {
    function handleRouteChange() {
      setPath(getCurrentPath());
    }

    window.addEventListener('popstate', handleRouteChange);
    window.addEventListener('hashchange', handleRouteChange);

    return () => {
      window.removeEventListener('popstate', handleRouteChange);
      window.removeEventListener('hashchange', handleRouteChange);
    };
  }, []);

  useEffect(() => {
    let isMounted = true;

    async function checkSession() {
      if (!getAccessToken()) {
        if (isMounted) {
          setIsCheckingSession(false);
        }

        if (path !== '/login') {
          navigate('/login');
        }

        return;
      }

      try {
        const currentUser = await getCurrentUser();

        if (isMounted) {
          setUser(currentUser);

          if (path === '/login') {
            navigate('/dashboard');
          }
        }
      } catch {
        clearTokens();

        if (isMounted) {
          setUser(null);
          navigate('/login');
        }
      } finally {
        if (isMounted) {
          setIsCheckingSession(false);
        }
      }
    }

    checkSession();

    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), 60000);
    return () => window.clearInterval(timer);
  }, []);

  function handleLogout() {
    clearTokens();
    setUser(null);
    navigate('/login');
  }

  if (isCheckingSession) {
    return (
      <main className="loading-screen">
        <BrandLockup compact />
        <span>Cargando MYC SYSTEM</span>
      </main>
    );
  }

  if (path === '/login') {
    return <LoginPage onAuthenticated={setUser} />;
  }

  if (!user) {
    navigate('/login');
    return null;
  }

  const selectedModule = modules.find((module) => path === module.path);
  const showModuleNavigation = Boolean(selectedModule);
  const layoutSubtitle = selectedModule ? formatModuleDateTime(now) : 'Sistema principal';

  return (
    <AppLayout
      onLogout={handleLogout}
      showSidebar={showModuleNavigation}
      subtitle={layoutSubtitle}
      user={user}
    >
      {selectedModule?.key === 'clients' ? (
        <ClientsPage />
      ) : selectedModule?.key === 'quotations' ? (
        <QuotationsPage />
      ) : selectedModule?.key === 'serviceOrders' ? (
        <ServiceOrdersPage />
      ) : selectedModule?.key === 'equipment' ? (
        <EquipmentPage module={selectedModule} timestamp={now} />
      ) : selectedModule?.key === 'fieldSheets' ? (
        <FieldSheetsPage module={selectedModule} timestamp={now} />
      ) : selectedModule?.key === 'certificates' ? (
        <CertificatesPage />
      ) : selectedModule?.key === 'quality' ? (
        <QualityPage />
      ) : selectedModule?.key === 'settings' ? (
        <SettingsPage />  
      ) : selectedModule ? (
        <ModulePage module={selectedModule} timestamp={now} />
      ) : (
        <DashboardHome user={user} />
      )}
    </AppLayout>
  );
}

export default App;