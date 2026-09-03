import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

// Regresión: la OT abierta se cerraba espontáneamente ("vuelve al listado
// sin pulsar Cerrar"). Causa raíz demostrada: NotificationSyncProvider
// navegaba con router.push(target) para CUALQUIER notificación LAB
// (propia, ajena, foreground o background). router.push "always pushes a
// new route, and never pops or replaces to an existing route... you can
// push the current route multiple times" (doc oficial de expo-router)
// -- si el técnico ya estaba en /(technician)/work-orders con una OT
// abierta, tocar la notificación montaba una SEGUNDA instancia de
// WorkOrdersScreen (open=false de fábrica) encima de la existente. Eso se
// veía exactamente como "la OT se cerró y volvió al listado", aunque la
// instancia original (con su modal abierto) seguía viva, sólo oculta
// detrás de la nueva. router.navigate reutiliza/enfoca la pantalla ya
// montada en vez de apilar un duplicado.
//
// Estos tests son de "wiring" (leen el código fuente), consistente con el
// resto de esta carpeta: no hay infraestructura de render de componentes
// React Native en este repo (sin @testing-library/react-native), así que
// la política se prueba de forma estructural/exhaustiva en vez de
// reproducir la implementación línea por línea.

const workOrdersPath = resolve(
  dirname(fileURLToPath(import.meta.url)),
  '../../app/(technician)/work-orders.tsx',
);
const notificationSyncPath = resolve(
  dirname(fileURLToPath(import.meta.url)),
  '../notifications/NotificationSyncProvider.tsx',
);

const workOrdersSource = readFileSync(workOrdersPath, 'utf8');
const notificationSyncSource = readFileSync(notificationSyncPath, 'utf8');

test('NotificationSyncProvider nunca usa router.push para navegar a un deep link -- sólo router.navigate', () => {
  // router.push duplicaría la pantalla si ya está enfocada; router.navigate
  // reutiliza la instancia existente. Ningún deep link de notificación debe
  // volver a usar push.
  assert.doesNotMatch(notificationSyncSource, /router\.push\(/);
  const navigateCalls = notificationSyncSource.match(/router\.navigate\(/g) ?? [];
  // Los dos sitios que antes usaban push: handleResponse (tap directo) y el
  // replay de pendingTarget (login/077 diferido).
  assert.equal(navigateCalls.length, 2, 'se esperaban exactamente 2 llamadas a router.navigate (tap directo + replay diferido)');
});

test('el modal de OT sólo se cierra desde las tres rutas de intención explícita', () => {
  // Política (no implementación): setOpen(false) SÓLO puede vivir dentro de
  // closeFlow (botón Cerrar / Android back), performWorkOrderDeletion
  // (eliminación definitiva exitosa) o createWorkOrder (al enviar
  // exitosamente una SOLICITUD de grupo, que nunca abre un work order real
  // que deba permanecer visible). Cualquier otra aparición -- en un
  // efecto, un callback de suscripción, un refresh, etc. -- es la clase
  // exacta de bug que cerraba la OT sola.
  const ALLOWED_OWNERS = new Set(['closeFlow', 'performWorkOrderDeletion', 'createWorkOrder']);
  const FUNCTION_DECL = /^ {2}(?:async )?function (\w+)\(/;
  const lines = workOrdersSource.split('\n');

  function enclosingFunctionName(lineIndex: number): string | null {
    for (let i = lineIndex; i >= 0; i -= 1) {
      const match = FUNCTION_DECL.exec(lines[i]);
      if (match) return match[1];
    }
    return null;
  }

  const offenders: string[] = [];
  let occurrences = 0;
  lines.forEach((line, index) => {
    if (!line.includes('setOpen(false)')) return;
    occurrences += 1;
    const owner = enclosingFunctionName(index);
    if (!owner || !ALLOWED_OWNERS.has(owner)) {
      offenders.push(`línea ${index + 1} (dueño detectado: ${owner ?? 'ninguno'})`);
    }
  });

  assert.equal(
    offenders.length,
    0,
    `setOpen(false) apareció fuera de closeFlow/performWorkOrderDeletion/createWorkOrder: ${offenders.join('; ')}`,
  );
  // Si este número cambia, alguien agregó o quitó una ruta de cierre --
  // debe revisarse a propósito, no pasar desapercibido.
  assert.equal(occurrences, 3, 'se esperaban exactamente 3 apariciones de setOpen(false) en todo el archivo');
});

test('los efectos sensibles a refresh/notificación/sesión nunca tocan setOpen', () => {
  // Recorta cada bloque de efecto por sus anclas textuales (no por número
  // de línea, para no ser frágil a reordenamientos) y confirma que ninguno
  // contiene setOpen(.
  const blocks: { label: string; start: string; end: string }[] = [
    { label: 'refresh del listado (refresh)', start: 'const refresh = useCallback(async (reset = true) => {', end: '}, [debouncedClient, debouncedFolio, request, statusFilter]);' },
    { label: 'refreshActive', start: 'const refreshActive = useCallback(async (force = false) => {', end: '}, [refresh]);' },
    { label: 'useFocusEffect', start: "useFocusEffect(useCallback(() => { if (user) refreshActive(); }, [refreshActive, user]));", end: "useFocusEffect(useCallback(() => { if (user) refreshActive(); }, [refreshActive, user]));" },
    { label: 'subscribe() -- notificación in-app', start: 'useEffect(() => subscribe((event) => {', end: '}), [closureScope, refreshActive, request, signatureFlowState?.rootWorkOrderId, subscribe, user?.full_name, workOrder]);' },
    { label: 'deep link workOrderId (openedDeepLinkId)', start: 'const openedDeepLinkId = useRef<number | null>(null);', end: '}, [params.workOrderId, user]);' },
    { label: 'delivery status effect', start: "if (!workOrder || !['completed', 'partially_closed'].includes(workOrder.status)) {", end: '}, [workOrder?.id, workOrder?.status]);' },
  ];

  for (const block of blocks) {
    const startIndex = workOrdersSource.indexOf(block.start);
    assert.notEqual(startIndex, -1, `ancla de inicio no encontrada para "${block.label}" -- actualiza este test si el código se reestructuró`);
    const endIndex = workOrdersSource.indexOf(block.end, startIndex);
    assert.notEqual(endIndex, -1, `ancla de fin no encontrada para "${block.label}"`);
    const body = workOrdersSource.slice(startIndex, endIndex + block.end.length);
    assert.doesNotMatch(body, /setOpen\(/, `"${block.label}" no debe poder cerrar ni abrir el modal de OT`);
  }
});

test('onRequestClose del Modal principal apunta exclusivamente a closeFlow', () => {
  assert.match(workOrdersSource, /<Modal\s+animationType="slide"\s+onRequestClose=\{closeFlow\}\s+visible=\{open\}>/);
});
