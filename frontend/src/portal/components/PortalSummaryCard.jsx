import React from 'react';

export default function PortalSummaryCard({ icon: Icon, label, value, detail, onClick }) {
  const Element = onClick ? 'button' : 'article';
  return (
    <Element className="portal-summary-card" onClick={onClick} type={onClick ? 'button' : undefined}>
      <span className="portal-summary-card__icon"><Icon aria-hidden="true" size={22} /></span>
      <span className="portal-summary-card__body">
        <small>{label}</small>
        <strong>{value}</strong>
        <span>{detail}</span>
      </span>
    </Element>
  );
}
