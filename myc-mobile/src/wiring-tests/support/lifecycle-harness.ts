// Harness de lifecycle: ejecuta el WorkOrdersScreen y el LabTechnicalCapture
// REALES sobre el reconciliador real de React (react-dom/client) con un DOM
// mínimo en memoria. Sólo se sustituyen los puertos nativos/expo, la sesión,
// el bus de notificaciones y la red. Sirve para observar montajes/desmontajes
// reales del subtree (algo que los tests de código fuente no pueden ver).
import { existsSync, readFileSync, statSync } from 'node:fs';
import { createRequire } from 'node:module';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import ts from 'typescript';

const here = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(here, '../../..');
const nodeRequire = createRequire(import.meta.url);

class FakeNode {
  nodeType = 1; parentNode: FakeNode | null = null; childNodes: FakeNode[] = []; style: Record<string, unknown> = {};
  attrs = new Map<string, string>(); text = ''; ownerDocument: any;
  constructor(public nodeName: string, ownerDocument: any, nodeType = 1) { this.ownerDocument = ownerDocument; this.nodeType = nodeType; }
  get tagName() { return this.nodeName.toUpperCase(); }
  get firstChild() { return this.childNodes[0] ?? null; }
  get lastChild() { return this.childNodes[this.childNodes.length - 1] ?? null; }
  get nextSibling() { const s = this.parentNode?.childNodes ?? []; return s[s.indexOf(this) + 1] ?? null; }
  get previousSibling() { const s = this.parentNode?.childNodes ?? []; return s[s.indexOf(this) - 1] ?? null; }
  get textContent(): string { return this.nodeType === 3 ? this.text : this.childNodes.map((c) => c.textContent).join(''); }
  set textContent(value: string) { this.childNodes.forEach((c) => { c.parentNode = null; }); this.childNodes = value ? [this.ownerDocument.createTextNode(value)] : []; this.childNodes.forEach((c) => { c.parentNode = this; }); }
  get nodeValue() { return this.text; }
  set nodeValue(value: string) { this.text = value; }
  set data(value: string) { this.text = value; }
  appendChild(child: FakeNode) { return this.insertBefore(child, null); }
  insertBefore(child: FakeNode, before: FakeNode | null) {
    child.parentNode?.removeChild(child);
    const index = before ? this.childNodes.indexOf(before) : this.childNodes.length;
    this.childNodes.splice(index < 0 ? this.childNodes.length : index, 0, child);
    child.parentNode = this; return child;
  }
  removeChild(child: FakeNode) { this.childNodes.splice(this.childNodes.indexOf(child), 1); child.parentNode = null; return child; }
  setAttribute(name: string, value: string) { this.attrs.set(name, String(value)); }
  removeAttribute(name: string) { this.attrs.delete(name); }
  getAttribute(name: string) { return this.attrs.get(name) ?? null; }
  addEventListener() {} removeEventListener() {}
  contains(other: FakeNode | null): boolean { for (let n = other; n; n = n.parentNode) if (n === this) return true; return false; }
}

function installDom() {
  const doc: any = new FakeNode('#document', null, 9);
  doc.ownerDocument = doc;
  doc.createElement = (name: string) => new FakeNode(name, doc);
  doc.createTextNode = (text: string) => { const n = new FakeNode('#text', doc, 3); n.text = text; return n; };
  doc.createComment = (text: string) => { const n = new FakeNode('#comment', doc, 8); n.text = text; return n; };
  doc.documentElement = doc.createElement('html'); doc.body = doc.createElement('body'); doc.activeElement = doc.body;
  doc.defaultView = { document: doc, getSelection: () => null, HTMLIFrameElement: class {} };
  (globalThis as any).window = doc.defaultView; (globalThis as any).document = doc;
  Object.defineProperty(globalThis, 'navigator', { value: { userAgent: 'node' }, configurable: true });
  (globalThis as any).IS_REACT_ACT_ENVIRONMENT = true;
  return doc;
}

