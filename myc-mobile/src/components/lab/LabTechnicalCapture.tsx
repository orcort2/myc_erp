import { useEffect, useMemo, useState } from 'react';
import { Alert, Pressable, StyleSheet, Text, TextInput, View } from 'react-native';

import type {
  FieldSheetResultRow,
  FieldSheetTemplate,
  LabEquipment,
  LabFieldSheet,
  LabWorkOrder,
  LinkedCompany,
} from '@/src/types/lab-work-order';
import { labelPrintService } from '@/src/services/label-print-service';

type Request = <T>(path: string, init?: RequestInit) => Promise<T>;

type Props = {
  canCapture: boolean;
  external: boolean;
  onUpdated(order: LabWorkOrder): void;
  request: Request;
  workOrder: LabWorkOrder;
};

const serviceLabels = { accredited: 'Acreditado', traceable: 'Trazable', linked: 'Vinculado' } as const;
const directFields = new Set([
  'initial_condition', 'final_condition', 'observations', 'evidence_notes', 'minimum_division',
  'location', 'calibration_place', 'environment_humidity_start', 'environment_humidity_end',
  'environment_temperature_start', 'environment_temperature_end', 'units', 'method',
  'environmental_conditions', 'technician_notes', 'results', 'pattern_used',
]);

export function LabTechnicalCapture({ canCapture, external, onUpdated, request, workOrder }: Props) {
  const [templates, setTemplates] = useState<FieldSheetTemplate[]>([]);
  const [linkedCompanies, setLinkedCompanies] = useState<LinkedCompany[]>([]);
  const [activeEquipment, setActiveEquipment] = useState<LabEquipment | null>(null);
  const [selectedTemplate, setSelectedTemplate] = useState('');
  const [sheet, setSheet] = useState<LabFieldSheet | null>(null);
  const [values, setValues] = useState<Record<string, unknown>>({});
  const [rows, setRows] = useState<FieldSheetResultRow[]>([]);
  const [ticketMode, setTicketMode] = useState<'manual_myc_folio' | 'linked_folio' | null>(null);
  const [requestedFolio, setRequestedFolio] = useState('');
  const [ticketReason, setTicketReason] = useState('');
  const [ticketDescription, setTicketDescription] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    request<FieldSheetTemplate[]>('/mobile/v1/technician/lab-work-orders/field-sheet-templates')
      .then(setTemplates)
      .catch(() => setTemplates([]));
    request<LinkedCompany[]>('/mobile/v1/technician/lab-work-orders/linked-companies')
      .then(setLinkedCompanies)
      .catch(() => setLinkedCompanies([]));
  }, [request]);

  const definition = sheet?.template_definition ?? templates.find((item) => item.template_key === selectedTemplate);
  const visibleFields = useMemo(() => (definition?.blocks ?? [])
    .filter((block) => block.capture_visible !== false && !block.block_type.includes('Table'))
    .flatMap((block) => (block.fields ?? []).filter((field) => field.visible !== false)
      .map((field) => ({ ...field, blockTitle: block.title }))), [definition]);

  async function assignService(equipment: LabEquipment, serviceType: keyof typeof serviceLabels, linkedCompanyId?: number) {
    setBusy(true);
    try {
      const updated = await request<LabWorkOrder>(
        `/mobile/v1/technician/lab-work-orders/${workOrder.id}/equipment/${equipment.id}/service`,
        { method: 'PUT', body: JSON.stringify({ service_type: serviceType, linked_company_id: linkedCompanyId ?? null }) },
      );
      onUpdated(updated);
    } catch (error) {
      Alert.alert('No fue posible asignar el servicio', error instanceof Error ? error.message : 'Intenta nuevamente');
    } finally { setBusy(false); }
  }

  async function openSheet(equipment: LabEquipment) {
    setActiveEquipment(equipment);
    setSelectedTemplate('');
    if (!equipment.field_sheet_id) {
      setSheet(null);
      setValues({});
      setRows([]);
      return;
    }
    setBusy(true);
    try {
      const loaded = await request<LabFieldSheet>(
        `/mobile/v1/technician/lab-work-orders/${workOrder.id}/equipment/${equipment.id}/field-sheet`,
      );
      setSheet(loaded);
      setSelectedTemplate(loaded.template_key);
      setValues({ ...loaded.capture_values, ...loaded });
      setRows(loaded.results_rows.map((row) => ({ ...row, row_data: { ...(row.row_data ?? {}) } })));
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
      setValues({ ...created.capture_values, ...created });
      setRows(created.results_rows.map((row) => ({ ...row, row_data: { ...(row.row_data ?? {}) } })));
    } catch (error) {
      Alert.alert('No fue posible crear la hoja', error instanceof Error ? error.message : 'Revisa el folio y la plantilla');
    } finally { setBusy(false); }
  }

  function setField(key: string, value: string) {
    setValues((current) => ({ ...current, [key]: value }));
  }

  function setRowValue(index: number, key: string, value: string) {
    setRows((current) => current.map((row, rowIndex) => rowIndex === index
      ? { ...row, row_data: { ...row.row_data, [key]: value } }
      : row));
  }

  function addRow(sectionKey: string) {
    const section = definition?.result_sections.find((item) => item.key === sectionKey);
    if (!section?.allow_add_rows) return;
    const sectionRows = rows.filter((row) => row.section_key === sectionKey);
    if (section.max_rows && sectionRows.length >= section.max_rows) return;
    setRows((current) => [...current, {
      section_key: sectionKey,
      row_number: sectionRows.length + 1,
      row_data: {},
    }]);
  }

  async function saveSheet(complete = false) {
    if (!activeEquipment || !sheet) return;
    setBusy(true);
    try {
      const captureValues = Object.fromEntries(Object.entries(values).filter(([key]) => !directFields.has(key)));
      const direct = Object.fromEntries(Object.entries(values).filter(([key]) => directFields.has(key)));
      const saved = await request<LabFieldSheet>(
        `/mobile/v1/technician/lab-work-orders/${workOrder.id}/equipment/${activeEquipment.id}/field-sheet`,
        { method: 'PATCH', body: JSON.stringify({ ...direct, capture_values: captureValues, results_rows: rows }) },
      );
      if (complete) {
        await request<LabFieldSheet>(
          `/mobile/v1/technician/lab-work-orders/${workOrder.id}/equipment/${activeEquipment.id}/field-sheet/complete`,
          { method: 'POST' },
        );
        const updated = await request<LabWorkOrder>(`/mobile/v1/technician/lab-work-orders/${workOrder.id}`);
        onUpdated(updated);
        setActiveEquipment(null);
        setSheet(null);
      } else {
        setSheet(saved);
        Alert.alert('Hoja guardada', 'Los cambios quedaron en esta instancia; la plantilla no fue modificada.');
      }
    } catch (error) {
      Alert.alert(complete ? 'No fue posible completar la hoja' : 'No fue posible guardar', error instanceof Error ? error.message : 'Revisa los campos requeridos');
    } finally { setBusy(false); }
  }

  async function requestFolio() {
    if (!activeEquipment || !ticketMode || !ticketReason.trim() || !ticketDescription.trim()) return;
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
      const updated = await request<LabWorkOrder>(`/mobile/v1/technician/lab-work-orders/${workOrder.id}`);
      onUpdated(updated);
      setTicketMode(null);
      setActiveEquipment(null);
      Alert.alert('Solicitud enviada', 'Admin resolverá el folio mediante el Ticket y su conversación.');
    } catch (error) {
      Alert.alert('No fue posible solicitar el folio', error instanceof Error ? error.message : 'Intenta nuevamente');
    } finally { setBusy(false); }
  }

  if (activeEquipment) {
    if (ticketMode) return (
      <View style={styles.panel}>
        <Text style={styles.title}>{ticketMode === 'linked_folio' ? 'Solicitar folio Vinculado' : 'Folio MYC manual'}</Text>
        {ticketMode === 'manual_myc_folio' && <Input label="Folio solicitado" value={requestedFolio} onChange={setRequestedFolio} />}
        <Input label="Motivo" value={ticketReason} onChange={setTicketReason} />
        <Input label="Descripción" value={ticketDescription} onChange={setTicketDescription} multiline />
        <Pressable disabled={busy} style={styles.primary} onPress={requestFolio}><Text style={styles.primaryText}>Enviar Ticket</Text></Pressable>
        <Pressable style={styles.secondary} onPress={() => setTicketMode(null)}><Text style={styles.secondaryText}>Volver</Text></Pressable>
      </View>
    );
    return (
      <View style={styles.panel}>
        <Text style={styles.eyebrow}>EQUIPO {activeEquipment.position}</Text>
        <Text style={styles.title}>{activeEquipment.instrument}</Text>
        {!sheet ? <>
          <Text style={styles.label}>Selecciona hoja de campo</Text>
          {templates.map((template) => (
            <Pressable key={template.template_key} onPress={() => setSelectedTemplate(template.template_key)} style={[styles.choice, selectedTemplate === template.template_key && styles.choiceActive]}>
              <Text>{template.name} · v{template.version}</Text>
            </Pressable>
          ))}
          {activeEquipment.service_type === 'linked' && activeEquipment.folio_status === 'pending' && !external && (
            <Pressable style={styles.secondary} onPress={() => setTicketMode('linked_folio')}><Text style={styles.secondaryText}>Ticket · Resolver folio Vinculado</Text></Pressable>
          )}
          {activeEquipment.service_type !== 'linked' && activeEquipment.automatic_certificate_folio && (
            <Pressable style={styles.secondary} onPress={() => setTicketMode('manual_myc_folio')}><Text style={styles.secondaryText}>Ticket · Folio MYC manual</Text></Pressable>
          )}
          <Pressable disabled={!selectedTemplate || busy || !canCapture} style={[styles.primary, (!selectedTemplate || !canCapture) && styles.disabled]} onPress={createSheet}><Text style={styles.primaryText}>Abrir captura</Text></Pressable>
        </> : <>
          <Text style={styles.status}>Estado: {sheet.status}</Text>
          {visibleFields.map((field) => <Input key={field.key} label={`${field.label}${field.required ? ' *' : ''}`} value={String(values[field.key] ?? '')} onChange={(value) => setField(field.key, value)} />)}
          {(definition?.result_sections ?? []).map((section) => <View key={section.key} style={styles.table}>
            <Text style={styles.tableTitle}>{section.title}</Text>
            {rows.map((row, rowIndex) => row.section_key === section.key ? <View key={`${section.key}-${row.row_number}`} style={styles.tableRow}>
              <Text style={styles.rowNumber}>{row.row_number}</Text>
              {section.columns.filter((column) => column.editable !== false).map((column) => <TextInput key={column.key} placeholder={column.label} style={styles.tableInput} value={String(row.row_data[column.source ?? column.key] ?? '')} onChangeText={(value) => setRowValue(rowIndex, column.source ?? column.key, value)} />)}
            </View> : null)}
            {section.allow_add_rows && <Pressable style={styles.addRow} onPress={() => addRow(section.key)}><Text style={styles.addRowText}>＋</Text></Pressable>}
          </View>)}
          {canCapture && sheet.status !== 'completed' && <>
            <Pressable disabled={busy} style={styles.secondary} onPress={() => saveSheet(false)}><Text style={styles.secondaryText}>Guardar borrador</Text></Pressable>
            <Pressable disabled={busy} style={styles.primary} onPress={() => saveSheet(true)}><Text style={styles.primaryText}>Completar hoja</Text></Pressable>
          </>}
          <Pressable disabled={!labelPrintService.available} style={[styles.secondary, !labelPrintService.available && styles.disabled]}><Text style={styles.secondaryText}>Imprimir etiqueta 50×30 · Próxima fase</Text></Pressable>
        </>}
        <Pressable style={styles.back} onPress={() => { setActiveEquipment(null); setSheet(null); setTicketMode(null); }}><Text style={styles.secondaryText}>Volver a equipos</Text></Pressable>
      </View>
    );
  }

  return <View style={styles.list}>
    {workOrder.equipment.map((equipment) => <View key={equipment.id} style={styles.card}>
      <View><Text style={styles.cardTitle}>{equipment.position}. {equipment.instrument}</Text><Text style={styles.meta}>{equipment.brand} · {equipment.serial_number}</Text></View>
      <Text style={styles.status}>{equipment.field_sheet_status === 'completed' ? 'HOJA COMPLETA' : equipment.field_sheet_status ? 'HOJA EN CAPTURA' : 'SIN HOJA'}</Text>
      <Text style={styles.meta}>Servicio: {equipment.service_type ? serviceLabels[equipment.service_type] : 'Sin asignar'}</Text>
      <Text style={styles.meta}>Folio: {equipment.certificate_folio ?? (equipment.folio_status === 'pending' ? 'PENDIENTE' : 'Sin resolver')}</Text>
      {canCapture && !equipment.field_sheet_id && <View style={styles.services}>
        {(['accredited', 'traceable'] as const).map((type) => <Pressable key={type} style={styles.choice} onPress={() => assignService(equipment, type)}><Text>{serviceLabels[type]}</Text></Pressable>)}
        <Text style={styles.label}>Vinculado · selecciona procedencia</Text>
        {linkedCompanies.map((company) => <Pressable key={company.id} style={styles.choice} onPress={() => assignService(equipment, 'linked', company.id)}><Text>{company.name}</Text></Pressable>)}
      </View>}
      {(equipment.service_type || equipment.field_sheet_id) && <Pressable style={styles.primary} onPress={() => openSheet(equipment)}><Text style={styles.primaryText}>{equipment.field_sheet_id ? 'Abrir hoja' : 'Seleccionar hoja / resolver folio'}</Text></Pressable>}
    </View>)}
  </View>;
}

