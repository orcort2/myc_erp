import {
  Banknote,
  Building2,
  FileCheck2,
  Files,
  FileText,
  Gauge,
  Network,
  Ruler,
  Settings,
  ShieldCheck
} from 'lucide-react';

export const navigation = [
  { label: 'Dashboard', icon: Gauge, path: '/dashboard' },
  { label: 'Resoluciones', icon: Network, path: '/resolutions' },
  { label: 'Clientes', icon: Building2, path: '/dashboard#clientes' },
  { label: 'Ventas / Cotizaciones', icon: FileText, path: '/dashboard#cotizaciones' },
  /*{ label: 'Catálogo MYC', icon: FileCheck2, path: '/dashboard#catalogo' },*/
  { label: 'Servicios', icon: ShieldCheck, path: '/dashboard#servicios' },
  { label: 'Control Documental', icon: Files, path: '/dashboard#control-documental' },
  { label: 'Patrones', icon: Ruler, path: '/dashboard#patrones' },
  { label: 'Facturación', icon: Banknote, path: '/dashboard#facturacion' },
  { label: 'Configuracion', icon: Settings, path: '/dashboard#configuracion' }
];

export const modules = [
  {
    key: 'resolutions',
    name: 'Centro de Resoluciones',
    description: 'Consola institucional para operar y auditar resoluciones.',
    icon: Network,
    path: '/resolutions',
    status: 'Activo'
  },
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
  /*{
    key: 'catalog',
    name: 'Catálogo MYC',
    description: 'Servicios, conceptos comerciales y base para cotizaciones.',
    icon: FileCheck2,
    path: '/dashboard#catalogo',
    status: 'Activo'
  },*/
  {
    key: 'serviceOrders',
    name: 'Servicios',
    description: 'Expediente Tecnico del Servicio con equipos, hojas, captura, calidad y certificados.',
    icon: ShieldCheck,
    path: '/dashboard#servicios',
    status: 'Activo'
  },
  {
    key: 'documentControl',
    name: 'Control Documental',
    description: 'Catalogo central de documentos controlados, revisiones, versiones y vigencias.',
    icon: Files,
    path: '/dashboard#control-documental',
    legacyPaths: ['/dashboard#biblioteca-documental'],
    status: 'Activo'
  },
  {
    key: 'standards',
    name: 'Patrones',
    description: 'Gestion de equipos patron, vigencias e incertidumbres por rango.',
    icon: Ruler,
    path: '/dashboard#patrones',
    status: 'Renovación'
  },
  {
    key: 'finance',
    name: 'Facturación',
    description: 'Facturas, pagos, cuentas por cobrar, notas de credito y configuracion fiscal administrativa.',
    icon: Banknote,
    path: '/dashboard#facturacion',
    status: 'Activo'
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
