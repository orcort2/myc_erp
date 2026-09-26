import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

const source = readFileSync(
  resolve(
    dirname(fileURLToPath(import.meta.url)),
    '../../app/(technician)/work-orders.tsx',
  ),
  'utf8',
);

test('el flujo técnico usa el canon de botones acordado', () => {
  assert.match(
    source,
    /<SecondaryButton icon="arrow-left" label="Volver a equipos" onPress=\{\(\) => setStep\('capture'\)\}/,
  );

  assert.match(
    source,
    /<PrimaryButton icon="arrow-right-circle" label="Continuar a cierre" onPress=\{\(\) => setStep\('review'\)\}/,
  );

  assert.match(
    source,
    /<SecondaryButton icon="download" label="Descargar paquete disponible"/,
  );
});

// Estas pruebas verifican cableado; no prueban geometría ni visibilidad nativa.
test('los cuatro formularios tienen una sola autoridad por plataforma y conservan taps', () => {
  const containers = [...source.matchAll(/<KeyboardAvoidingView([^>]+)>\s*<ScrollView([^>]+)>/g)];
  assert.equal(containers.length, 4);
  for (const [, kav, scroll] of containers) {
    assert.match(kav, /enabled=\{Platform\.OS === 'android'\}/);
    assert.match(kav, /behavior=\{Platform\.OS === 'android' \? 'height' : undefined\}/);
    assert.match(scroll, /automaticallyAdjustKeyboardInsets=\{Platform\.OS === 'ios'\}/);
    assert.match(scroll, /keyboardShouldPersistTaps="handled"/);
    assert.doesNotMatch(scroll, /scrollEnabled=\{false\}/);
  }
  assert.doesNotMatch(source, /behavior=.*'padding'/);
  assert.equal((source.match(/automaticallyAdjustKeyboardInsets=/g) ?? []).length, 4);
});

