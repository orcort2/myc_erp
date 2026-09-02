import * as FileSystem from 'expo-file-system/legacy';
import * as Sharing from 'expo-sharing';
import { useEffect, useState } from 'react';
import { Alert, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import type {
  FieldSheetTemplate,
  LabEquipment,
  LabFieldSheet,
  LabWorkOrder,
} from '@/src/types/lab-work-order';
import { labelPrintService } from '@/src/services/label-print-service';
import { directFields, normalizeFieldSheetPayload } from '@/src/services/field-sheet-payload';
import { resolveDocumentaryClientLabel } from '@/src/services/lab-documentary-client';
import { resolveBlockFields, keyboardTypeForFieldType } from '@/src/services/field-sheet-contract';
import { computeOverallProgress } from '@/src/services/field-sheet-progress';
import { filterFieldSheetTemplates } from '@/src/services/field-sheet-template-selector';
import { PENDING_SIGNATURE_LABEL, resolveCalibradoPor } from '@/src/services/lab-signature-authority';
import {
  captureIsAlwaysReadOnly,
  initialViewMode,
  isFieldSheetEditable,
  viewModeAfterDraftSaved,
  viewModeAfterEditRequested,
  type FieldSheetViewMode,
} from '@/src/services/field-sheet-draft-view-state';
import { apiUrl, ApiError } from '@/src/api/client';
import {
  ActionRow, AdministrativeButton, AlertBanner, Card, EmptyState, FadeIn, Field, LoadingState, PrimaryButton, ReadOnlyField, SecondaryButton, Section, StatusBadge,
} from '@/src/design/primitives';
import { colors, spacing } from '@/src/design/tokens';
import { FieldSheetResultsWorkspace } from '@/src/components/field-sheets/FieldSheetResultsWorkspace';

type Request = <T>(path: string, init?: RequestInit) => Promise<T>;

type Props = {
  accessToken: string;
  canCapture: boolean;
  external: boolean;
  onUpdated(order: LabWorkOrder): void;
  request: Request;
  workOrder: LabWorkOrder;
};

// Firmas/autoridad documental: nunca capturados como texto libre (ver
// lab-signature-authority.ts). Se excluyen de los "campos ordinarios" y se
// muestran aparte, de sólo lectura, derivados del actor/evento real.
const SIGNATURE_AUTHORITY_KEYS = new Set(['calibrated_by', 'reviewed_by', 'report_made_by']);

const serviceLabels = { accredited: 'Acreditado', traceable: 'Trazable', linked: 'Vinculado' } as const;

// Campos calculados/congelados que el backend expone pero que FieldSheetUpdate no acepta
// (reserved_certificate_folio es un @property; work_order_number se fija al crear la hoja).
// Se muestran de solo lectura y nunca se envían de vuelta.
const readOnlyFields = new Set(['work_order_number', 'reserved_certificate_folio']);

// Fase 6: fallback LEGACY -- la autoridad principal es block.fields[] del
// snapshot (ver resolveBlockFields/field-sheet-contract.ts). Este mapa sólo
// cubre las claves que el catálogo legacy declara en visible_fields sin
// traer todavía una entrada rica en fields[].
const FIELD_LABELS: Record<string, string> = {
  work_order_number: 'No. de orden de trabajo',
  reserved_certificate_folio: 'Folio de certificado',
  attention: 'Atención a',
  company: 'Empresa',
  address: 'Dirección',
  instrument: 'Instrumento',
  scope: 'Alcance / capacidad',
  brand: 'Marca',
  model: 'Modelo',
  serial_number: 'No. de serie',
  internal_id: 'ID interno',
  location: 'Ubicación',
  minimum_division: 'División mínima',
  reception_date: 'Fecha de recepción',
  calibration_date: 'Fecha de calibración',
  next_calibration_date: 'Próxima calibración',
  calibration_place: 'Lugar de calibración',
  environment_humidity_start: 'Humedad inicial',
  environment_humidity_end: 'Humedad final',
  environment_temperature_start: 'Temperatura inicial',
  environment_temperature_end: 'Temperatura final',
  initial_condition: 'Condición inicial',
  final_condition: 'Condición final',
  method: 'Método',
  units: 'Unidades',
  observations: 'Observaciones',
  evidence_notes: 'Notas de evidencia',
  calibrated_by: 'Calibrado por',
  reviewed_by: 'Revisado por',
  report_made_by: 'Reporte elaborado por',
  purchase_order_or_quotation: 'Orden de compra / cotización',
};

function buildValues(entity: LabFieldSheet): Record<string, unknown> {
  const picked: Record<string, unknown> = {};
  for (const key of directFields) {
    if (key in entity) picked[key] = (entity as unknown as Record<string, unknown>)[key];
  }
  return { ...entity.capture_values, ...picked };
}

function statusTone(status: string): 'warning' | 'info' | 'success' {
  if (status === 'completed') return 'success';
  if (status === 'draft') return 'warning';
  return 'info';
}

// Cierre UX 2026-09 (item K): el status crudo de FieldSheet ("draft"/
// "completed") no debe llegar tal cual a un StatusBadge -- mismo criterio ya
// aplicado a LabWorkOrder vía statusPresentation.
const FIELD_SHEET_STATUS_LABELS: Record<string, string> = {
  draft: 'BORRADOR',
  in_progress: 'EN CAPTURA',
  completed: 'COMPLETADA',
};

function fieldSheetStatusLabel(status: string): string {
  return FIELD_SHEET_STATUS_LABELS[status] ?? status.toUpperCase();
}

/**
 * Fase 6: flujo principal de captura -- contexto OT/equipo, datos readonly,
 * campos ordinarios, Resultados (fuera del formulario, vía
 * FieldSheetResultsWorkspace), acciones guardar/completar. No crea una
 * pantalla distinta por instrumento: renderiza según block/section
 * genéricamente, igual que antes de esta fase, ahora con el contrato de
 * campo completo del snapshot y sin tablas inline.
 */
export function LabTechnicalCapture({ accessToken, canCapture, external, onUpdated, request, workOrder }: Props) {
  const [templates, setTemplates] = useState<FieldSheetTemplate[]>([]);
  const [templatesLoading, setTemplatesLoading] = useState(true);
  const [templatesError, setTemplatesError] = useState('');
  const [templateSearch, setTemplateSearch] = useState('');
  const [activeEquipment, setActiveEquipment] = useState<LabEquipment | null>(null);
  const [selectedTemplate, setSelectedTemplate] = useState('');
  const [sheet, setSheet] = useState<LabFieldSheet | null>(null);
  const [values, setValues] = useState<Record<string, unknown>>({});
  const [viewMode, setViewMode] = useState<FieldSheetViewMode>(initialViewMode());
  const [resultsOpen, setResultsOpen] = useState(false);
  const [ticketMode, setTicketMode] = useState<'manual_myc_folio' | 'linked_folio' | 'field_sheet_template' | 'field_sheet_reopen' | null>(null);
  const [requestedFolio, setRequestedFolio] = useState('');
  const [ticketReason, setTicketReason] = useState('');
  const [ticketDescription, setTicketDescription] = useState('');
  const [busy, setBusy] = useState(false);
  const [downloadingPdf, setDownloadingPdf] = useState(false);

  async function refreshWorkOrder() {
    const updated = await request<LabWorkOrder>(
      `/mobile/v1/technician/lab-work-orders/${workOrder.id}`,
    );
    onUpdated(updated);
    return updated;
  }

  useEffect(() => {
    setTemplatesLoading(true);
    setTemplatesError('');
    request<FieldSheetTemplate[]>('/mobile/v1/technician/lab-work-orders/field-sheet-templates')
      .then(setTemplates)
      .catch((error) => setTemplatesError(error instanceof Error ? error.message : 'No fue posible cargar las hojas de campo.'))
      .finally(() => setTemplatesLoading(false));
  }, [request]);

  const definition = sheet?.template_definition ?? templates.find((item) => item.template_key === selectedTemplate);
  const ordinaryFields = (definition?.blocks ?? [])
    .filter((block) => block.capture_visible !== false && !block.block_type.includes('Table'))
    .flatMap((block) => resolveBlockFields(block, { fallbackLabels: FIELD_LABELS, readOnlyKeys: readOnlyFields }))
    .filter((field) => !SIGNATURE_AUTHORITY_KEYS.has(field.key));
  const overallProgress = definition ? computeOverallProgress(definition.result_sections, sheet?.results_rows ?? []) : null;
  const editable = !!sheet && isFieldSheetEditable(sheet.status, viewMode);
  const visibleTemplates = filterFieldSheetTemplates(templates, templateSearch);

  async function openSheet(equipment: LabEquipment) {
    setActiveEquipment(equipment);
    setSelectedTemplate('');
    setTemplateSearch('');
    if (!equipment.field_sheet_id) {
      setSheet(null);
      setValues({});
      return;
    }
    setBusy(true);
    try {
      const loaded = await request<LabFieldSheet>(
        `/mobile/v1/technician/lab-work-orders/${workOrder.id}/equipment/${equipment.id}/field-sheet`,
      );
      setSheet(loaded);
      setSelectedTemplate(loaded.template_key);
      setValues(buildValues(loaded));
      // Reabrir una hoja ya existente entra en modo consulta -- "Editar"
      // vuelve a habilitar los inputs explícitamente (cierre UX 2026-09).
      setViewMode('view');
    } catch (error) {
      Alert.alert('No fue posible abrir la hoja', error instanceof Error ? error.message : 'Intenta nuevamente');
      setActiveEquipment(null);
    } finally { setBusy(false); }
  }

  async function createSheet() {
    if (!activeEquipment || !selectedTemplate) return;
    setBusy(true);
    try {
      const created = await request<LabFieldSheet>(
        `/mobile/v1/technician/lab-work-orders/${workOrder.id}/equipment/${activeEquipment.id}/field-sheet`,
        { method: 'POST', body: JSON.stringify({ template_key: selectedTemplate }) },
      );
      setSheet(created);
      setValues(buildValues(created));
      setViewMode(initialViewMode());
      await refreshWorkOrder();
    } catch (error) {
      Alert.alert('No fue posible crear la hoja', error instanceof Error ? error.message : 'Revisa el folio y la plantilla');
    } finally { setBusy(false); }
  }

  function setField(key: string, value: string) {
    setValues((current) => ({ ...current, [key]: value }));
  }

  // Fase 6: Resultados se guarda de forma independiente y explícita dentro
  // del workspace (nunca un PATCH por tecla desde el formulario principal).
  // saveSheet más abajo reenvía sheet.results_rows tal cual -- ya persistidos
  // aquí -- para no perderlos cuando el técnico use "Guardar borrador".
  async function saveResultsRows(rows: LabFieldSheet['results_rows']) {
    if (!activeEquipment) return;
    const saved = await request<LabFieldSheet>(
      `/mobile/v1/technician/lab-work-orders/${workOrder.id}/equipment/${activeEquipment.id}/field-sheet`,
      { method: 'PATCH', body: JSON.stringify({ results_rows: rows }) },
    );
    setSheet(saved);
  }

  async function saveSheet(complete = false) {
    if (!activeEquipment || !sheet) return;
    setBusy(true);
    let saved: LabFieldSheet;
    try {
      const { direct, captureValues } = normalizeFieldSheetPayload(values, sheet);
      saved = await request<LabFieldSheet>(
        `/mobile/v1/technician/lab-work-orders/${workOrder.id}/equipment/${activeEquipment.id}/field-sheet`,
        { method: 'PATCH', body: JSON.stringify({ ...direct, capture_values: captureValues, results_rows: sheet.results_rows }) },
      );
    } catch (error) {
      // A) payload inválido técnicamente en el PATCH (tipos, formato): no es
      // que la hoja esté incompleta, es que el dato en sí no es aceptable.
      Alert.alert('No fue posible guardar', error instanceof Error ? error.message : 'Revisa los campos requeridos');
      setBusy(false);
      return;
    }
    if (!complete) {
      setSheet(saved);
      setViewMode(viewModeAfterDraftSaved());
      Alert.alert('Hoja guardada', 'Los cambios quedaron en esta instancia; la plantilla no fue modificada.');
      setBusy(false);
      return;
    }
    try {
      await request<LabFieldSheet>(
        `/mobile/v1/technician/lab-work-orders/${workOrder.id}/equipment/${activeEquipment.id}/field-sheet/complete`,
        { method: 'POST' },
      );
      await refreshWorkOrder();
      setActiveEquipment(null);
      setSheet(null);
    } catch (error) {
      // B) el PATCH fue válido y quedó guardado como borrador; lo que falta
      // es completitud técnica para poder cerrar la hoja. Si el motor ya
      // conoce la lista de campos faltantes (FieldSheetUpdate/`missing_fields`),
      // se muestra tal cual en vez del mensaje genérico de error del servidor.
      setSheet(saved);
      if (error instanceof ApiError && error.missingFields && error.missingFields.length > 0) {
        const bullets = error.missingFields.map((field) => `• ${FIELD_LABELS[field] ?? field}`).join('\n');
        Alert.alert('No se puede completar la hoja', `Faltan:\n${bullets}`);
      } else {
        Alert.alert('No se puede completar la hoja', error instanceof Error ? error.message : 'Revisa los campos requeridos');
      }
    } finally { setBusy(false); }
  }

  async function requestFolio() {
    if (!activeEquipment || (ticketMode !== 'manual_myc_folio' && ticketMode !== 'linked_folio')) return;
    if (!ticketReason.trim() || !ticketDescription.trim()) return;
    setBusy(true);
    try {
      await request('/mobile/v1/technician/tickets/folio', {
        method: 'POST',
        body: JSON.stringify({
          work_order_id: workOrder.id,
          equipment_id: activeEquipment.id,
          type: ticketMode,
          requested_folio: ticketMode === 'manual_myc_folio' ? requestedFolio.trim() : null,
          reason: ticketReason.trim(),
          description: ticketDescription.trim(),
        }),
      });
      await refreshWorkOrder();
      setTicketMode(null);
      setActiveEquipment(null);
      Alert.alert('Solicitud enviada', 'Admin resolverá el folio mediante el Ticket y su conversación.');
    } catch (error) {
      Alert.alert('No fue posible solicitar el folio', error instanceof Error ? error.message : 'Intenta nuevamente');
    } finally { setBusy(false); }
  }

  // Fase 4: "No encuentro la hoja necesaria" nunca crea una plantilla ni una
  // FieldSheet desde Mobile -- únicamente deja constancia mediante el tipo de
  // Ticket ya existente (field_sheet_template_request, ver
  // backend/app/services/operational_tickets.py). El equipo y la OT ya
  // identifican instrumento/servicio/folio por FK; no se duplican aquí.
  async function requestFieldSheetTemplate() {
    if (!activeEquipment || ticketMode !== 'field_sheet_template') return;
    if (!ticketReason.trim() || !ticketDescription.trim()) return;
    setBusy(true);
    try {
      await request('/mobile/v1/technician/tickets/field-sheet-template', {
        method: 'POST',
        body: JSON.stringify({
          work_order_id: workOrder.id,
          equipment_id: activeEquipment.id,
          reason: ticketReason.trim(),
          description: ticketDescription.trim(),
        }),
      });
      setTicketMode(null);
      setActiveEquipment(null);
      Alert.alert('Solicitud enviada', 'Se registró el Ticket; no se creó ninguna hoja de campo mientras se resuelve.');
    } catch (error) {
      Alert.alert('No fue posible enviar la solicitud', error instanceof Error ? error.message : 'Intenta nuevamente');
    } finally { setBusy(false); }
  }

  // Cierre UX 2026-09: desbloqueo auditable de UNA hoja completed mientras la
  // OT sigue abierta (in_progress/ready_to_close) -- reutiliza el ticket
  // field_sheet_reopen ya existente (mismo OperationalTicket, sin segundo
  // sistema). Si la OT ya cerró, este componente ya no se muestra: esa
  // corrección usa la reapertura de OT completa en la pantalla de OT.
  async function requestFieldSheetReopen() {
    if (!activeEquipment || ticketMode !== 'field_sheet_reopen') return;
    if (!ticketReason.trim() || !ticketDescription.trim()) return;
    setBusy(true);
    try {
      await request('/mobile/v1/technician/tickets/field-sheet-reopen', {
        method: 'POST',
        body: JSON.stringify({
          work_order_id: workOrder.id,
          equipment_id: activeEquipment.id,
          reason: ticketReason.trim(),
          description: ticketDescription.trim(),
        }),
      });
      setTicketMode(null);
      setActiveEquipment(null);
      Alert.alert('Solicitud enviada', 'Un administrador debe autorizar el desbloqueo antes de recapturar.');
    } catch (error) {
      Alert.alert('No fue posible solicitar el desbloqueo', error instanceof Error ? error.message : 'Intenta nuevamente');
    } finally { setBusy(false); }
  }

  // Mismo PDF institucional que ya congela el backend (final_pdf) -- ningún
  // renderer nuevo, sólo exponerlo vía auth Mobile (mismo patrón que
  // downloadPdf en work-orders.tsx).
  async function downloadFieldSheetPdf() {
    if (!activeEquipment || !sheet) return;
    setDownloadingPdf(true);
    try {
      const uri = `${FileSystem.cacheDirectory}HOJA-${workOrder.folio}-${activeEquipment.position}.pdf`;
      const result = await FileSystem.downloadAsync(
        apiUrl(`/mobile/v1/technician/lab-work-orders/${workOrder.id}/equipment/${activeEquipment.id}/field-sheet/pdf`),
        uri,
        { headers: { Authorization: `Bearer ${accessToken}` } },
      );
      if (result.status !== 200) throw new Error(`No fue posible descargar el PDF (${result.status})`);
      if (await Sharing.isAvailableAsync()) {
        await Sharing.shareAsync(result.uri, { UTI: 'com.adobe.pdf', mimeType: 'application/pdf' });
      }
    } catch (error) {
      Alert.alert('No fue posible abrir el PDF', error instanceof Error ? error.message : 'Intenta nuevamente');
    } finally { setDownloadingPdf(false); }
  }

  if (activeEquipment) {
    if (ticketMode === 'field_sheet_template') return (
      <ScrollView contentContainerStyle={styles.panel}>
        <Text style={styles.title}>No encuentro la hoja necesaria</Text>
        <Text style={styles.meta}>{activeEquipment.instrument} · OT {workOrder.folio}</Text>
        <Field label="Motivo" onChange={setTicketReason} value={ticketReason} />
        <Field label="Descripción" multiline onChange={setTicketDescription} value={ticketDescription} />
        <ActionRow>
          <SecondaryButton label="Volver" onPress={() => setTicketMode(null)} />
          <PrimaryButton label="Enviar Ticket" loading={busy} onPress={requestFieldSheetTemplate} />
        </ActionRow>
      </ScrollView>
    );
    if (ticketMode === 'field_sheet_reopen') return (
      <ScrollView contentContainerStyle={styles.panel}>
        <Text style={styles.title}>Solicitar desbloqueo</Text>
        <Text style={styles.meta}>{activeEquipment.instrument} · OT {workOrder.folio} · Hoja {sheet ? fieldSheetStatusLabel(sheet.status).toLowerCase() : ''}</Text>
        <Field label="Motivo" onChange={setTicketReason} value={ticketReason} />
        <Field label="Descripción" multiline onChange={setTicketDescription} value={ticketDescription} />
        <ActionRow>
          <SecondaryButton label="Volver" onPress={() => setTicketMode(null)} />
          <PrimaryButton label="Enviar Ticket" loading={busy} onPress={requestFieldSheetReopen} />
        </ActionRow>
      </ScrollView>
    );
    if (ticketMode) return (
      <ScrollView contentContainerStyle={styles.panel}>
        <Text style={styles.title}>{ticketMode === 'linked_folio' ? 'Solicitar folio Vinculado' : 'Folio MYC manual'}</Text>
        {ticketMode === 'manual_myc_folio' && <Field label="Folio solicitado" onChange={setRequestedFolio} value={requestedFolio} />}
        <Field label="Motivo" onChange={setTicketReason} value={ticketReason} />
        <Field label="Descripción" multiline onChange={setTicketDescription} value={ticketDescription} />
        <ActionRow>
          <SecondaryButton label="Volver" onPress={() => setTicketMode(null)} />
          <PrimaryButton label="Enviar Ticket" loading={busy} onPress={requestFolio} />
        </ActionRow>
      </ScrollView>
    );
    // Fase 4: contexto administrativo de sólo lectura -- servicio, folio y
    // cliente documental ya quedaron congelados en recepción (draft) y no se
    // vuelven a pedir aquí; ver LabEquipmentForm/certificate-client.
    const modalityLabel = activeEquipment.service_type ? serviceLabels[activeEquipment.service_type] : 'Sin asignar';
    const folioLabel = activeEquipment.certificate_folio
      ?? (activeEquipment.folio_status === 'pending' ? 'FOLIO PENDIENTE' : 'FOLIO SIN RESOLVER');
    const documentaryClientLabel = resolveDocumentaryClientLabel(activeEquipment, workOrder);
    return (
      <ScrollView contentContainerStyle={styles.panel}>
        <FadeIn transitionKey={activeEquipment.id}>
        <Text style={styles.eyebrow}>OT {workOrder.folio} · EQUIPO {activeEquipment.position}</Text>
        <Text style={styles.title}>{activeEquipment.instrument}</Text>

        <Card>
          <ReadOnlyField label="Equipo" value={`${activeEquipment.brand} · ${activeEquipment.serial_number}`} />
          <ReadOnlyField label="Modalidad · Folio" value={`${modalityLabel} · ${folioLabel}`} />
          <ReadOnlyField label="Cliente documental" value={documentaryClientLabel} />
        </Card>

        {!sheet ? <>
          <Section title="Selecciona hoja de campo">
            <Field label="Buscar hoja de campo" onChange={setTemplateSearch} placeholder="Ej. presión, termómetro…" value={templateSearch} />
            {templatesLoading ? (
              <LoadingState label="Cargando hojas de campo…" />
            ) : templatesError ? (
              <AlertBanner tone="danger">{templatesError}</AlertBanner>
            ) : visibleTemplates.length > 0 ? (
              <ScrollView nestedScrollEnabled style={styles.templateList}>
                {visibleTemplates.map((template) => (
                  <Pressable
                    key={template.template_key}
                    onPress={() => setSelectedTemplate(template.template_key)}
                    style={({ pressed }) => [
                      styles.choice,
                      selectedTemplate === template.template_key && styles.choiceActive,
                      pressed && styles.choicePressed,
                    ]}
                  >
                    <Text>{template.name} · v{template.version}</Text>
                  </Pressable>
                ))}
              </ScrollView>
            ) : (
              <EmptyState title="Sin resultados" description={templateSearch.trim() ? 'Prueba con otro término o solicita la hoja.' : 'No hay hojas de campo disponibles.'} />
            )}
            {!templatesLoading && !templatesError && visibleTemplates.length === 0 && (
              <SecondaryButton label="+ Solicitar hoja de campo" onPress={() => setTicketMode('field_sheet_template')} />
            )}
          </Section>
          {activeEquipment.service_type === 'linked' && activeEquipment.folio_status === 'pending' && !external && (
            <SecondaryButton label="Ticket · Resolver folio Vinculado" onPress={() => setTicketMode('linked_folio')} />
          )}
          {activeEquipment.service_type !== 'linked' && activeEquipment.automatic_certificate_folio && (
            <SecondaryButton label="Ticket · Folio MYC manual" onPress={() => setTicketMode('manual_myc_folio')} />
          )}
          <ActionRow>
            <PrimaryButton disabled={!selectedTemplate || !canCapture} label="Abrir captura" loading={busy} onPress={createSheet} />
          </ActionRow>
        </> : <>
          <View style={styles.statusRow}>
            <StatusBadge label={fieldSheetStatusLabel(sheet.status)} tone={statusTone(sheet.status)} />
          </View>

          {ordinaryFields.length > 0 && (
            <Section title="Datos de la hoja">
              {ordinaryFields.map((field) => field.readOnly
                ? <ReadOnlyField key={field.key} label={field.label} value={String((sheet as unknown as Record<string, unknown>)[field.key] ?? '-')} />
                : !editable
                ? <ReadOnlyField key={field.key} label={field.label} value={String(values[field.key] ?? '-')} />
                : (
                  <Field
                    key={field.key}
                    keyboardType={keyboardTypeForFieldType(field.fieldType)}
                    label={field.label}
                    onChange={(value) => setField(field.key, value)}
                    placeholder={field.placeholder ?? undefined}
                    value={String(values[field.key] ?? '')}
                  />
                ))}
            </Section>
          )}

          <Section title="Firmas">
            <ReadOnlyField label="Calibró" value={resolveCalibradoPor(workOrder)} />
            <ReadOnlyField label="Revisó" value={PENDING_SIGNATURE_LABEL} />
            <ReadOnlyField label="Elaboró informe" value={PENDING_SIGNATURE_LABEL} />
          </Section>

          {definition && definition.result_sections.length > 0 && overallProgress && (
            <Section title="Resultados">
              <Card>
                {overallProgress.sections.map((section) => (
                  <View key={section.key} style={styles.progressRow}>
                    <Text style={styles.progressTitle}>{section.title}</Text>
                    <Text style={styles.progressCount}>{section.completed} / {section.totalRequired} completos</Text>
                    {section.missing > 0 && <Text style={styles.progressMissing}>{section.missing} pendiente{section.missing === 1 ? '' : 's'}</Text>}
                  </View>
                ))}
                <SecondaryButton label="Abrir resultados" onPress={() => setResultsOpen(true)} />
              </Card>
            </Section>
          )}

          {canCapture && !captureIsAlwaysReadOnly(sheet.status) && (
            editable ? (
              <ActionRow>
                <SecondaryButton label="Guardar borrador" loading={busy} onPress={() => saveSheet(false)} />
                <PrimaryButton label="Completar hoja" loading={busy} onPress={() => saveSheet(true)} />
              </ActionRow>
            ) : (
              <SecondaryButton label="Editar" onPress={() => setViewMode(viewModeAfterEditRequested())} />
            )
          )}

          {sheet.status === 'completed' && (
            <>
              <ActionRow>
                <SecondaryButton label="Ver / descargar PDF" loading={downloadingPdf} onPress={downloadFieldSheetPdf} />
              </ActionRow>
              {canCapture && !['completed', 'partially_closed'].includes(workOrder.status) && (
                <AdministrativeButton label="Solicitar desbloqueo" onPress={() => setTicketMode('field_sheet_reopen')} />
              )}
            </>
          )}

          <SecondaryButton
            disabled={!labelPrintService.available}
            label="Imprimir etiqueta 50×30 · Próxima fase"
            onPress={() => undefined}
          />

          {definition && (
            <FieldSheetResultsWorkspace
              onClose={() => setResultsOpen(false)}
              onSave={saveResultsRows}
              readOnly={!canCapture || !editable}
              rows={sheet.results_rows}
              sections={definition.result_sections}
              title={`${activeEquipment.instrument} · ${definition.name}`}
              visible={resultsOpen}
            />
          )}
        </>}
        <SecondaryButton label="Volver a equipos" onPress={() => { setActiveEquipment(null); setSheet(null); setTicketMode(null); setViewMode(initialViewMode()); }} />
        </FadeIn>
      </ScrollView>
    );
  }

  // Fase 4: Mesa Técnica ya no vuelve a pedir modalidad/folio/cliente
  // documental -- eso se definió en recepción (draft) y quedó congelado. Aquí
  // sólo se presenta como contexto de sólo lectura; la primera y única acción
  // es seleccionar/abrir la hoja de campo.
  if (workOrder.equipment.length === 0) {
    return <EmptyState description="Añade equipos en el paso anterior para comenzar la captura técnica." title="Sin equipos todavía" />;
  }
  return <View style={styles.list}>
    {workOrder.equipment.map((equipment) => (
      <Card key={equipment.id}>
        <View style={styles.cardHeader}>
          <View style={styles.flex}>
            <Text style={styles.cardTitle}>{equipment.position}. {equipment.instrument}</Text>
            <Text style={styles.meta}>{equipment.brand} · {equipment.serial_number}</Text>
          </View>
          <StatusBadge
            label={equipment.field_sheet_status === 'completed' ? 'COMPLETA' : equipment.field_sheet_status ? 'EN CAPTURA' : 'SIN HOJA'}
            tone={equipment.field_sheet_status === 'completed' ? 'success' : equipment.field_sheet_status ? 'info' : 'neutral'}
          />
        </View>
        <Text style={styles.meta}>{equipment.service_type ? serviceLabels[equipment.service_type] : 'Sin asignar'} · {equipment.certificate_folio ?? (equipment.folio_status === 'pending' ? 'PENDIENTE' : 'Sin resolver')}</Text>
        <ReadOnlyField label="Cliente documental" value={resolveDocumentaryClientLabel(equipment, workOrder)} />
        <PrimaryButton label={equipment.field_sheet_id ? 'Abrir hoja' : 'Seleccionar hoja'} onPress={() => openSheet(equipment)} />
      </Card>
    ))}
  </View>;
}

const styles = StyleSheet.create({
  list: { gap: spacing.md }, panel: { gap: spacing.sm, paddingBottom: spacing.xl },
  flex: { flex: 1 },
  cardHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start' },
  cardTitle: { color: colors.text, fontSize: 17, fontWeight: '800' }, meta: { color: colors.textSubtle },
  templateList: { borderColor: colors.border, borderRadius: 9, borderWidth: 1, maxHeight: 240, padding: spacing.xs },
  choice: { backgroundColor: colors.background, borderColor: colors.border, borderRadius: 9, borderWidth: 1, padding: spacing.md, marginBottom: spacing.xs },
  choiceActive: { backgroundColor: colors.primarySoft, borderColor: colors.accent },
  choicePressed: { backgroundColor: colors.background },
  eyebrow: { color: colors.accent, fontSize: 12, fontWeight: '800', letterSpacing: 1 },
  title: { color: colors.text, fontSize: 22, fontWeight: '800' },
  statusRow: { flexDirection: 'row', marginBottom: spacing.sm },
  progressRow: { marginBottom: spacing.sm },
  progressTitle: { color: colors.text, fontWeight: '700' },
  progressCount: { color: colors.textMuted, fontSize: 13 },
  progressMissing: { color: colors.warningStrong, fontSize: 12, fontWeight: '700' },
});
