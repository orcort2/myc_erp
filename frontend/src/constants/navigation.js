import {
  BadgeCheck,
  Banknote,
  Boxes,
  Building2,
  ClipboardList,
  FileCheck2,
  FileText,
  FlaskConical,
  Gauge,
  MessageSquareText,
  Ruler,
  Settings,
  ShieldCheck
} from 'lucide-react';

export const navigation = [
  { label: 'Dashboard', icon: Gauge, path: '/dashboard' },
  { label: 'Clientes', icon: Building2, path: '/dashboard#clientes' },
  { label: 'CRM', icon: MessageSquareText, path: '/dashboard#crm' },
  { label: 'Ventas / Cotizaciones', icon: FileText, path: '/dashboard#cotizaciones' },
  { label: 'Servicios', icon: ShieldCheck, path: '/dashboard#servicios' },
  { label: 'Ordenes de servicio', icon: ClipboardList, path: '/dashboard#ordenes' },
  { label: 'Equipos', icon: Boxes, path: '/dashboard#equipos' },
  { label: 'Hojas de campo', icon: BadgeCheck, path: '/dashboard#hojas' },
  { label: 'Certificados', icon: FileCheck2, path: '/dashboard#certificados' },
  { label: 'Calidad', icon: ShieldCheck, path: '/dashboard#calidad' },
  { label: 'Patrones', icon: Ruler, path: '/dashboard#patrones' },
  { label: 'Procedimientos', icon: FlaskConical, path: '/dashboard#procedimientos' },
  { label: 'Finanzas', icon: Banknote, path: '/dashboard#finanzas' },
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
    key: 'crm',
    name: 'CRM',
    description: 'Prospectos, oportunidades y conversaciones comerciales.',
    icon: MessageSquareText,
    path: '/dashboard#crm',
    status: 'Pendiente'
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
    key: 'services',
    name: 'Servicios',
    description: 'Flujo operativo de laboratorio, ruta y programacion tecnica.',
    icon: ShieldCheck,
    path: '/dashboard#servicios',
    status: 'En desarrollo'
  },
  {
    key: 'serviceOrders',
    name: 'Ordenes de servicio',
    description: 'Planeacion, avance y cierre de trabajos autorizados.',
    icon: ClipboardList,
    path: '/dashboard#ordenes',
    status: 'Activo'
  },
  {
    key: 'equipment',
    name: 'Equipos',
    description: 'Instrumentos individuales vinculados a cada orden de servicio.',
    icon: Boxes,
    path: '/dashboard#equipos',
    status: 'Activo'
  },
  {
    key: 'fieldSheets',
    name: 'Hojas de campo',
    description: 'Registro tecnico por equipo, resultados y trazabilidad del trabajo.',
    icon: BadgeCheck,
    path: '/dashboard#hojas',
    status: 'Activo'
  },
  {
    key: 'certificates',
    name: 'Certificados',
    description: 'Generacion, revision y liberacion documental para clientes.',
    icon: FileCheck2,
    path: '/dashboard#certificados',
    status: 'Activo'
  },
  {
    key: 'quality',
    name: 'Calidad',
    description: 'Revision transversal, aprobacion y control final de certificados.',
    icon: ShieldCheck,
    path: '/dashboard#calidad',
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
    key: 'procedures',
    name: 'Procedimientos',
    description: 'Base de procedimientos de calibracion, perfiles y reglas de decision.',
    icon: FlaskConical,
    path: '/dashboard#procedimientos',
    status: 'En desarrollo'
  },
  {
    key: 'finance',
    name: 'Finanzas',
    description: 'Pagos, facturas y control de liberacion administrativa.',
    icon: Banknote,
    path: '/dashboard#finanzas',
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
  quality: 0,
  certificates: 0,
  certificatesReview: 0,
  certificatesApproved: 0,
  certificatesReleased: 0
};
