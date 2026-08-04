import React from 'react';

export default function PortalStatusBadge({ presentation }) {
  return (
    <span className={`portal-status portal-status--${presentation?.tone ?? 'neutral'}`}>
      {presentation?.label ?? 'Sin estado'}
    </span>
  );
}
