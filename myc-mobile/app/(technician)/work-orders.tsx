import * as FileSystem from 'expo-file-system/legacy';
import * as Print from 'expo-print';
import * as Sharing from 'expo-sharing';
import { Redirect, router } from 'expo-router';
import { useCallback, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import {
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Modal,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { SafeAreaProvider, SafeAreaView } from 'react-native-safe-area-context';

import { apiUrl, readApiError } from '@/src/api/client';
import { useAuth } from '@/src/auth/AuthProvider';
import { SignaturePad } from '@/src/components/SignaturePad';
import type {
  EquipmentData,
  GeneralData,
  LabEquipment,
  LabListItem,
  LabWorkOrder,
} from '@/src/types/lab-work-order';

const today = () => new Date().toISOString().slice(0, 10);
const emptyGeneral = (): GeneralData => ({
  reception_date: today(),
  departure_date: today(),
  client_name: '',
  address: '',
  contact_name: '',
  contact_phone: '',
  contact_email: '',
  postal_code: '',
  city: '',
  state_name: '',
  purchase_order: '',
  notes: '',
});
const emptyEquipment = (): EquipmentData => ({
  instrument: '',
  brand: '',
  identification: '',
  serial_number: '',
  report_number: null,
  is_good_condition: true,
});

type Step = 'general' | 'capture' | 'review' | 'signatures' | 'completed';

function Field({
  label,
  value,
  onChangeText,
  required,
  multiline,
  keyboardType,
}: {
  label: string;
  value: string;
  onChangeText(value: string): void;
  required?: boolean;
  multiline?: boolean;
  keyboardType?: 'default' | 'email-address' | 'phone-pad';
}) {
  return (
    <View style={styles.field}>
      <Text style={styles.fieldLabel}>{label}{required ? ' *' : ''}</Text>
      <TextInput
        keyboardType={keyboardType}
        multiline={multiline}
        onChangeText={onChangeText}
        style={[styles.input, multiline && styles.multiline]}
        value={value}
      />
    </View>
  );
}

function FormSection({
  children,
  title,
}: {
  children: ReactNode;
  title: string;
}) {
  return (
    <View style={styles.formSection}>
      <Text style={styles.formSectionTitle}>{title}</Text>
      {children}
    </View>
  );
}

export default function WorkOrdersScreen() {
  const { authorizedFetch, isLoading: authLoading, session, user } = useAuth();
  const [items, setItems] = useState<LabListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [open, setOpen] = useState(false);
  const [step, setStep] = useState<Step>('general');
  const [general, setGeneral] = useState<GeneralData>(emptyGeneral);
  const [workOrder, setWorkOrder] = useState<LabWorkOrder | null>(null);
  const [equipmentEditor, setEquipmentEditor] = useState<LabEquipment | 'new' | null>(null);
  const [equipment, setEquipment] = useState<EquipmentData>(emptyEquipment);
  const [technicianName, setTechnicianName] = useState('');
  const [clientName, setClientName] = useState('');
  const [technicianSignature, setTechnicianSignature] = useState('');
  const [clientSignature, setClientSignature] = useState('');

  const request = useCallback(async <T,>(path: string, init?: RequestInit): Promise<T> => {
    const headers = new Headers(init?.headers);
    if (init?.body) headers.set('Content-Type', 'application/json');
    const response = await authorizedFetch(apiUrl(path), { ...init, headers });
    if (!response.ok) throw new Error(await readApiError(response));
    return response.json() as Promise<T>;
  }, [authorizedFetch]);

  const refresh = useCallback(async () => {
    try {
      setItems(await request<LabListItem[]>('/mobile/v1/technician/lab-work-orders'));
    } catch (error) {
      Alert.alert('No fue posible cargar las OT', error instanceof Error ? error.message : 'Intenta nuevamente');
    } finally {
      setLoading(false);
    }
  }, [request]);

  useEffect(() => {
    if (user) refresh();
  }, [refresh, user]);

  const editable = workOrder?.status === 'draft';
  const canSaveEquipment = useMemo(
    () => equipment.instrument.trim() && equipment.brand.trim() && equipment.identification.trim() && equipment.serial_number.trim(),
    [equipment],
  );

  function startNew() {
    setGeneral(emptyGeneral());
    setWorkOrder(null);
    setStep('general');
    setTechnicianName(user?.full_name ?? '');
    setClientName('');
    setTechnicianSignature('');
    setClientSignature('');
    setOpen(true);
  }

  async function openExisting(id: number) {
    setBusy(true);
    try {
      const detail = await request<LabWorkOrder>(`/mobile/v1/technician/lab-work-orders/${id}`);
      setWorkOrder(detail);
      setGeneral({
        reception_date: detail.reception_date,
        departure_date: detail.departure_date,
        client_name: detail.client_name,
        address: detail.address,
        contact_name: detail.contact_name ?? '',
        contact_phone: detail.contact_phone ?? '',
        contact_email: detail.contact_email ?? '',
        postal_code: detail.postal_code ?? '',
        city: detail.city ?? '',
        state_name: detail.state_name ?? '',
        purchase_order: detail.purchase_order ?? '',
        notes: detail.notes ?? '',
      });
      setTechnicianName(user?.full_name ?? '');
      setClientName(detail.contact_name ?? '');
      setStep(detail.status === 'completed' ? 'completed' : detail.status === 'ready_for_signatures' ? 'signatures' : 'capture');
      setOpen(true);
    } catch (error) {
      Alert.alert('No fue posible abrir la OT', error instanceof Error ? error.message : 'Intenta nuevamente');
    } finally {
      setBusy(false);
    }
  }

  async function createWorkOrder() {
    if (!general.client_name.trim()) return;
    setBusy(true);
    try {
      const detail = await request<LabWorkOrder>('/mobile/v1/technician/lab-work-orders', {
        method: 'POST',
        body: JSON.stringify({
          ...general,
          contact_name: general.contact_name || null,
          contact_phone: general.contact_phone || null,
          contact_email: general.contact_email || null,
          postal_code: general.postal_code || null,
          city: general.city || null,
          state_name: general.state_name || null,
          purchase_order: general.purchase_order || null,
          notes: general.notes || null,
        }),
      });
      setWorkOrder(detail);
      setClientName(detail.contact_name ?? '');
      setStep('capture');
    } catch (error) {
      Alert.alert('No fue posible crear la OT', error instanceof Error ? error.message : 'Revisa los datos');
    } finally {
      setBusy(false);
    }
  }

  async function selectRelated(id: number) {
    setBusy(true);
    try {
      setWorkOrder(await request<LabWorkOrder>(`/mobile/v1/technician/lab-work-orders/${id}`));
    } catch (error) {
      Alert.alert('No fue posible cambiar de OT', error instanceof Error ? error.message : 'Intenta nuevamente');
    } finally {
      setBusy(false);
    }
  }

  function showEquipmentEditor(item: LabEquipment | 'new') {
    setEquipmentEditor(item);
    setEquipment(item === 'new' ? emptyEquipment() : {
      instrument: item.instrument,
      brand: item.brand,
      identification: item.identification,
      serial_number: item.serial_number,
      report_number: item.report_number,
      is_good_condition: item.is_good_condition,
    });
  }

  async function saveEquipment() {
    if (!workOrder || !equipmentEditor || !canSaveEquipment) return;
    setBusy(true);
    const path = equipmentEditor === 'new'
      ? `/mobile/v1/technician/lab-work-orders/${workOrder.id}/equipment`
      : `/mobile/v1/technician/lab-work-orders/${workOrder.id}/equipment/${equipmentEditor.id}`;
    try {
      const detail = await request<LabWorkOrder>(path, {
        method: equipmentEditor === 'new' ? 'POST' : 'PATCH',
        body: JSON.stringify(equipment),
      });
      setWorkOrder(detail);
      setEquipmentEditor(null);
    } catch (error) {
      Alert.alert('No fue posible guardar el equipo', error instanceof Error ? error.message : 'Revisa los datos');
    } finally {
      setBusy(false);
    }
  }

  async function removeEquipment() {
    if (!workOrder || !equipmentEditor || equipmentEditor === 'new') return;
    setBusy(true);
    try {
      const detail = await request<LabWorkOrder>(
        `/mobile/v1/technician/lab-work-orders/${workOrder.id}/equipment/${equipmentEditor.id}`,
        { method: 'DELETE' },
      );
      setWorkOrder(detail);
      setEquipmentEditor(null);
    } catch (error) {
      Alert.alert('No fue posible eliminar el equipo', error instanceof Error ? error.message : 'Intenta nuevamente');
    } finally {
      setBusy(false);
    }
  }

  async function addAdditional() {
    if (!workOrder) return;
    setBusy(true);
    try {
      setWorkOrder(await request<LabWorkOrder>(
        `/mobile/v1/technician/lab-work-orders/${workOrder.id}/additional`,
        { method: 'POST' },
      ));
    } catch (error) {
      Alert.alert('No fue posible asignar la OT extra', error instanceof Error ? error.message : 'Intenta nuevamente');
    } finally {
      setBusy(false);
    }
  }

  async function applySignatures() {
    if (!workOrder || !technicianName.trim() || !clientName.trim() || !technicianSignature || !clientSignature) return;
    setBusy(true);
    const signedAt = new Date().toISOString();
    try {
      setWorkOrder(await request<LabWorkOrder>(
        `/mobile/v1/technician/lab-work-orders/${workOrder.id}/signatures`,
        {
          method: 'POST',
          body: JSON.stringify({
            technician: { signer_name: technicianName, signed_at: signedAt, version: 1, signature_data_url: technicianSignature },
            client: { signer_name: clientName, signed_at: signedAt, version: 1, signature_data_url: clientSignature },
          }),
        },
      ));
    } catch (error) {
      Alert.alert('No fue posible aplicar las firmas', error instanceof Error ? error.message : 'Intenta nuevamente');
    } finally {
      setBusy(false);
    }
  }

  async function completeGroup() {
    if (!workOrder) return;
    setBusy(true);
    try {
      setWorkOrder(await request<LabWorkOrder>(
        `/mobile/v1/technician/lab-work-orders/${workOrder.id}/complete`,
        { method: 'POST' },
      ));
      setStep('completed');
      await refresh();
    } catch (error) {
      Alert.alert('No fue posible finalizar el grupo', error instanceof Error ? error.message : 'Intenta nuevamente');
    } finally {
      setBusy(false);
    }
  }

  async function downloadPdf(action: 'print' | 'share') {
    if (!workOrder || !session) return;
    setBusy(true);
    try {
      const uri = `${FileSystem.cacheDirectory}OT-${workOrder.folio}.pdf`;
      const result = await FileSystem.downloadAsync(
        apiUrl(`/mobile/v1/technician/lab-work-orders/${workOrder.id}/pdf`),
        uri,
        { headers: { Authorization: `Bearer ${session.access_token}` } },
      );
      if (result.status !== 200) throw new Error(`No fue posible descargar el PDF (${result.status})`);
      if (action === 'print') await Print.printAsync({ uri: result.uri });
      else if (await Sharing.isAvailableAsync()) await Sharing.shareAsync(result.uri, { UTI: 'com.adobe.pdf', mimeType: 'application/pdf' });
    } catch (error) {
      Alert.alert('No fue posible abrir el PDF', error instanceof Error ? error.message : 'Intenta nuevamente');
    } finally {
      setBusy(false);
    }
  }

  function closeFlow() {
    setOpen(false);
    setEquipmentEditor(null);
    refresh();
  }

  if (authLoading) return <View style={styles.center}><ActivityIndicator /></View>;
  if (!user) return <Redirect href="/(auth)/login" />;

  return (
    <SafeAreaView edges={['top', 'right', 'bottom', 'left']} style={styles.screen}>
      <View style={styles.header}>
        <Pressable onPress={() => router.back()}><Text style={styles.back}>‹ Inicio</Text></Pressable>
        <Text style={styles.title}>Órdenes de Trabajo</Text>
        <Text style={styles.subtitle}>LAB temporal · folios 6400–6999</Text>
      </View>
      <Pressable style={[styles.primary, styles.screenPrimary]} onPress={startNew}><Text style={styles.primaryText}>+ Generar orden</Text></Pressable>
      {loading ? <ActivityIndicator style={styles.loader} /> : (
        <ScrollView contentContainerStyle={styles.list}>
          {items.map((item) => (
            <Pressable key={item.id} style={styles.card} onPress={() => openExisting(item.id)}>
              <View><Text style={styles.folio}>OT {item.folio}</Text><Text style={styles.client}>{item.client_name}</Text></View>
              <View style={styles.cardRight}><Text style={styles.count}>{item.equipment_count}/10</Text><Text style={styles.status}>{item.status}</Text></View>
            </Pressable>
          ))}
          {!items.length && <Text style={styles.empty}>Aún no hay órdenes LAB.</Text>}
        </ScrollView>
      )}

      <Modal animationType="slide" onRequestClose={closeFlow} visible={open}>
        <SafeAreaProvider>
        <SafeAreaView edges={['top', 'right', 'bottom', 'left']} style={styles.modalScreen}>
          <View style={styles.modalHeader}>
            <View><Text style={styles.modalTitle}>OT LAB {workOrder ? `· ${workOrder.folio}` : ''}</Text><Text style={styles.modalHint}>Firma única para todo el grupo</Text></View>
            <Pressable onPress={closeFlow}><Text style={styles.close}>Cerrar</Text></Pressable>
          </View>
          {busy && <View style={styles.busy}><ActivityIndicator color="#fff" /><Text style={styles.busyText}>Guardando…</Text></View>}
          <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={styles.flex}>
            <ScrollView contentContainerStyle={styles.modalContent} keyboardShouldPersistTaps="handled">
              {step === 'general' && (
                <>
                  <View style={styles.sectionIntro}>
                    <Text style={styles.sectionEyebrow}>NUEVA ORDEN</Text>
                    <Text style={styles.sectionTitle}>Datos generales</Text>
                    <Text style={styles.sectionDescription}>Captura esta información una sola vez. Las OT adicionales la heredarán automáticamente.</Text>
                  </View>
                  <FormSection title="Servicio y cliente">
                    <Field label="Fecha de recepción (AAAA-MM-DD)" required value={general.reception_date} onChangeText={(value) => setGeneral({ ...general, reception_date: value })} />
                    <Field label="Fecha de salida (AAAA-MM-DD)" required value={general.departure_date} onChangeText={(value) => setGeneral({ ...general, departure_date: value })} />
                    <Field label="Empresa / cliente" required value={general.client_name} onChangeText={(value) => setGeneral({ ...general, client_name: value })} />
                    <Field label="Atención / contacto" value={general.contact_name} onChangeText={(value) => setGeneral({ ...general, contact_name: value })} />
                  </FormSection>
                  <FormSection title="Ubicación y referencia">
                    <Field label="Domicilio" multiline value={general.address} onChangeText={(value) => setGeneral({ ...general, address: value })} />
                    <Field label="C.P." value={general.postal_code} onChangeText={(value) => setGeneral({ ...general, postal_code: value })} />
                    <Field label="Ciudad" value={general.city} onChangeText={(value) => setGeneral({ ...general, city: value })} />
                    <Field label="Estado" value={general.state_name} onChangeText={(value) => setGeneral({ ...general, state_name: value })} />
                    <Field label="Orden de compra / cotización" value={general.purchase_order} onChangeText={(value) => setGeneral({ ...general, purchase_order: value })} />
                    <Field label="Observaciones" multiline value={general.notes} onChangeText={(value) => setGeneral({ ...general, notes: value })} />
                  </FormSection>
                  <Pressable disabled={!general.client_name.trim() || busy} style={styles.primary} onPress={createWorkOrder}><Text style={styles.primaryText}>Crear OT y capturar equipos</Text></Pressable>
                </>
              )}

              {workOrder && step !== 'general' && (
                <>
                  <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.related}>
                    {workOrder.related_work_orders.map((item) => (
                      <Pressable key={item.id} onPress={() => selectRelated(item.id)} style={[styles.relatedChip, item.id === workOrder.id && styles.relatedActive]}>
                        <Text style={[styles.relatedFolio, item.id === workOrder.id && styles.relatedActiveText]}>{item.folio}</Text>
                        <Text style={[styles.relatedCount, item.id === workOrder.id && styles.relatedActiveText]}>{item.equipment_count}/10</Text>
                      </Pressable>
                    ))}
                  </ScrollView>
                  <View style={styles.summary}><Text style={styles.summaryClient}>{workOrder.client_name}</Text><Text style={styles.summaryLine}>{workOrder.reception_date} → {workOrder.departure_date}</Text><Text style={styles.summaryLine}>{workOrder.address}</Text></View>
                </>
              )}

              {workOrder && step === 'capture' && (
                <>
                  <View style={styles.sectionRow}><Text style={styles.sectionTitle}>Equipos</Text><Text style={styles.counter}>{workOrder.equipment.length}/10</Text></View>
                  {workOrder.equipment.map((item) => (
                    <Pressable key={item.id} style={styles.equipmentRow} onPress={() => editable && showEquipmentEditor(item)}>
                      <View style={styles.flex}><Text style={styles.equipmentTitle}>{item.position}. {item.instrument}</Text><Text style={styles.equipmentMeta}>{item.brand} · {item.identification} · {item.serial_number}</Text></View>
                      <Text style={item.is_good_condition ? styles.good : styles.bad}>{item.is_good_condition ? '✓' : 'X'}</Text>
                    </Pressable>
                  ))}
                  {!workOrder.equipment.length && <Text style={styles.empty}>Aún no hay equipos.</Text>}
                  {editable && workOrder.equipment.length < 10 && <Pressable style={styles.secondary} onPress={() => showEquipmentEditor('new')}><Text style={styles.secondaryText}>+ Añadir equipo</Text></Pressable>}
                  {editable && workOrder.equipment.length === 10 && <Pressable style={styles.secondary} onPress={addAdditional}><Text style={styles.secondaryText}>Asignar OT extra</Text></Pressable>}
                  <Pressable disabled={!workOrder.equipment.length} style={[styles.primary, !workOrder.equipment.length && styles.disabled]} onPress={() => setStep('review')}><Text style={styles.primaryText}>Continuar</Text></Pressable>
                </>
              )}

              {workOrder && step === 'review' && (
                <>
                  <Text style={styles.sectionTitle}>Revisión del grupo</Text>
                  {workOrder.related_work_orders.map((item) => <Text key={item.id} style={styles.reviewLine}>OT {item.folio}: {item.equipment_count} equipo(s)</Text>)}
                  <Text style={styles.notice}>Las firmas se capturarán una sola vez y se aplicarán a todos los PDFs del grupo. Después de firmar no se podrán agregar OT ni equipos.</Text>
                  <Pressable style={styles.secondary} onPress={() => setStep('capture')}><Text style={styles.secondaryText}>Editar equipos</Text></Pressable>
                  <Pressable style={styles.primary} onPress={() => setStep('signatures')}><Text style={styles.primaryText}>Continuar a firmas</Text></Pressable>
                </>
              )}

              {workOrder && step === 'signatures' && workOrder.status === 'draft' && (
                <>
                  <View style={styles.sectionIntro}>
                    <Text style={styles.sectionEyebrow}>CIERRE DEL GRUPO</Text>
                    <Text style={styles.sectionTitle}>Firmas del grupo</Text>
                    <Text style={styles.sectionDescription}>Una sola sesión se aplicará a todos los PDFs relacionados.</Text>
                  </View>
                  <FormSection title="Técnico responsable">
                    <Field label="Nombre del técnico" required value={technicianName} onChangeText={setTechnicianName} />
                    <SignaturePad label="Firma del técnico" value={technicianSignature} onChange={setTechnicianSignature} />
                  </FormSection>
                  <FormSection title="Cliente que recibe">
                    <Field label="Nombre del cliente" required value={clientName} onChangeText={setClientName} />
                    <SignaturePad label="Firma del cliente" value={clientSignature} onChange={setClientSignature} />
                  </FormSection>
                  <Pressable disabled={!technicianSignature || !clientSignature || !technicianName || !clientName} style={styles.primary} onPress={applySignatures}><Text style={styles.primaryText}>Aplicar firmas a todo el grupo</Text></Pressable>
                </>
              )}

              {workOrder && step === 'signatures' && workOrder.status === 'ready_for_signatures' && (
                <>
                  <Text style={styles.sectionTitle}>Grupo firmado</Text>
                  <Text style={styles.notice}>La misma sesión de firma quedó vinculada a {workOrder.related_work_orders.length} OT. El grupo ya está bloqueado para nuevas OT y equipos.</Text>
                  <Pressable style={styles.primary} onPress={completeGroup}><Text style={styles.primaryText}>Finalizar grupo y generar PDFs</Text></Pressable>
                </>
              )}

              {workOrder && step === 'completed' && (
                <>
                  <Text style={styles.sectionTitle}>OT {workOrder.folio} finalizada</Text>
                  <Text style={styles.notice}>Selecciona arriba cada folio para abrir, imprimir o compartir su PDF individual.</Text>
                  <Pressable style={styles.primary} onPress={() => downloadPdf('print')}><Text style={styles.primaryText}>Ver / imprimir OT {workOrder.folio}</Text></Pressable>
                  <Pressable style={styles.secondary} onPress={() => downloadPdf('share')}><Text style={styles.secondaryText}>Compartir OT {workOrder.folio}</Text></Pressable>
                </>
              )}
            </ScrollView>
          </KeyboardAvoidingView>

          {equipmentEditor && (
            <View style={styles.overlay}>
              <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={styles.overlayCard}>
                <ScrollView contentContainerStyle={styles.overlayContent} keyboardShouldPersistTaps="handled">
                  <View style={styles.overlayHandle} />
                  <Text style={styles.sectionEyebrow}>EQUIPO DE LA OT {workOrder?.folio}</Text>
                  <Text style={styles.sectionTitle}>{equipmentEditor === 'new' ? 'Añadir equipo' : 'Editar equipo'}</Text>
                  <Text style={styles.sectionDescription}>Registra únicamente los datos que aparecerán en la orden institucional.</Text>
                  <Field label="Instrumento" required value={equipment.instrument} onChangeText={(value) => setEquipment({ ...equipment, instrument: value })} />
                  <Field label="Marca" required value={equipment.brand} onChangeText={(value) => setEquipment({ ...equipment, brand: value })} />
                  <Field label="Identificación" required value={equipment.identification} onChangeText={(value) => setEquipment({ ...equipment, identification: value })} />
                  <Field label="Serie" required value={equipment.serial_number} onChangeText={(value) => setEquipment({ ...equipment, serial_number: value })} />
                  <Field label="Informe (opcional)" value={equipment.report_number ?? ''} onChangeText={(value) => setEquipment({ ...equipment, report_number: value || null })} />
                  <Text style={styles.fieldLabel}>Estado físico</Text>
                  <View style={styles.conditionRow}>
                    <Pressable onPress={() => setEquipment({ ...equipment, is_good_condition: true })} style={[styles.condition, equipment.is_good_condition && styles.conditionSelected]}><Text style={styles.conditionText}>✓ Bueno</Text></Pressable>
                    <Pressable onPress={() => setEquipment({ ...equipment, is_good_condition: false })} style={[styles.condition, !equipment.is_good_condition && styles.conditionBadSelected]}><Text style={styles.conditionText}>X Malo</Text></Pressable>
                  </View>
                  <View style={styles.actionRow}>
                    <Pressable style={styles.cancel} onPress={() => setEquipmentEditor(null)}><Text>Cancelar</Text></Pressable>
                    <Pressable disabled={!canSaveEquipment} style={styles.save} onPress={saveEquipment}><Text style={styles.primaryText}>Guardar equipo</Text></Pressable>
                  </View>
                  {equipmentEditor !== 'new' && <Pressable onPress={removeEquipment}><Text style={styles.delete}>Eliminar equipo</Text></Pressable>}
                </ScrollView>
              </KeyboardAvoidingView>
            </View>
          )}
        </SafeAreaView>
        </SafeAreaProvider>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 }, center: { alignItems: 'center', flex: 1, justifyContent: 'center' }, screen: { backgroundColor: '#f4f7fa', flex: 1 },
  header: { paddingBottom: 8, paddingHorizontal: 20, paddingTop: 18 }, back: { color: '#0067a8', fontSize: 17, marginBottom: 18 }, title: { color: '#142b3a', fontSize: 29, fontWeight: '800' }, subtitle: { color: '#667582', marginTop: 7 },
  primary: { alignItems: 'center', backgroundColor: '#0067a8', borderRadius: 12, justifyContent: 'center', marginTop: 18, minHeight: 52, paddingHorizontal: 18 }, primaryText: { color: '#fff', fontSize: 16, fontWeight: '700' }, screenPrimary: { marginHorizontal: 20 },
  secondary: { alignItems: 'center', borderColor: '#0067a8', borderRadius: 10, borderWidth: 1.5, justifyContent: 'center', marginTop: 14, minHeight: 50 }, secondaryText: { color: '#0067a8', fontSize: 16, fontWeight: '700' }, disabled: { opacity: 0.4 },
  loader: { marginTop: 40 }, list: { gap: 10, padding: 20, paddingTop: 0 }, card: { alignItems: 'center', backgroundColor: '#fff', borderRadius: 12, flexDirection: 'row', justifyContent: 'space-between', padding: 16 }, folio: { color: '#0067a8', fontSize: 18, fontWeight: '800' }, client: { color: '#334451', marginTop: 3 }, cardRight: { alignItems: 'flex-end' }, count: { fontWeight: '700' }, status: { color: '#70808d', fontSize: 12, marginTop: 3 }, empty: { color: '#70808d', paddingVertical: 22, textAlign: 'center' },
  modalScreen: { backgroundColor: '#f4f7f9', flex: 1 }, modalHeader: { alignItems: 'center', backgroundColor: '#fff', borderBottomColor: '#dce3e9', borderBottomWidth: 1, flexDirection: 'row', justifyContent: 'space-between', paddingHorizontal: 20, paddingVertical: 18 }, modalTitle: { color: '#142b3a', fontSize: 21, fontWeight: '800' }, modalHint: { color: '#637280', fontSize: 12, marginTop: 5 }, close: { color: '#0067a8', fontSize: 16, fontWeight: '700', paddingVertical: 8 }, modalContent: { paddingBottom: 72, paddingHorizontal: 20, paddingTop: 26 }, sectionIntro: { marginBottom: 20 }, sectionEyebrow: { color: '#008f87', fontSize: 12, fontWeight: '800', letterSpacing: 1.1, marginBottom: 7 }, sectionTitle: { color: '#142b3a', fontSize: 24, fontWeight: '800', marginBottom: 8 }, sectionDescription: { color: '#637280', fontSize: 15, lineHeight: 21 }, sectionRow: { alignItems: 'center', flexDirection: 'row', justifyContent: 'space-between' }, counter: { color: '#0067a8', fontSize: 18, fontWeight: '800' },
  formSection: { backgroundColor: '#fff', borderColor: '#dbe4ea', borderRadius: 16, borderWidth: 1, marginBottom: 16, paddingHorizontal: 16, paddingTop: 18 }, formSectionTitle: { color: '#173746', fontSize: 16, fontWeight: '800', marginBottom: 16 }, field: { marginBottom: 18 }, fieldLabel: { color: '#344553', fontSize: 14, fontWeight: '700', marginBottom: 8 }, input: { backgroundColor: '#fbfcfd', borderColor: '#b9c8d2', borderRadius: 11, borderWidth: 1, fontSize: 16, minHeight: 50, paddingHorizontal: 14 }, multiline: { minHeight: 86, paddingTop: 13, textAlignVertical: 'top' },
  related: { marginBottom: 14 }, relatedChip: { backgroundColor: '#e5ebf0', borderRadius: 10, marginRight: 8, minWidth: 78, padding: 10 }, relatedActive: { backgroundColor: '#0067a8' }, relatedFolio: { fontSize: 16, fontWeight: '800' }, relatedCount: { color: '#556571', fontSize: 12 }, relatedActiveText: { color: '#fff' }, summary: { backgroundColor: '#eef3f6', borderRadius: 10, marginBottom: 20, padding: 14 }, summaryClient: { fontSize: 18, fontWeight: '800' }, summaryLine: { color: '#53636f', marginTop: 4 },
  equipmentRow: { alignItems: 'center', backgroundColor: '#fff', borderBottomColor: '#e2e7eb', borderBottomWidth: 1, flexDirection: 'row', padding: 14 }, equipmentTitle: { fontSize: 16, fontWeight: '700' }, equipmentMeta: { color: '#61717d', fontSize: 13, marginTop: 3 }, good: { color: '#19713b', fontSize: 22, fontWeight: '900' }, bad: { color: '#a51c30', fontSize: 20, fontWeight: '900' },
  reviewLine: { backgroundColor: '#fff', borderRadius: 8, fontSize: 17, fontWeight: '700', marginBottom: 8, padding: 14 }, notice: { backgroundColor: '#fff5cf', borderRadius: 10, color: '#5f4d00', fontSize: 15, lineHeight: 22, padding: 14 },
  overlay: { ...StyleSheet.absoluteFillObject, backgroundColor: 'rgba(16,28,38,0.58)', justifyContent: 'flex-end', zIndex: 20 }, overlayCard: { backgroundColor: '#f4f7f9', borderTopLeftRadius: 24, borderTopRightRadius: 24, maxHeight: '92%', overflow: 'hidden' }, overlayContent: { paddingBottom: 38, paddingHorizontal: 20, paddingTop: 12 }, overlayHandle: { alignSelf: 'center', backgroundColor: '#b8c4cc', borderRadius: 3, height: 5, marginBottom: 22, width: 46 }, conditionRow: { flexDirection: 'row', gap: 10, marginBottom: 20 }, condition: { alignItems: 'center', backgroundColor: '#e7ecef', borderRadius: 11, flex: 1, padding: 15 }, conditionSelected: { backgroundColor: '#bde8c9' }, conditionBadSelected: { backgroundColor: '#f5c6cc' }, conditionText: { fontSize: 16, fontWeight: '800' }, actionRow: { flexDirection: 'row', gap: 10 }, cancel: { alignItems: 'center', backgroundColor: '#e3e8ec', borderRadius: 11, flex: 1, justifyContent: 'center', minHeight: 50 }, save: { alignItems: 'center', backgroundColor: '#0067a8', borderRadius: 11, flex: 2, justifyContent: 'center', minHeight: 50 }, delete: { color: '#a51c30', fontSize: 16, fontWeight: '700', padding: 18, textAlign: 'center' },
  busy: { alignItems: 'center', backgroundColor: '#243844', flexDirection: 'row', gap: 10, justifyContent: 'center', padding: 11 }, busyText: { color: '#fff', fontWeight: '700' },
});
