import React from 'react';
import PortalEmptyState from '../components/PortalEmptyState.jsx';

export default function ClientPortalRecords({ title, eyebrow, description, items, loading, renderTitle, renderMeta }) {
  return <div className="client-portal-page"><header className="client-portal-page-header"><div><span className="client-portal-eyebrow">{eyebrow}</span><h1>{title}</h1><p>{description}</p></div></header>{loading ? <div className="portal-loading">Cargando información…</div> : items.length ? <div className="portal-card-list">{items.map((item) => <article className="portal-record-card" key={item.id}><div className="portal-record-card__main"><h2>{renderTitle(item)}</h2><div className="portal-record-card__meta">{renderMeta(item)}</div></div></article>)}</div> : <PortalEmptyState title="Sin información disponible" description="Los registros autorizados aparecerán aquí." />}</div>;
}
