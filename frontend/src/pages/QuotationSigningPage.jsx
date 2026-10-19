import React, { useEffect, useState } from 'react';
import './QuotationSigningPage.css';
import mycLogo from '../assets/myc-logo.png';

const API = (import.meta.env.VITE_API_URL || '/api').replace(/\/$/, '');
const endpoint = (path) => API + '/public/quotation-signing/' + path;

export default function QuotationSigningPage() {
  const token = new URLSearchParams(window.location.hash.replace(/^#/, '')).get('token') || '';
  const [document, setDocument] = useState(null);
  const [pdfUrl, setPdfUrl] = useState('');
  const [challenge, setChallenge] = useState(null);
  const [code, setCode] = useState('');
  const [verified, setVerified] = useState(false);
  const [name, setName] = useState('');
  const [consent, setConsent] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [otpSent, setOtpSent] = useState(false);

  async function post(path, payload = {}) {
    const response = await fetch(endpoint(path), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      cache: 'no-store',
      body: JSON.stringify({ token, ...payload }),
    });
    if (!response.ok) {
      let detail = 'No fue posible completar la operación.';
      try { const data = await response.json(); detail = typeof data.detail === 'string' ? data.detail : detail; } catch {}
      throw new Error(detail);
    }
    return response;
  }

  useEffect(() => {
    if (!token) { setError('El enlace de firmado no es válido.'); return; }
    let cancelled = false;
    let url = '';
    (async () => {
      try {
        const info = await (await post('document')).json();
        const blob = await (await post('pdf')).blob();
        url = URL.createObjectURL(blob);
        if (!cancelled) { setDocument(info); setPdfUrl(url); }
      } catch (err) { if (!cancelled) setError(err.message); }
    })();
    return () => { cancelled = true; if (url) URL.revokeObjectURL(url); };
  }, [token]);

  async function action(callback) {
    setBusy(true); setError('');
    try { await callback(); } catch (err) { setError(err.message); }
    finally { setBusy(false); }
  }

  return (
    <main className="myc-signing">
      <header className="myc-signing__header"><img className="myc-signing__logo" src={mycLogo} alt="MYC" width="240" height="211" /><span>METROLOGÍA Y SERVICIOS</span><div className="myc-signing__secure">✓ Firma segura</div></header>
      <div className="myc-signing__content">
      <p className="myc-signing__eyebrow">PORTAL DE CLIENTES · FIRMA DIGITAL</p>
      <h1>{result ? 'Gracias por confiar en MYC.' : 'Su cotización, lista para revisar.'}</h1>
      <p className="myc-signing__lead">Revise su documento y complete la verificación para confirmar el servicio.</p>
      {error && <p role="alert" className="myc-signing__error">{error}</p>}
      {result ? (
        <section role="status" className="myc-signing__success"><div className="myc-signing__success-mark"><img src={mycLogo} alt="MYC Metrología y Servicios" width="240" height="211" /><b aria-hidden="true">✓</b></div><p className="myc-signing__eyebrow">ACEPTACIÓN REGISTRADA</p><h2>Su orden ha sido emitida.</h2><p>Gracias por confiar en Metrología y Servicios MYC. En breve, un asesor se pondrá en contacto con usted para coordinar la programación de su servicio.</p><div className="myc-signing__receipt">Confirmación {result.confirmation_folio || `#${result.acceptance_id}`}</div></section>
      ) : document ? (
        <>
          <div className="myc-signing__grid"><section className="myc-signing__document"><div className="myc-signing__document-bar"><div><strong>{document.filename}</strong><small>Documento oficial · PDF</small></div><a href={pdfUrl} download={document.filename || "cotizacion-myc.pdf"} className="myc-signing__download" aria-label="Descargar documento PDF">↓ Descargar</a></div>
          {pdfUrl && <iframe title="Cotización PDF" src={pdfUrl} className="myc-signing__pdf" />}
          </section><section className="myc-signing__form-panel"><div className="myc-signing__lock">✧</div><p className="myc-signing__eyebrow">VERIFICACIÓN DE IDENTIDAD</p><h2>{verified ? "Confirme su aceptación" : challenge ? "Verifique su correo" : "Protegemos su aceptación"}</h2><p className="myc-signing__description">{verified ? "Indique el nombre de la persona autorizada." : challenge ? "Introduzca el código de seis dígitos enviado a su correo." : "Enviaremos un código de seguridad al correo asociado a esta cotización."}</p>
          {!challenge && <button className={"myc-signing__primary myc-signing__otp-button" + (otpSent ? " is-sent" : "")} disabled={busy} onClick={() => action(async () => {
            const data = await (await post('otp/request')).json();
            setOtpSent(true);
            setChallenge(data);
          })}>{busy ? "Enviando código…" : otpSent ? "✓" : "Enviar código de verificación →"}</button>}
          {challenge && !verified && (<div className="myc-signing__fade"><p className="myc-signing__sent">✓ Código enviado correctamente</p>
            <form onSubmit={(event) => { event.preventDefault(); action(async () => {
              await post('otp/verify', { challenge_id: challenge.challenge_id, code });
              setVerified(true);
            }); }}>
              <label>Código de seis dígitos <input value={code} onChange={e => setCode(e.target.value.replace(/\\D/g, "").slice(0, 6))} inputMode="numeric" autoComplete="one-time-code" maxLength={6} pattern="[0-9]{6}" placeholder="000000" required /></label>
              <button className="myc-signing__primary" disabled={busy || code.length !== 6}>{busy ? "Verificando…" : "Verificar código →"}</button>
            </form></div>
          )}
          {verified && (
            <form className="myc-signing__fade" onSubmit={(event) => { event.preventDefault(); action(async () => {
              const data = await (await post('accept', {
                challenge_id: challenge.challenge_id, signer_name: name.trim(), consent,
              })).json();
              setResult(data);
            }); }}>
              <label>Nombre completo <input placeholder="Nombre y apellidos" autoComplete="name" value={name} onChange={e => setName(e.target.value)} minLength={2} maxLength={180} required /></label>
              <p>{document.consent_text}</p>
              <label><input type="checkbox" checked={consent} onChange={e => setConsent(e.target.checked)} required /> Acepto las condiciones indicadas</label>
              <button className="myc-signing__primary" disabled={busy || !consent || name.trim().length < 2}>{busy ? "Registrando aceptación…" : "Aceptar cotización ✓"}</button>
            </form>
          )}
          <p className="myc-signing__assurance">✓ Documento protegido y verificación por correo</p></section></div>
        </>
      ) : !error ? <p>Cargando documento…</p> : null}
      <footer className="myc-signing__footer">Metrología y Servicios MYC · Atención profesional en cada medición</footer>
      </div>
    </main>
  );
}