function Input({ label, value, onChange, multiline }: { label: string; value: string; onChange(value: string): void; multiline?: boolean }) {
  return <View style={styles.inputGroup}><Text style={styles.label}>{label}</Text><TextInput multiline={multiline} onChangeText={onChange} style={[styles.input, multiline && styles.multiline]} value={value} /></View>;
}

const styles = StyleSheet.create({
  list: { gap: 12 }, panel: { gap: 10 }, card: { backgroundColor: '#fff', borderColor: '#dbe4ea', borderRadius: 14, borderWidth: 1, gap: 8, padding: 14 },
  cardTitle: { color: '#142b3a', fontSize: 17, fontWeight: '800' }, meta: { color: '#637280' }, status: { color: '#008f87', fontSize: 12, fontWeight: '800' },
  services: { gap: 7, marginTop: 4 }, choice: { backgroundColor: '#f5f8fa', borderColor: '#cbd7df', borderRadius: 9, borderWidth: 1, padding: 10 }, choiceActive: { backgroundColor: '#dff3f1', borderColor: '#008f87' },
  primary: { alignItems: 'center', backgroundColor: '#0067a8', borderRadius: 10, marginTop: 6, padding: 13 }, primaryText: { color: '#fff', fontWeight: '800' },
  secondary: { alignItems: 'center', borderColor: '#0067a8', borderRadius: 10, borderWidth: 1, marginTop: 6, padding: 12 }, secondaryText: { color: '#0067a8', fontWeight: '800' }, disabled: { opacity: 0.42 }, back: { alignItems: 'center', padding: 12 },
  eyebrow: { color: '#008f87', fontSize: 12, fontWeight: '800', letterSpacing: 1 }, title: { color: '#142b3a', fontSize: 22, fontWeight: '800' }, label: { color: '#344553', fontSize: 12, fontWeight: '700' },
  inputGroup: { gap: 4 }, input: { backgroundColor: '#fff', borderColor: '#b9c8d2', borderRadius: 9, borderWidth: 1, minHeight: 44, paddingHorizontal: 11 }, multiline: { minHeight: 90, paddingTop: 10, textAlignVertical: 'top' },
  table: { borderColor: '#dbe4ea', borderRadius: 10, borderWidth: 1, gap: 7, padding: 9 }, tableTitle: { color: '#142b3a', fontWeight: '800' }, tableRow: { alignItems: 'center', flexDirection: 'row', gap: 5 }, rowNumber: { width: 22 }, tableInput: { borderColor: '#cbd7df', borderRadius: 6, borderWidth: 1, flex: 1, minWidth: 70, padding: 7 }, addRow: { alignItems: 'center', borderColor: '#008f87', borderRadius: 8, borderStyle: 'dashed', borderWidth: 1, padding: 7 }, addRowText: { color: '#008f87', fontSize: 20, fontWeight: '800' },
});
