import { ShieldCheck, UserRound } from 'lucide-react';
import React from 'react';

export default function ClientPortalProfile({ user }) {
  return (
    <div className="client-portal-page">
      <header className="client-portal-page-header"><div><span className="client-portal-eyebrow">Cuenta</span><h1>Mi perfil</h1><p>Información de la cuenta que tiene acceso al portal.</p></div><UserRound size={28} /></header>
      <section className="portal-profile-card">
        <div className="portal-profile-card__avatar"><UserRound size={34} /></div>
        <div className="portal-profile-card__identity"><small>Usuario del portal</small><h2>{user?.full_name ?? 'Cliente MYC'}</h2><p>{user?.email}</p></div>
        <div className="portal-profile-card__security"><ShieldCheck size={21} /><div><strong>Acceso protegido</strong><span>La información mostrada está limitada a la organización vinculada con tu cuenta.</span></div></div>
      </section>
      <section className="portal-notice"><strong>Actualización de datos</strong><p>Los cambios de razón social, contactos o información fiscal deben solicitarse directamente a MYC para conservar la trazabilidad administrativa.</p></section>
    </div>
  );
}
