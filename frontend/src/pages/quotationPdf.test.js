import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';
import { openQuotationPdfWindow } from '../utils/quotationPdfWindow.js';

// api.js has no imports; only Vite's build-time env needs replacing in Node.
const apiSource = readFileSync(new URL('../services/api.js', import.meta.url), 'utf8');
const api = await import(`data:text/javascript;base64,${Buffer.from(
  apiSource.replace('import.meta.env.VITE_API_URL', JSON.stringify('https://erp.example.test/api'))
).toString('base64')}`);
const pageSource = readFileSync(new URL('./QuotationsPage.jsx', import.meta.url), 'utf8');

function browser(t, { token = 'test-token', blocked = false } = {}) {
  const events = [];
  const revoked = [];
  const intervals = new Map();
  const timeouts = new Map();
  let timer = 0;
  const tab = new EventTarget();
  Object.assign(tab, {
    closed: false, opener: {},
    location: { href: 'about:blank', replace(url) { events.push(['navigate', url]); this.href = url; } },
    close() { this.closed = true; events.push(['close']); },
    focus() { events.push(['focus']); },
    print() { events.push(['print']); }
  });
  const win = {
    localStorage: { getItem: () => token },
    open(url, target) { events.push(['open', url, target]); return blocked ? null : tab; },
    setInterval(callback) { intervals.set(++timer, callback); return timer; },
    clearInterval(id) { intervals.delete(id); },
    setTimeout(callback) { timeouts.set(++timer, callback); return timer; },
    clearTimeout(id) { timeouts.delete(id); }
  };
  t.mock.method(globalThis, 'fetch', async (url, options) => {
    events.push(['fetch', url, options]);
    return new Response('%PDF-test', { headers: {
      'Content-Type': 'application/pdf',
      'Content-Disposition': 'inline; filename="Cotizacion_COT-1_Cliente.pdf"'
    } });
  });
  t.mock.method(URL, 'createObjectURL', (blob) => {
    assert.equal(blob.type, 'application/pdf');
    events.push(['blob']);
    return 'blob:https://erp.example.test/pdf-1';
  });
  t.mock.method(URL, 'revokeObjectURL', (url) => revoked.push(url));
  const previous = globalThis.window;
  globalThis.window = win;
  t.after(() => { globalThis.window = previous; });
  return { win, tab, events, revoked, intervals, timeouts };
}

