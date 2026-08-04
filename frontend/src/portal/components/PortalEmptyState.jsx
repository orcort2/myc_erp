import { Inbox } from 'lucide-react';
import React from 'react';

export default function PortalEmptyState({ title, description }) {
  return (
    <div className="portal-empty-state">
      <Inbox aria-hidden="true" size={28} />
      <strong>{title}</strong>
      <p>{description}</p>
    </div>
  );
}
