import {
  Banknote,
  Building2,
  FileText,
  PlugZap,
  Server,
  ShieldCheck,
  SlidersHorizontal,
  Users,
} from 'lucide-react';

import AuditSettingsPanel from '../AuditSettingsPanel.jsx';
import FieldSheetTemplatesSettingsPanel from '../FieldSheetTemplatesSettingsPanel.jsx';
import UsersSettingsPanel from '../UsersSettingsPanel.jsx';
import CompanyBrand from '../company/CompanyBrand.jsx';
import CompanyDocuments from '../company/CompanyDocuments.jsx';
import CompanyErpIdentity from '../company/CompanyErpIdentity.jsx';
import CompanyIdentity from '../company/CompanyIdentity.jsx';
import CompanyLocations from '../company/CompanyLocations.jsx';
import ComingSoon from '../placeholders/ComingSoon.jsx';

export const settingsNavigation = [
  {
    id: 'company',
    title: 'Empresa e identidad',
    description: 'Identidad institucional, presencia, documentos y representación de la empresa.',
    icon: Building2,
    children: [
      {
        id: 'company-identity',
        title: '¿Cómo se identifica la empresa?',
        shortTitle: 'Identidad institucional',
        description: 'Nombre, razón social, contacto, ubicación y responsables.',
        component: CompanyIdentity,
      },
      {
        id: 'company-brand',
        title: '¿Qué imagen representa a la empresa?',
        shortTitle: 'Identidad visual',
        description: 'Logotipos, símbolos y recursos visuales institucionales.',
        component: CompanyBrand,
      },
      {
        id: 'company-documents',
        title: '¿Cómo se presentan los documentos?',
        shortTitle: 'Presentación documental',
        description: 'Encabezados, pies, datos institucionales y criterios de presentación.',
        component: CompanyDocuments,
      },
      {
        id: 'company-locations',
        title: '¿Qué sedes tiene la empresa?',
        shortTitle: 'Sedes',
        description: 'Domicilios, sucursales y puntos de operación.',
        component: CompanyLocations,
      },
      {
        id: 'company-erp-identity',
        title: '¿Cómo se muestra la empresa dentro del ERP?',
        shortTitle: 'Identidad en el ERP',
        description: 'Nombre corto, emblema y presentación interna.',
        component: CompanyErpIdentity,
      },
    ],
  },
  {
    id: 'users',
    title: 'Usuarios y seguridad',
    description: 'Usuarios, roles, accesos y controles de seguridad.',
    icon: Users,
    children: [
      {
        id: 'user-management',
        title: '¿Quién puede utilizar el ERP?',
        shortTitle: 'Usuarios',
        description: 'Alta, edición, roles y estado de las cuentas de usuario.',
        component: UsersSettingsPanel,
      },
    ],
  },
  {
    id: 'operations',
    title: 'Operación',
    description: 'Parámetros seguros que gobiernan la operación cotidiana.',
    icon: SlidersHorizontal,
    component: ComingSoon,
  },
  {
    id: 'documents',
    title: 'Documentos y plantillas',
    description: 'Plantillas, familias documentales y herramientas de diseño.',
    icon: FileText,
    children: [
      {
        id: 'field-sheet-templates',
        title: '¿Cómo se administran las hojas de campo?',
        shortTitle: 'Panel maestro',
        description: 'Plantillas, familias y catálogos de hojas de campo.',
        component: FieldSheetTemplatesSettingsPanel,
      },
    ],
  },
  {
    id: 'billing',
    title: 'Facturación y pagos',
    description: 'Preferencias fiscales, financieras y de cobranza.',
    icon: Banknote,
    component: ComingSoon,
  },
  {
    id: 'integrations',
    title: 'Integraciones',
    description: 'Conexiones con proveedores y servicios externos.',
    icon: PlugZap,
    component: ComingSoon,
  },
  {
    id: 'governance',
    title: 'Gobierno y auditoría',
    description: 'Trazabilidad, supervisión y registro de cambios.',
    icon: ShieldCheck,
    children: [
      {
        id: 'audit-log',
        title: '¿Qué cambios se han realizado en el ERP?',
        shortTitle: 'Auditoría',
        description: 'Consulta de acciones, responsables y valores modificados.',
        component: AuditSettingsPanel,
      },
    ],
  },
  {
    id: 'system',
    title: 'Sistema',
    description: 'Mantenimiento, comportamiento general y estado del ERP.',
    icon: Server,
    component: ComingSoon,
  },
];

export function findSettingsSection(sectionId) {
  return settingsNavigation.find((section) => section.id === sectionId) ?? null;
}

export function findSettingsChild(sectionId, childId) {
  const section = findSettingsSection(sectionId);
  return section?.children?.find((child) => child.id === childId) ?? null;
}

export function getDefaultSection() {
  return settingsNavigation[0] ?? null;
}

export function getDefaultChild(section) {
  return section?.children?.[0] ?? null;
}