function pageHarness(t, options) {
  const env = browser(t, options);
  const errors = [];
  const notices = [];
  const downloads = [];
  const context = vm.createContext({
    window: env.win, URL, openQuotationPdfWindow,
    downloadQuotationPdf: api.downloadQuotationPdf,
    selectedQuotation: { id: 42, folio: 'COT-1', client_id: 2 },
    quotations: [{ id: 43, folio: 'COT-2', client_id: 2 }],
    clientsById: new Map([[2, { name: 'Cliente' }]]),
    getClientDisplayName: (client) => client.name,
    setError: (message) => errors.push(message),
    setNotice: (message) => notices.push(message),
    document: {
      createElement: () => ({ click() { downloads.push({ href: this.href, filename: this.download }); } }),
      body: { appendChild() {}, removeChild() {} }
    }
  });
  // Execute the actual handlers without a JSX renderer, following this repo's
  // Node test setup. No duplicate implementation of page behavior in tests.
  function load(name) {
    const start = pageSource.search(new RegExp(`^(?:  )?(?:async )?function ${name}\\(`, 'm'));
    assert.notEqual(start, -1);
    const rest = pageSource.slice(start);
    const end = rest.slice(1).search(/\n(?:  )?(?:async )?function \w+\(/) + 1;
    assert.ok(end > 0);
    context[name] = vm.runInContext(`(${rest.slice(0, end).trim()})`, context);
  }
  for (const name of ['showAuthenticatedQuotationPdf', 'continueOpenQuotationPdf',
    'openTemplatePdfPreview', 'handleDownloadQuotationPdfConfirmed', 'mapTemplateFromApi', 'mapTemplatePayload']) load(name);
  context.defaultQuotationTemplate = {};
  return { ...env, errors, notices, downloads, context };
}

for (const [name, handler, mode, id] of [
  ['Imprimir', 'continueOpenQuotationPdf', 'print', 42],
  ['Vista PDF de prueba', 'openTemplatePdfPreview', undefined, 43]
]) {
  test(`${name}: reserves a blank tab, fetches with Bearer, navigates only to Blob`, async (t) => {
    const env = pageHarness(t);
    const task = env.context[handler](mode);
    assert.equal(env.events[0][0], 'open');
    assert.equal(env.events[0][1], 'about:blank');
    assert.equal(env.tab.opener, null);
    await task;
    const request = env.events.find(([event]) => event === 'fetch');
    assert.equal(request[1], `https://erp.example.test/api/quotations/${id}/pdf`);
    assert.equal(request[2].headers.Authorization, 'Bearer test-token');
    assert.equal(env.tab.location.href, 'blob:https://erp.example.test/pdf-1');
    assert.equal(env.events.filter(([event]) => event === 'print').length, 0);
    assert.deepEqual(env.revoked, []);
    env.tab.dispatchEvent(new Event('load'));
    assert.equal(env.events.filter(([event]) => event === 'print').length, mode === 'print' ? 1 : 0);
    env.tab.dispatchEvent(new Event('load'));
    assert.equal(env.events.filter(([event]) => event === 'print').length, mode === 'print' ? 1 : 0);
    assert.deepEqual(env.revoked, []);
    assert.equal(env.intervals.size, 0);
    assert.equal(env.timeouts.size, 0);
    env.tab.dispatchEvent(new Event('pagehide'));
    env.tab.close();
    assert.deepEqual(env.revoked, ['blob:https://erp.example.test/pdf-1']);
    assert.equal(env.intervals.size, 0);
    assert.equal(env.timeouts.size, 0);
  });
}

test('Download keeps the authenticated request and filename, with deferred revocation', async (t) => {
  const env = pageHarness(t);
  await env.context.handleDownloadQuotationPdfConfirmed();
  assert.equal(env.events.some(([event]) => event === 'open'), false);
  assert.equal(env.events.find(([event]) => event === 'fetch')[2].headers.Authorization, 'Bearer test-token');
  assert.deepEqual(env.downloads, [{ href: 'blob:https://erp.example.test/pdf-1', filename: 'Cotizacion_COT-1_Cliente.pdf' }]);
  assert.deepEqual(env.revoked, []);
  for (const callback of env.timeouts.values()) callback();
  assert.deepEqual(env.revoked, ['blob:https://erp.example.test/pdf-1']);
});

for (const handler of ['continueOpenQuotationPdf', 'openTemplatePdfPreview', 'handleDownloadQuotationPdfConfirmed']) {
  test(`${handler}: HTTP failure reaches the UI and closes the reserved empty tab`, async (t) => {
    const env = pageHarness(t);
    t.mock.method(globalThis, 'fetch', async () => new Response(JSON.stringify({ detail: 'Autenticación requerida' }), { status: 401 }));
    await env.context[handler]();
    assert.equal(env.errors.at(-1), 'Autenticación requerida');
    assert.equal(env.tab.closed, handler !== 'handleDownloadQuotationPdfConfirmed');
    assert.equal(env.events.some(([event]) => event === 'blob'), false);
    assert.equal(env.intervals.size, 0);
  });
}

test('Popup blocking reports an error before fetching', async (t) => {
  const env = pageHarness(t, { blocked: true });
  await env.context.continueOpenQuotationPdf();
  assert.match(env.errors.at(-1), /ventanas emergentes/);
  assert.equal(env.events.some(([event]) => event === 'fetch'), false);
});

test('Closing the blank tab during fetch creates no object URL', async (t) => {
  const env = browser(t);
  let resolve;
  const task = openQuotationPdfWindow(() => new Promise((done) => { resolve = done; }));
  env.tab.close();
  resolve({ blob: new Blob(['%PDF'], { type: 'application/pdf' }), filename: 'quotation.pdf' });
  assert.equal(await task, null);
  assert.equal(env.events.some(([event]) => event === 'blob'), false);
});

test('Initial blank load cannot print; leaving a consumed PDF releases its URL', async (t) => {
  const env = browser(t);
  let resolve;
  const task = openQuotationPdfWindow(() => new Promise((done) => { resolve = done; }), { print: true });
  env.tab.dispatchEvent(new Event('load'));
  resolve({ blob: new Blob(['%PDF'], { type: 'application/pdf' }), filename: 'quotation.pdf' });
  await task;
  const url = env.tab.location.href;
  env.tab.location.href = 'about:blank';
  env.tab.dispatchEvent(new Event('load'));
  assert.equal(env.events.some(([event]) => event === 'print'), false);
  env.tab.location.href = url;
  env.tab.dispatchEvent(new Event('load'));
  env.tab.dispatchEvent(new Event('pagehide'));
  env.tab.location.href = 'https://example.test';
  assert.deepEqual(env.revoked, [url]);
});

test('Print failure and viewer load timeout report a usable fallback without closing the PDF', async (t) => {
  const env = pageHarness(t);
  await env.context.continueOpenQuotationPdf('print');
  env.tab.print = () => { throw new Error('unsupported'); };
  env.tab.dispatchEvent(new Event('load'));
  assert.match(env.errors.at(-1), /opción Imprimir del visor/);
  assert.equal(env.tab.closed, false);
  await env.context.continueOpenQuotationPdf('print');
  for (const callback of env.timeouts.values()) callback();
  assert.match(env.errors.at(-1), /no confirmó la carga/);
  assert.equal(env.tab.closed, false);
  assert.equal(env.intervals.size, 0);
  assert.equal(env.timeouts.size, 0);
  assert.deepEqual(env.revoked, []);
});

test('Authenticated PDF service preserves extended and fallback filenames, and handles absent tokens', async (t) => {
  const env = browser(t, { token: null });
  t.mock.method(globalThis, 'fetch', async (_url, options) => {
    assert.equal(options.headers.Authorization, undefined);
    return new Response('%PDF', { headers: {
      'Content-Type': 'application/pdf', 'Content-Disposition': "inline; filename*=UTF-8''Cotizaci%C3%B3n.pdf"
    } });
  });
  assert.equal((await api.downloadQuotationPdf(42)).filename, 'Cotización.pdf');
  t.mock.method(globalThis, 'fetch', async () => new Response('%PDF', { headers: { 'Content-Type': 'application/pdf' } }));
  assert.equal((await api.downloadQuotationPdf(42, { folio: 'COT 42' }, 'José SA')).filename, 'Cotizacion_COT-42_Jose-SA.pdf');
  assert.deepEqual(env.revoked, []);
});

test('HTTP non-JSON failures and network failures are not treated as PDFs', async (t) => {
  browser(t);
  t.mock.method(globalThis, 'fetch', async () => new Response('forbidden', { status: 403 }));
  await assert.rejects(api.downloadQuotationPdf(42), /No tienes permiso/);
  t.mock.method(globalThis, 'fetch', async () => { throw new TypeError('offline'); });
  await assert.rejects(api.downloadQuotationPdf(42), /No fue posible conectar/);
});

test('No PDF action navigates to the protected endpoint or embeds tokens in URLs', () => {
  assert.doesNotMatch(pageSource, /getQuotationPdfUrl|window\.open\(/);
  assert.doesNotMatch(apiSource.slice(apiSource.indexOf('export function getQuotationPdfUrl'), apiSource.indexOf('export async function changeQuotationStatus')), /[?&](?:token|access_token|authorization)=/i);
});

test('Template mapping and payload preserve all eight boolean flag combinations', (t) => {
  const { context } = pageHarness(t);
  for (const summary of [true, false]) for (const full of [true, false]) for (const signature of [true, false]) {
    const flags = { show_summary_terms: summary, show_full_terms: full, show_acceptance_signature: signature };
    const payload = context.mapTemplatePayload(context.mapTemplateFromApi(flags));
    for (const [name, value] of Object.entries(flags)) assert.equal(payload[name], value);
  }
});

test('Print observes the loaded Blob document if navigation discards the blank window load listener', async (t) => {
  const env = browser(t);
  await openQuotationPdfWindow(() => api.downloadQuotationPdf(42), { print: true });
  env.tab.document = { readyState: 'loading' };
  for (const callback of env.intervals.values()) callback();
  assert.equal(env.events.filter(([name]) => name === 'print').length, 0);
  env.tab.document.readyState = 'complete';
  for (const callback of env.intervals.values()) callback();
  assert.equal(env.events.filter(([name]) => name === 'print').length, 1);
  assert.equal(env.intervals.size, 0);
  assert.equal(env.timeouts.size, 0);
});

for (const print of [false, true]) {
  test(`Isolated viewer stops all timers at the explicit deadline (print=${print})`, async (t) => {
    const env = browser(t);
    const errors = [];
    t.mock.method(env.win, 'setTimeout', (callback, delay) => {
      assert.equal(delay, 60000);
      env.timeouts.set(100, callback);
      return 100;
    });
    await openQuotationPdfWindow(() => api.downloadQuotationPdf(42), { print, onError: (error) => errors.push(error) });
    Object.defineProperty(env.tab, 'document', { get() { throw new Error('isolated'); } });
    for (const callback of env.intervals.values()) callback();
    for (const callback of env.timeouts.values()) callback();
    assert.equal(env.intervals.size, 0);
    assert.equal(env.timeouts.size, 0);
    assert.equal(errors.length, Number(print));
    assert.deepEqual(env.revoked, []);
    env.tab.dispatchEvent(new Event('load'));
    assert.equal(env.events.some(([event]) => event === 'print'), false);
  });
}

test('Cached PDF retains its URL without keeping timers alive', async (t) => {
  const env = browser(t);
  await openQuotationPdfWindow(() => api.downloadQuotationPdf(42));
  env.tab.dispatchEvent(new Event('load'));
  const event = new Event('pagehide');
  Object.defineProperty(event, 'persisted', { value: true });
  env.tab.dispatchEvent(event);
  assert.deepEqual(env.revoked, []);
  assert.equal(env.intervals.size, 0);
  assert.equal(env.timeouts.size, 0);
});

test('Navigation failure closes the reserved tab, revokes the unused Blob and clears timers', async (t) => {
  const env = browser(t);
  env.tab.location.replace = () => { throw new Error('navigation failed'); };
  await assert.rejects(openQuotationPdfWindow(() => api.downloadQuotationPdf(42)), /navigation failed/);
  assert.equal(env.tab.closed, true);
  assert.equal(env.revoked.length, 1);
  assert.equal(env.intervals.size, 0);
  assert.equal(env.timeouts.size, 0);
});