test('el formulario conserva scroll acotado y bloqueo exclusivo durante el trazo de firma', () => {
  assert.match(source, /scrollEnabled=\{!signatureDrawing\}/);
  assert.match(source, /contentContainerStyle=\{styles\.modalContent\}/);
  assert.equal((source.match(/contentContainerStyle=\{styles\.overlayContent\}/g) ?? []).length, 3);
  assert.match(source, /flex: \{\s*flex: 1/);
});

test('el ajuste no depende del modelo del dispositivo ni de offsets manuales', () => {
  assert.doesNotMatch(source, /iPhone|modelName|modelId|deviceName|keyboardVerticalOffset|Keyboard\.addListener/);
});

test('datos generales y equipo presentan fieldErrors estructurados junto al control', () => {
  assert.match(
    source,
    /setGeneralErrors\(Object\.fromEntries\(error\.fieldErrors/,
  );

  assert.match(
    source,
    /setEquipmentErrors\(Object\.fromEntries\(error\.fieldErrors/g,
  );

  assert.match(
    source,
    /<AlertBanner tone="danger">Revisa los campos marcados/,
  );

  assert.match(
    source,
    /fieldErrors=\{equipmentErrors\}/,
  );

  assert.match(
    source,
    /onFieldChange=\{clearEquipmentError\}/,
  );
});

test('anular ingreso de equipo usa el endpoint administrativo void y nunca el DELETE legacy', () => {
  assert.equal(
    source.includes(
      '/equipment/${equipmentEditor.id}?expected_edit_version=${workOrder.edit_version}',
    ),
    false,
    'el DELETE legacy de equipo no debe seguir presente',
  );

  assert.equal(
    source.includes('async function removeEquipment()'),
    false,
    'removeEquipment legacy no debe existir',
  );

  assert.match(
    source,
    /\/equipment\/\$\{voidingEquipment\.id\}\/void/,
  );

  assert.match(
    source,
    /method:\s*'POST'/,
  );

  assert.match(
    source,
    /reason,/,
  );

  assert.match(
    source,
    /expected_edit_version:\s*workOrder\.edit_version/,
  );
});

test('anular ingreso queda reservado a autoridad administrativa y exige confirmación explícita', () => {
  // PENDIENTE 5 (encargo de corrección LAB): ya no gatea con canCancel
  // (== hasPermission(lab_work_orders.cancel) sin actor interno) sino con
  // canVoidLabEquipmentEntry, la capability dedicada que además exige
  // actor_type === 'internal', igual que el backend
  // (post_void_lab_equipment_entry) y que canVoidLabDelivery.
  assert.match(
    source,
    /\{canVoidLabEquipmentEntry && \(\s*<OperationalActionStack>/,
  );

  assert.match(
    source,
    /function openVoidEquipmentDialog\(equipment: LabEquipment\) \{\s*if \(!canVoidLabEquipmentEntry\) return;/,
  );

  assert.match(
    source,
    /label="Anular ingreso del equipo"/,
  );

  assert.match(
    source,
    /setTicketDialogMode\('void_equipment'\)/,
  );

  assert.match(
    source,
    /ticketDialogMode === 'void_equipment' && canVoidLabEquipmentEntry/,
  );

  assert.match(
    source,
    /ticketReason\.trim\(\)\.length < 3/,
  );
});

test('el diálogo identifica el equipo que será anulado y conserva el lenguaje de trazabilidad', () => {
  assert.match(
    source,
    /Se anulará el ingreso del equipo/,
  );

  assert.match(
    source,
    /dejará de formar parte activa de esta recepción/,
  );

  assert.match(
    source,
    /registro histórico se conservará/,
  );
});

// PENDIENTE 2 (bug REVISION_CONFLICT productivo): reopen -> anular equipo ->
// agregar reemplazo respondía 409 porque saveConfiguredEquipment() llamaba a
// buildConfiguredEquipmentPayload() sin expected_edit_version. La OT
// reabierta SÍ exige la versión (_check_edit_version en backend); el alta
// debe leer siempre workOrder.edit_version fresco de la última respuesta, no
// un valor cacheado.
test('el alta de equipo (saveConfiguredEquipment) manda workOrder.edit_version para no producir REVISION_CONFLICT tras reabrir/anular', () => {
  assert.match(
    source,
    /buildConfiguredEquipmentPayload\(values\.equipment, values\.documentaryClient, values\.service, workOrder\.edit_version\)/,
  );
});

// Contratos estáticos de la cabecera; no validan geometría en dispositivo.
test('listado usa un input q, debounce de 400 ms y limpia búsqueda/estado', () => {
  const header = source.slice(source.indexOf('<View style={styles.filters}>'), source.indexOf('<View style={styles.screenActions}>'));
  assert.equal((header.match(/<TextInput/g) ?? []).length, 1);
  assert.match(header, /placeholder="Buscar OT o cliente"/);
  assert.match(header, /onChangeText=\{setSearchFilter\}/);
  assert.doesNotMatch(source, /folioFilter|clientFilter|debouncedFolio|debouncedClient|`folio=|`client=/);
  assert.match(source, /debouncedSearch \? `q=\$\{encodeURIComponent\(debouncedSearch\)\}`/);
  assert.match(source, /setTimeout\(\(\) => \{\s*setDebouncedSearch\(searchFilter\.trim\(\)\);\s*}, 400\)/);
  assert.match(source, /return \(\) => clearTimeout\(timer\)/);
  assert.match(source, /function clearFilters\(\) \{\s*setSearchFilter\(''\);\s*setDebouncedSearch\(''\);\s*setStatusFilter\('all'\)/);
  assert.match(header, /onPress=\{clearFilters\}/);
  assert.match(header, /onPress=\{\(\) => setStatusFilter\(value\)\}/);
  assert.match(source, /if \(user\) refresh\(true\);[\s\S]*?\[debouncedSearch, statusFilter, user\]/);
});

test('listado conserva offset, tamaño de página y append versus reset', () => {
  assert.match(source, /const offset = reset \? 0 : itemCount\.current/);
  assert.match(source, /`limit=\$\{PAGE_SIZE\}`/);
  assert.match(source, /`offset=\$\{offset\}`/);
  assert.match(source, /`status=\$\{statusFilter\}`/);
  assert.match(source, /const updated = reset \? next : \[\.\.\.current, \.\.\.next\]/);
  assert.match(source, /setHasMore\(next\.length === PAGE_SIZE\)/);
  assert.match(source, /onPress=\{\(\) => refresh\(false\)\}/);
});

test('generación conserva dos targets, permisos y handlers con composición horizontal local', () => {
  for (const [permission, label, handler] of [
    ['canCreateWorkOrders', 'Generar orden', 'startNew'],
    ['canCreateWorkOrderGroupsDirect', 'Generar grupo', 'startDirectGroup'],
  ]) {
    const start = source.indexOf(`{${permission} && (`);
    const block = source.slice(start, source.indexOf('</Pressable>', start));
    assert.match(block, /<Pressable/);
    assert.ok(block.includes(`accessibilityLabel="${label}"`));
    assert.ok(block.includes(`onPress={${handler}}`));
    assert.match(block, /accessibilityRole="button"/);
    assert.match(block, /styles.generateAction/);
    assert.ok(block.indexOf('<MaterialCommunityIcons') < block.indexOf('<Text'));
  }
  assert.match(source, /generateAction: \{\s*flex: 1,\s*flexDirection: 'row',\s*alignItems: 'center'/);
  assert.match(source, /minHeight: 52/);
  assert.match(source, /screenActions: \{\s*flexDirection: 'row'/);
});
