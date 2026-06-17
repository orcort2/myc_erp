import {
  BadgeCheck,
  Banknote,
  CalendarDays,
  ClipboardList,
  FileCheck2,
  FileText,
  Gauge,
  MessageSquareText,
  Wrench
} from 'lucide-react';

import { ModuleCard } from '../components/ModuleCard.jsx';

const modules = [
  {
    icon: MessageSquareText,
    name: 'CRM y Leads',
    status: 'Base',
    description: 'Entrada de prospectos, datos fiscales, chat y conversion a cotizacion.'
  },
  {
    icon: FileText,
    name: 'Cotizaciones',
    status: 'Flujo',
    description: 'Folios MYC, versiones, recordatorios, revigencia y aceptacion.'
  },
  {
    icon: CalendarDays,
    name: 'Agenda',
    status: 'Operacion',
    description: 'Pre-servicio, fechas confirmadas y datos documentales ajustables.'
  },
  {
    icon: ClipboardList,
    name: 'Llamados',
    status: 'Tecnico',
    description: 'Alta de equipos, agregados, autorizaciones y firma de conformidad.'
  },
  {
    icon: Wrench,
    name: 'Ordenes de servicio',
    status: 'Campo',
    description: 'Hojas de campo, evidencias, patrones, resultados y etiquetas.'
  },
  {
    icon: BadgeCheck,
    name: 'Calidad',
    status: 'Revision',
    description: 'Validacion de incertidumbres, certificados y documentacion final.'
  },
  {
    icon: FileCheck2,
    name: 'Certificados',
    status: 'Documento',
    description: 'Folios MYCA/MYCT, QR, codigos de barras, firmas y liberacion.'
  },
  {
    icon: Banknote,
    name: 'Finanzas',
    status: 'Cobranza',
    description: 'Pagos, prefacturas, timbrado, saldos y desbloqueo documental.'
  }
];

export function App() {
  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <Gauge size={24} />
          <div>
            <strong>ERP MYC</strong>
            <span>Sistema de calidad</span>
          </div>
        </div>
        <nav className="nav-list">
          {modules.map((module) => (
            <a href={`#${module.name}`} key={module.name}>
              {module.name}
            </a>
          ))}
        </nav>
      </aside>

      <section className="workspace">
        <header className="workspace-header">
          <div>
            <p>Base del sistema</p>
            <h1>Control operativo MYC</h1>
          </div>
          <button type="button">Nueva cotizacion</button>
        </header>

        <section className="flow-strip" aria-label="Flujo principal">
          <span>Lead</span>
          <span>Cotizacion</span>
          <span>Agenda</span>
          <span>Llamado</span>
          <span>Orden</span>
          <span>Certificado</span>
          <span>Pago</span>
          <span>Cierre</span>
        </section>

        <section className="module-grid">
          {modules.map((module) => (
            <ModuleCard key={module.name} module={module} />
          ))}
        </section>
      </section>
    </main>
  );
}

