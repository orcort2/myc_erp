import React, { useEffect, useState } from 'react';

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
    <main style={{ maxWidth: 900, margin: '30px auto', padding: 24, fontFamily: 'system-ui, sans-serif' }}>
      <h1>Mesa de Firmado MYC</h1>
      <p>Revisa la cotización antes de confirmar tu aceptación.</p>
      {error && <p role="alert" style={{ color: '#a11' }}>{error}</p>}
      {result ? (
        <section role="status"><h2>Cotización aceptada</h2><p>Confirmación #{result.acceptance_id}</p></section>
      ) : document ? (
        <>
          <p>Documento: {document.filename}</p>
          {pdfUrl && <iframe title="Cotización PDF" src={pdfUrl} style={{ width: '100%', height: 520, border: '1px solid #ddd' }} />}
          {!challenge && <button disabled={busy} onClick={() => action(async () => {
            const data = await (await post('otp/request')).json();
            setChallenge(data);
          })}>Enviar código de verificación</button>}
          {challenge && !verified && (
            <form onSubmit={(event) => { event.preventDefault(); action(async () => {
              await post('otp/verify', { challenge_id: challenge.challenge_id, code });
              setVerified(true);
            }); }}>
              <label>Código de seis dígitos <input value={code} onChange={e => setCode(e.target.value)} inputMode="numeric" pattern="[0-9]{6}" required /></label>
              <button disabled={busy}>Verificar código</button>
            </form>
          )}
          {verified && (
            <form onSubmit={(event) => { event.preventDefault(); action(async () => {
              const data = await (await post('accept', {
                challenge_id: challenge.challenge_id, signer_name: name.trim(), consent,
              })).json();
              setResult(data);
            }); }}>
              <label>Nombre completo <input value={name} onChange={e => setName(e.target.value)} minLength={2} maxLength={180} required /></label>
              <p>{document.consent_text}</p>
              <label><input type="checkbox" checked={consent} onChange={e => setConsent(e.target.checked)} required /> Acepto las condiciones indicadas</label>
              <button disabled={busy || !consent || name.trim().length < 2}>Aceptar cotización</button>
            </form>
          )}
        </>
      ) : !error ? <p>Cargando documento…</p> : null}
    </main>
  );
}