export type Probe = {
  log: string[];
  /** Alertas con sus botones, para accionar confirmaciones. */
  alerts: { title: string; buttons: { text?: string; onPress?: () => void }[] }[];
  requests: string[];
  /** Peticiones con cuerpo ya parseado, en orden de emisión. */
  calls: { method: string; path: string; body: any }[];
  /** Eventos publicados con publishLocalChange. */
  published: Record<string, unknown>[];
};
export type Env = {
  user: Record<string, unknown>;
  detail: any; sheet: any;
  /** TechnicalReport devuelto por POST/GET technical-report. */
  report: any;
  /** Respuesta de POST /lab-work-orders (alta de OT). */
  created: any;
  /** Respuesta de POST .../signatures (recepción firmada). */
  signed: any;
  /** Si es true, POST technical-report responde 409. */
  failTechnicalReportCreate: boolean;
  failCaptureSave: boolean;
  /** Mensaje de validación que devuelve POST .../confirm-capture (422). */
  confirmCaptureError: string | null;
  /** Ancho de ventana simulado (iPhone 390 por defecto; 320 = SE/mini). */
  windowWidth: number;
  failEvidenceUpload: boolean;
  /** Estado de entrega del grupo (GET .../delivery); null = valor por defecto vacío. */
  deliveryStatus: any;
  /** Si es true, POST .../delivery responde 409 con este mensaje. */
  deliveryError: string | null;
  /** Respuesta por OT para GET detalle; si no existe se usa `detail`. */
  details: Record<number, any>;
  /** Gate opcional por petición de detalle (secuencia de llamadas). */
  detailGates: (Promise<void> | null)[];
  /** Gates por escritura (POST/PATCH) de field-sheet, en orden de llegada. */
  sheetWriteGates: (Promise<void> | null)[];
  params: Record<string, string>;
  listeners: Set<(event: any) => void>;
  session: { access_token: string };
};

