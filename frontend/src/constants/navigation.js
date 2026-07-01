import {
  Banknote,
  Building2,
  FileCheck2,
  FileText,
  Gauge,
  Ruler,
  Settings,
  ShieldCheck
} from 'lucide-react';

export const navigation = [
  { label: 'Dashboard', icon: Gauge, path: '/dashboard' },
  { label: 'Clientes', icon: Building2, path: '/dashboard#clientes' },
  { label: 'Ventas / Cotizaciones', icon: FileText, path: '/dashboard#cotizaciones' },
  { label: 'Catálogo MYC', icon: FileCheck2, path: '/dashboard#catalogo' },
  { label: 'Servicios', icon: ShieldCheck, path: '/dashboard#servicios' },
  { label: 'Patrones', icon: Ruler, path: '/dashboard#patrones' },
  { label: 'Facturación', icon: Banknote, path: '/dashboard#facturacion' },
  { label: 'Configuracion', icon: Settings, path: '/dashboard#configuracion' }
];

export const modules = [
  {
    key: 'clients',
    name: 'Clientes',
    description: 'Base comercial para cuentas, contactos y seguimiento operativo.',
    icon: Building2,
    path: '/dashboard#clientes',
    status: 'Activo'
  },
  {
    key: 'quotations',
    name: 'Ventas / Cotizaciones',
    description: 'Propuestas, condiciones comerciales y origen de servicios.',
    icon: FileText,
    path: '/dashboard#cotizaciones',
    status: 'Activo'
  },
  {
    key: 'catalog',
    name: 'Catálogo MYC',
    description: 'Servicios, conceptos comerciales y base para cotizaciones.',
    icon: FileCheck2,
    path: '/dashboard#catalogo',
    status: 'Activo'
  },
  {
    key: 'serviceOrders',
    name: 'Servicios',
    description: 'Expediente Tecnico del Servicio con equipos, hojas, captura, calidad y certificados.',
    icon: ShieldCheck,
    path: '/dashboard#servicios',
    status: 'Activo'
  },
  {
    key: 'standards',
    name: 'Patrones',
    description: 'Gestion de equipos patron, vigencias e incertidumbres por rango.',
    icon: Ruler,
    path: '/dashboard#patrones',
    status: 'En desarrollo'
  },
  {
    key: 'finance',
    name: 'Facturación',
    description: 'Pagos, facturas y control de liberacion administrativa.',
    icon: Banknote,
    path: '/dashboard#facturacion',
    status: 'Pendiente'
  },
  {
    key: 'settings',
    name: 'Configuracion',
    description: 'Usuarios, roles, permisos y parametros del sistema.',
    icon: Settings,
    path: '/dashboard#configuracion',
    status: 'En desarrollo'
  }
];

export const defaultCounts = {
  clients: 0,
  quotations: 0,
  serviceOrders: 0,
  equipment: 0,
  fieldSheets: 0,
  servicesScheduled: 0,
  servicesInProgress: 0,
  servicesClosed: 0,
  capturePending: 0,
  quality: 0,
  qualityPending: 0,
  certificates: 0,
  certificatesReview: 0,
  certificatesApproved: 0,
  certificatesReleased: 0,
  certificatesToRelease: 0,
  billingPending: 0,
  authenticationPending: 0,
  authenticatedCertificates: 0,
  returnedToTechnician: 0,
  etsAverageProgress: 0
};
