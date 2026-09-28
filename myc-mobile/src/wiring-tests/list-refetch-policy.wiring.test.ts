import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

/**
 * Wiring (análisis estático del código fuente, no validación visual): las
 * listas remotas no desmontan datos válidos al revalidar, y una renovación
 * silenciosa de sesión no re-dispara cargas. La máquina de estados se prueba
 * por separado en src/sync/list-load-state.test.ts.
 */
const root = resolve(dirname(fileURLToPath(import.meta.url)), '../..');
const read = (path: string) => readFileSync(resolve(root, path), 'utf8');

const screens = {
  'work-orders': read('app/(technician)/work-orders.tsx'),
  tickets: read('app/(technician)/tickets.tsx'),
  clients: read('app/(technician)/clients.tsx'),
};

// Deps del efecto que dispara la carga por filtros/identidad en cada pantalla.
// (Los efectos de deep-link conservan `user`: ya están protegidos por MOB-003.)
const loadTriggerDeps: Record<keyof typeof screens, string> = {
  'work-orders': '}, [debouncedSearch, statusFilter, userId]);',
  tickets: '}, [debouncedSearch, status, userId]);',
  clients: '}, [searchTerm, showInactive, userId]);',
};

for (const [name, source] of Object.entries(screens)) {
  test(`${name}: el spinner de pantalla depende de showsInitialSpinner, no de un loading reusado por refetch`, () => {
    assert.doesNotMatch(source, /setLoading\(true\)/);
    assert.doesNotMatch(source, /\{loading \? /);
    assert.match(source, /showsInitialSpinner\(listLoad\) \?/);
    assert.match(source, /beginListFetch\(listLoadRef\.current, /);
    assert.match(source, /settleListFetch\(listLoadRef\.current, 'success', userId\)/);
    assert.match(source, /settleListFetch\(listLoadRef\.current, 'error', userId\)/);
  });

  test(`${name}: el refetch muestra un indicador no destructivo y sólo la petición más reciente aplica`, () => {
    assert.match(source, /\{listLoad\.refetching && <RefetchIndicator \/>\}/);
    assert.match(source, /if \(requestId !== (listRequestSequence|requestSequence)\.current\) return;/);
    assert.match(source, /disabled=\{!canLoadMore\(listLoad\)\}/);
  });

  test(`${name}: los disparadores de carga usan la identidad estable user.id, no la referencia de user`, () => {
    assert.match(source, /const userId = user\?\.id \?\? null;/);
    assert.ok(source.includes(loadTriggerDeps[name as keyof typeof screens]));
    assert.match(source, /if \(plan\.discardData\) \{/);
  });
}

for (const name of ['work-orders', 'tickets'] as const) {
  const source = screens[name];
  test(`${name}: pull-to-refresh ya no vive dentro de un árbol que el refetch desmonta`, () => {
    assert.match(source, /<RefreshControl refreshing=\{listLoad\.pullRefreshing\} onRefresh=\{\(\) => refreshActive\(true, 'pull'\)\} \/>/);
    assert.doesNotMatch(source, /setRefreshing\(/);
  });

  test(`${name}: el focus sólo depende de la identidad (una renovación de sesión no lo re-ejecuta)`, () => {
    assert.match(source, /useFocusEffect\(useCallback\(\(\) => \{ if \(userId != null\) refreshActiveRef\.current\(\); \}, \[userId\]\)\);/);
    assert.match(source, /useEffect\(\(\) => \{ refreshActiveRef\.current = refreshActive; \}, \[refreshActive\]\);/);
  });
}

test('AuthProvider: authorizedFetch tiene identidad estable, fuera del useMemo que depende de session', () => {
  const source = read('src/auth/AuthProvider.tsx');
  const declaration = source.indexOf('const authorizedFetch = useCallback(async (path: string, init: RequestInit = {}): Promise<Response> => {');
  const memo = source.indexOf('const value = useMemo<AuthContextValue>(() => ({');
  assert.ok(declaration > 0 && declaration < memo);
  assert.match(source.slice(declaration, memo), /\}, \[refreshSession\]\);/);
  assert.doesNotMatch(source.slice(memo), /async authorizedFetch\(/);
  // refreshSession, su única dependencia, es estable (sólo depende de callbacks estables).
  assert.match(source, /\}, \[persist, persistOperationalSession\]\);\n\n  \/\/ Shared session-setup authority/);
});

test('work-orders: request (usado por LabTechnicalCapture y LabClientSelector) sólo depende de authorizedFetch', () => {
  assert.match(screens['work-orders'], /return response\.json\(\) as Promise<T>;\n  \}, \[authorizedFetch\]\);/);
});