export async function createLifecycleHarness() {
  const doc = installDom();
  const React: any = nodeRequire('react');
  const { createRoot } = nodeRequire('react-dom/client');
  const { act, createElement: h, useEffect, useRef } = React;
  const ts_ = ts;
  const probe: Probe = { log: [], alerts: [], requests: [], calls: [], published: [] };
  const registry = new Map<string, any>();
  const stubs = new Map<string, any>();
  const textOf = (node: any): string => (Array.isArray(node) ? node.map(textOf).join('') : typeof node === 'string' || typeof node === 'number' ? String(node) : node?.props ? textOf(node.props.children) : '');
  const stub = (name: string) => {
    if (!stubs.has(name)) {
      const C: any = (props: any) => {
        const label = props.label ?? props.accessibilityLabel;
        if (label) registry.set(String(label), props);
        else if (name === 'Pressable' && typeof props.onPress === 'function') registry.set(`pressable:${textOf(props.children)}`, props);
        if (name === 'Modal' && props.visible === false) return null;
        const children = typeof props.children === 'function' ? null : props.children;
        return h('div', null, typeof props.label === 'string' ? props.label : null, typeof props.title === 'string' ? props.title : null, name === 'ReadOnlyField' && typeof props.value === 'string' ? props.value : null, children);
      };
      C.displayName = name; stubs.set(name, C);
    }
    return stubs.get(name);
  };
  const allStubs = new Proxy({}, { get: (_t, key) => stub(String(key)) });
  const env: Env = {
    user: { id: 1, full_name: 'Tec', actor_type: 'internal', permissions: ['*', 'mobile.access', 'lab_work_orders.use'] },
    detail: null, sheet: null, report: null, created: null, signed: null, failTechnicalReportCreate: false, failCaptureSave: false, confirmCaptureError: null, windowWidth: 390, failEvidenceUpload: false, deliveryStatus: null, deliveryError: null, details: {}, detailGates: [], sheetWriteGates: [], params: {}, listeners: new Set(), session: { access_token: 't' },
  };
  const response = (body: unknown) => ({ ok: true, status: 200, headers: { get: () => null }, json: async () => body });
  let detailCalls = 0;
  let sheetWrites = 0;
  let nextEvidenceId = 0;
  const authorizedFetch = async (path: string, init: { method?: string; body?: string | FormData } = {}) => {
    probe.requests.push(`${init.method ?? 'GET'} ${path}`);
    probe.calls.push({ method: init.method ?? 'GET', path, body: init.body ? (typeof init.body === 'string' ? JSON.parse(init.body) : Object.fromEntries((init.body as unknown as { entries(): Iterable<[string, unknown]> }).entries())) : undefined });
    if (/\/signatures(\/individual)?$/.test(path) && init.method === 'POST') return response(env.signed ?? env.detail);
    if (/\/technical-report\/confirm-capture$/.test(path) && init.method === 'POST') {
      if (env.confirmCaptureError) {
        return { ok: false, status: 422, headers: { get: () => null }, json: async () => ({ detail: { code: 'TECHNICAL_REPORT_INCOMPLETE', message: env.confirmCaptureError, missing_fields: ['installation_date'] } }) };
      }
      env.report.status = 'ready_for_signatures';
      env.report.performed_by_name_snapshot = 'Tec';
      env.report.performed_at = '2026-10-08T15:30:00+00:00';
      return response(structuredClone(env.report));
    }
    if (/\/technical-report\/evidence\/\d+$/.test(path) && init.method === 'DELETE') {
      const id = Number(path.split('/').pop());
      env.report.evidence = env.report.evidence.filter((item: any) => item.id !== id).map((item: any, index: number) => ({ ...item, position: index + 1 }));
      return response(structuredClone(env.report));
    }
    if (/\/technical-report\/evidence$/.test(path) && init.method === 'POST') {
      const form = init.body as FormData;
      const created = {
        id: 900 + (nextEvidenceId += 1), technical_report_id: env.report.id, evidence_type: form.get('evidence_type'),
        mime_type: 'image/jpeg', sha256: 'a'.repeat(64), size_bytes: 1000, position: env.report.evidence.length + 1,
        caption: null, created_at: '2026-10-08T00:00:00Z',
      };
      if (env.failEvidenceUpload) return { ok: false, status: 413, headers: { get: () => null }, json: async () => ({ detail: 'demasiado grande' }) };
      env.report.evidence.push(created);
      if (env.report.status === 'draft') env.report.status = 'in_progress';
      return response(structuredClone(created));
    }
    if (/\/technical-report$/.test(path)) {
      if (init.method === 'POST' && env.failTechnicalReportCreate) {
        return { ok: false, status: 409, headers: { get: () => null }, json: async () => ({ detail: 'El equipo ya tiene un reporte técnico vigente' }) };
      }
      if (init.method === 'PATCH') {
        if (env.failCaptureSave) return { ok: false, status: 500, headers: { get: () => null }, json: async () => ({ detail: 'error' }) };
        const incoming = (JSON.parse(init.body as string) as { capture_values: Record<string, unknown> }).capture_values;
        const stored = Object.fromEntries(Object.entries({ ...env.report.capture_values, ...incoming }).filter(([, value]) => value !== null));
        env.report.capture_values = stored;
        if (Object.keys(stored).length && env.report.status === 'draft') env.report.status = 'in_progress';
        return response(structuredClone(env.report));
      }
      return response(structuredClone(env.report));
    }
    if (/\/equipment\/configured$|\/equipment\/\d+\/configured$/.test(path)) return response(env.detail);
    if (/\/mobile\/v1\/technician\/lab-work-orders(\/groups)?$/.test(path) && init.method === 'POST') return response(env.created ?? env.detail);
    if (/field-sheet-templates/.test(path)) return response([]);
    if (/\/delivery$/.test(path) && init.method === 'POST') {
      if (env.deliveryError) return { ok: false, status: 409, headers: { get: () => null }, json: async () => ({ detail: env.deliveryError }) };
      const status = env.deliveryStatus;
      if (status) {
        status.exhibitions = [...status.exhibitions, { id: 900, exhibition_number: status.exhibitions.length + 1, delivery_type: 'full', status: 'completed', delivered_at: '2026-10-08T17:00:00+00:00', recipient_name: 'Persona Recibe', items: [] }];
        status.delivered_equipment = status.total_equipment;
        status.pending_equipment = [];
        status.group_complete = true;
      }
      return response({ id: 900 });
    }
    if (/\/delivery$/.test(path)) return response(structuredClone(env.deliveryStatus ?? { exhibitions: [], delivered_equipment: 0, total_equipment: 1, pending_equipment: [], group_complete: false, pending_partial_delivery_ticket_id: null }));
    if (/\/field-sheet$/.test(path)) {
      if (init.method && init.method !== 'GET') { const gate = env.sheetWriteGates[sheetWrites++] ?? null; if (gate) await gate; }
      return response(env.sheet);
    }
    const match = /lab-work-orders\/(\d+)$/.exec(path);
    if (match) {
      const gate = env.detailGates[detailCalls++] ?? null;
      // El payload se congela al EMITIR la petición, como un servidor real:
      // una respuesta retenida llega con el estado de cuando se pidió.
      const payload = structuredClone(env.details[Number(match[1])] ?? env.detail);
      if (gate) await gate;
      return response(payload);
    }
    return response(/group-requests|lab-work-orders/.test(path) ? [] : {});
  };
  const rn: any = new Proxy({
    StyleSheet: { create: (s: unknown) => s, flatten: (s: unknown) => s, hairlineWidth: 1 },
    Platform: { OS: 'ios', select: (o: any) => o.ios ?? o.default },
    Alert: { alert: (title: string, _message?: string, buttons?: { text?: string; onPress?: () => void }[]) => { probe.log.push(`Alert:${title}`); probe.alerts.push({ title, buttons: buttons ?? [] }); } },
    Animated: { Value: class { setValue() {} }, timing: () => ({ start() {}, stop() {} }), View: stub('Animated.View') },
    AccessibilityInfo: { isReduceMotionEnabled: () => Promise.resolve(false), addEventListener: () => ({ remove() {} }) },
    Dimensions: { get: () => ({ width: 390, height: 844 }) },
    Keyboard: { addListener: () => ({ remove() {} }), dismiss() {} },
    useWindowDimensions: () => ({ width: env.windowWidth, height: 844 }),
  }, { get: (t: any, k) => (k in t ? t[k] : stub(String(k))) });
  const FadeIn = (props: any) => h('div', null, props.children);
  const ports: Record<string, unknown> = {
    react: React,
    'react/jsx-runtime': nodeRequire('react/jsx-runtime'),
    'react-native': rn,
    'react-native-safe-area-context': allStubs,
    'expo-router': { Redirect: stub('Redirect'), router: { push() {}, navigate() {} }, useLocalSearchParams: () => env.params },
    '@react-navigation/native': { useFocusEffect: (cb: () => void) => { useEffect(cb, [cb]); } },
    '@expo/vector-icons': allStubs,
    '@/src/auth/AuthProvider': { useAuth: () => ({ authorizedFetch, isLoading: false, refreshSession: async () => env.session, session: env.session, user: env.user }) },
    '@/src/notifications/NotificationSyncProvider': {
      useNotificationSync: () => ({ publishLocalChange(event: Record<string, unknown>) { probe.published.push(event); }, subscribe: (l: (e: any) => void) => { env.listeners.add(l); return () => env.listeners.delete(l); } }),
    },
    '@/src/api/client': { apiUrl: (p: string) => p, ApiError: class extends Error {}, readApiErrorDetail: async () => ({ message: 'x' }) },
    '@/src/design/primitives': new Proxy({}, { get: (_t, key) => (key === 'FadeIn' ? FadeIn : stub(String(key))) }),
  };
  const stubbedModules = new Set([
    '@/src/components/lab/LabClientSelector',
    '@/src/components/lab/ErpCalibrationLinkField',
    '@/src/design/MycDatePickerField',
  ]);
  const cache = new Map<string, { exports: any }>();
  const resolveFile = (base: string) => {
    for (const candidate of [`${base}.ts`, `${base}.tsx`, `${base}/index.ts`, `${base}/index.tsx`]) {
      if (existsSync(candidate) && statSync(candidate).isFile()) return candidate;
    }
    return null;
  };
  const load = (file: string): any => {
    const cached = cache.get(file);
    if (cached) return cached.exports;
    const js = ts_.transpileModule(readFileSync(file, 'utf8'), { fileName: file, compilerOptions: {
      target: ts_.ScriptTarget.ES2022, module: ts_.ModuleKind.CommonJS, jsx: ts_.JsxEmit.ReactJSX, esModuleInterop: true,
    } }).outputText;
    const mod = { exports: {} as any }; cache.set(file, mod);
    new Function('require', 'module', 'exports', js)((name: string) => requireFrom(dirname(file), name), mod, mod.exports);
    return mod.exports;
  };
  let wrapped: unknown = null;
  const requireFrom = (dir: string, name: string): any => {
    if (name in ports) return ports[name];
    if (stubbedModules.has(name)) return allStubs;
    if (name === '@/src/components/signatures/MobileSignatureFlow') {
      // Expone onSubmit/onComplete: la prueba firma con el flujo real de WorkOrdersScreen.
      return { MobileSignatureFlow: (props: any) => { registry.set('MobileSignatureFlow', props); return null; } };
    }
    if (name === '@/src/components/lab/LabPartialDeliveryRequest') {
      return { LabPartialDeliveryRequest: (props: any) => { registry.set('LabPartialDeliveryRequest', props); return h('div', null, 'LabPartialDeliveryRequest'); } };
    }
    if (name === '@/src/components/lab/LabDeliveryFlow') {
      // Expone las props reales del wizard de entrega (equipos, conformidad, onSubmit...).
      return { LabDeliveryFlow: (props: any) => { registry.set('LabDeliveryFlow', props); return h('div', null, 'LabDeliveryFlow'); } };
    }
    if (name === '@/src/components/lab/LabWorkOrderClientField') {
      // Expone sus props (onSelect) para elegir cliente desde la prueba.
      return { LabWorkOrderClientField: (props: any) => { registry.set('LabWorkOrderClientField', props); return null; } };
    }
    if (name === '@/src/components/lab/LabTechnicalCapture') {
      // Mismo componente real, observado: cada instancia registra montaje/desmontaje.
      wrapped ??= { LabTechnicalCapture: (props: any) => {
        const id = useRef(`ltc${probe.log.filter((l) => l.startsWith('LTC mount')).length + 1}`).current;
        useEffect(() => { probe.log.push(`LTC mount ${id}`); return () => { probe.log.push(`LTC unmount ${id}`); }; }, [id]);
        return h(load(resolve(ROOT, 'src/components/lab/LabTechnicalCapture.tsx')).LabTechnicalCapture, props);
      } };
      return wrapped;
    }
    if (name.startsWith('@/')) { const file = resolveFile(resolve(ROOT, name.slice(2))); if (file) return load(file); }
    if (name.startsWith('.')) { const file = resolveFile(resolve(dir, name)); if (file) return load(file); }
    if (/^(expo|react-native)/.test(name)) return allStubs;
    return nodeRequire(name);
  };

  const tick = async () => { for (let i = 0; i < 8; i += 1) await new Promise((r) => setTimeout(r, 0)); };
  const screen = load(resolve(ROOT, 'app/(technician)/work-orders.tsx')).default;
  const container = doc.createElement('div'); doc.body.appendChild(container);
  const root = createRoot(container);
  return {
    env, probe, registry, act: act as (callback: () => Promise<void>) => Promise<void>,
    /** Instala un proveedor de medios falso en la MISMA instancia de módulo que usa la pantalla. */
    setMediaProvider(provider: unknown) {
      load(resolve(ROOT, 'src/services/technical-report-media.ts')).setEvidenceMediaProvider(provider);
    },
    async mount() { await act(async () => { root.render(h(screen)); }); await tick(); },
    async flush() { await act(async () => { await tick(); }); },
    async emit(event: Record<string, unknown>) { await act(async () => { env.listeners.forEach((l) => l(event)); await tick(); }); },
    /** Varios eventos en ráfaga dentro de un único ciclo; `between` corre tras cada uno. */
    async emitBurst(events: Record<string, unknown>[], between: (index: number) => void | Promise<void> = () => {}) {
      await act(async () => {
        for (const [index, event] of events.entries()) {
          env.listeners.forEach((l) => l(event));
          await tick();
          await between(index);
        }
        await tick();
      });
    },
    /**
     * Ejecuta `during` SIN act() (React programa por sí mismo), de modo que el
     * DOM puede observarse a mitad de una operación asíncrona. `pending`, si se
     * da, es el botón cuya acción queda en curso mientras `during` corre.
     */
    async observe(during: (tools: ObserveTools) => Promise<void>, pending?: string) {
      const props = pending ? registry.get(pending) : null;
      if (pending && !props) throw new Error(`Sin botón "${pending}"`);
      const g = globalThis as any;
      g.IS_REACT_ACT_ENVIRONMENT = false;
      try {
        const running = props ? props.onPress() : null;
        await tick();
        await during({
          fire: async (event) => { env.listeners.forEach((l) => l(event)); await tick(); },
          tapRelated: async (folio) => {
            const key = [...registry.keys()].find((k) => k.startsWith(`pressable:${folio}`));
            if (!key) throw new Error(`Sin chip de OT ${folio}`);
            await registry.get(key).onPress(); await tick();
          },
          settle: tick,
        });
        await running;
        await tick();
      } finally { g.IS_REACT_ACT_ENVIRONMENT = true; }
    },
    /** Cambia el deep-link/params y fuerza un re-render del screen. */
    async navigateTo(workOrderId: number) {
      env.params = { workOrderId: String(workOrderId) };
      await act(async () => { env.listeners.forEach((l) => l({ event_type: 'app.foreground', source: 'foreground' })); await tick(); });
    },
    async press(label: string) {
      const props = registry.get(label);
      if (!props) throw new Error(`Sin botón "${label}". Disponibles: ${[...registry.keys()].join(' | ')}`);
      await act(async () => { await props.onPress(); await tick(); });
    },
    text: () => container.textContent as string,
    async unmount() { await act(async () => { root.unmount(); }); },
  };
}

export type ObserveTools = {
  fire(event: Record<string, unknown>): Promise<void>;
  tapRelated(folio: number): Promise<void>;
  settle(): Promise<void>;
};

export type LifecycleHarness = Awaited<ReturnType<typeof createLifecycleHarness>>;
