import React, { useEffect, useState } from 'react';

import AppLayout from '../components/AppLayout.jsx';
import AccessDenied from '../components/AccessDenied.jsx';
import BrandLockup from '../components/BrandLockup.jsx';
import { modules } from '../constants/navigation.js';
import { clearPortalTokens, clearTokens, getAccessToken, getClientPortalProfile, getCurrentUser, getPortalAccessToken, portalLogout } from '../services/api.js';
import BillingPage from './BillingPage.jsx';
import { formatModuleDateTime } from '../utils/formatters.js';
import { getCurrentPath, navigate } from '../utils/routing.js';
import CertificatesPage from './CertificatesPage.jsx';
import ClientsPage from './ClientsPage.jsx';
import CapturePage from './CapturePage.jsx';
import DashboardHome from './DashboardHome.jsx';
import DocumentLibraryPage from './DocumentLibraryPage.jsx';
import EquipmentPage from './EquipmentPage.jsx';
import FlowTestPage from './FlowTestPage.jsx';
import LoginPage from './LoginPage.jsx';
import ModulePage from './ModulePage.jsx';
import CommunicationsPage from './CommunicationsPage.jsx';
import ProceduresPage from './ProceduresPage.jsx';
import QualityPage from './QualityPage.jsx';
import QuotationsPage from './QuotationsPage.jsx';
import ResolutionCenterPage from './ResolutionCenterPage.jsx';
import ServiceOrdersPage from './ServiceOrdersPage.jsx';
import LabWorkOrderGroupsPage from './LabWorkOrderGroupsPage.jsx';
import SettingsPage from './SettingsPage.jsx';
import StandardsPage from './StandardsPage.jsx';
import UncertaintyPage from './UncertaintyPage.jsx';
import SignatureLabPage from './SignatureLabPage.jsx';
import DocumentDesignerLabPage from './labs/DocumentDesignerLabPage.jsx';
import FieldSheetLabPage from './labs/FieldSheetLabPage.jsx';
import { canAccessModule, hasAnyPermission, isClientPortalUser } from '../utils/accessControl.js';
import ClientPortalApp from '../portal/ClientPortalApp.jsx';
import PortalAccessPage from '../portal/PortalAccessPage.jsx';

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
      const portalPath = path.startsWith('/portal');
      const publicPortalPath = path === '/portal/login' || path === '/portal/registro' || path === '/portal/verificar-correo' || path.startsWith('/portal/invitacion/');
      if (publicPortalPath) {
        if (isMounted) setIsCheckingSession(false);
        return;
      }
      const token = portalPath ? getPortalAccessToken() : getAccessToken();
      if (!token) {
        if (isMounted) {
          setIsCheckingSession(false);
        }

        if (path !== '/login') {
          navigate(portalPath ? '/portal/login' : '/login');
        }

        return;
      }

      try {
        const currentUser = portalPath ? await getClientPortalProfile() : await getCurrentUser();

        if (isMounted) {
          setUser(currentUser);

          if (path === '/login') {
            navigate(isClientPortalUser(currentUser) ? '/portal' : '/dashboard');
          }
        }
      } catch {
        if (portalPath) clearPortalTokens(); else clearTokens();

        if (isMounted) {
          setUser(null);
          navigate(portalPath ? '/portal/login' : '/login');
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
    if (isClientPortalUser(user)) {
      portalLogout().catch(() => clearPortalTokens());
      clearPortalTokens();
    } else clearTokens();
    setUser(null);
    navigate(isClientPortalUser(user) ? '/portal/login' : '/login');
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

  if (path === '/portal/login' || path === '/portal/registro' || path === '/portal/verificar-correo' || path.startsWith('/portal/invitacion/')) {
    return <PortalAccessPage onAuthenticated={setUser} path={path} />;
  }

  if (!user) {
    navigate(path.startsWith('/portal') ? '/portal/login' : '/login');
    return null;
  }

  if (isClientPortalUser(user)) {
    return <ClientPortalApp path={path} onLogout={handleLogout} user={user} />;
  }

  if (path.startsWith('/portal')) {
    navigate('/dashboard');
    return null;
  }

  const isCommunicationsCenter = path === '/communications' || path === '/notifications';
  const selectedModule = modules.find(
    (module) => path === module.path || module.legacyPaths?.includes(path)
  );
  const showModuleNavigation = Boolean(selectedModule) || isCommunicationsCenter;
  const layoutSubtitle = selectedModule
    ? formatModuleDateTime(now)
    : isCommunicationsCenter
      ? 'Centro de comunicaciones'
      : 'Sistema principal';
  const isAuthorizedModule = !selectedModule || canAccessModule(selectedModule, user);
  const isLabPath = [
    '/dashboard/field-sheet-lab',
    '/dashboard/field-sheet-preview',
    '/signature-lab',
    '/document-designer-lab',
  ].includes(path);
  const canAccessLabs = hasAnyPermission(user, ['settings.manage']);

  let content = null;
  if ((selectedModule && !isAuthorizedModule) || (isLabPath && !canAccessLabs)) {
    content = <AccessDenied />;
  } else if (path === '/dashboard/field-sheet-lab' || path === '/dashboard/field-sheet-preview') {
    content = <FieldSheetLabPage />;
  } else if (path === '/signature-lab') {
    content = <SignatureLabPage />;
  } else if (path === '/document-designer-lab') {
    content = <DocumentDesignerLabPage />;
  }

  return (
    <AppLayout
      onLogout={handleLogout}
      showSidebar={showModuleNavigation}
      subtitle={layoutSubtitle}
      user={user}
    >
      {content || (isCommunicationsCenter ? (
        <CommunicationsPage user={user} />
      ) : selectedModule?.key === 'clients' ? (
        <ClientsPage user={user} />
      ) : selectedModule?.key === 'resolutions' ? (
        <ResolutionCenterPage />
      ) : selectedModule?.key === 'quotations' ? (
        <QuotationsPage user={user} />
      ) : selectedModule?.key === 'serviceOrders' ? (
        <ServiceOrdersPage user={user} />
      ) : selectedModule?.key === 'labWorkOrderGroups' ? (
        <LabWorkOrderGroupsPage user={user} />
      ) : selectedModule?.key === 'equipment' ? (
        <EquipmentPage module={selectedModule} timestamp={now} />
      ) : selectedModule?.key === 'certificates' ? (
        <CertificatesPage user={user} />
      ) : selectedModule?.key === 'capture' ? (
        <CapturePage />
      ) : selectedModule?.key === 'quality' ? (
        <QualityPage />
      ) : selectedModule?.key === 'documentControl' ? (
        <DocumentLibraryPage user={user} />
      ) : selectedModule?.key === 'standards' ? (
        <StandardsPage />
      ) : selectedModule?.key === 'procedures' ? (
        <ProceduresPage />
      ) : selectedModule?.key === 'uncertainty' ? (
        <UncertaintyPage />
      ) : selectedModule?.key === 'finance' ? (
        <BillingPage user={user} />
      ) : selectedModule?.key === 'flowTest' ? (
        <FlowTestPage />
      ) : selectedModule?.key === 'settings' ? (
        <SettingsPage user={user} />
      ) : selectedModule ? (
        <ModulePage module={selectedModule} timestamp={now} />
      ) : (
        <DashboardHome user={user} />
      ))}
    </AppLayout>
  );
}

export default App;
