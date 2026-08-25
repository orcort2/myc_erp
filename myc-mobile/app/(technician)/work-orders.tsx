import * as FileSystem from 'expo-file-system/legacy';
import * as Print from 'expo-print';
import * as Sharing from 'expo-sharing';
import { useFocusEffect } from '@react-navigation/native';
import { Redirect, router, useLocalSearchParams } from 'expo-router';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import {
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Modal,
  Platform,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { SafeAreaProvider, SafeAreaView } from 'react-native-safe-area-context';

import { apiUrl, readApiError } from '@/src/api/client';
import { useAuth } from '@/src/auth/AuthProvider';
import { MobileSignatureFlow } from '@/src/components/signatures/MobileSignatureFlow';
import {
  reconcileSignatureFlowState,
  type SignatureFlowState,
  type SignaturePayload,
} from '@/src/components/signatures/signature-flow-state';
import { useNotificationSync } from '@/src/notifications/NotificationSyncProvider';
import { affectsWorkOrders, RefreshGate } from '@/src/notifications/refresh-policy';
import {
  canDeleteLabWorkOrder,
  deleteLabWorkOrder,
  LabWorkOrderDeletionCoordinator,
} from '@/src/services/lab-work-order-deletion';
import { canSkipSignaturesAfterReopen } from '@/src/services/lab-work-order-signature-policy';
import { postLabGroupSignatures } from '@/src/services/lab-work-order-signature-submission';
import type {
  EquipmentData,
  GeneralData,
  LabEquipment,
  LabListItem,
  LabWorkOrder,
} from '@/src/types/lab-work-order';

const today = () => new Date().toISOString().slice(0, 10);
const PAGE_SIZE = 25;
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
  const { authorizedFetch, isLoading: authLoading, refreshSession, session, user } = useAuth();
  const { publishLocalChange, subscribe } = useNotificationSync();
  const params = useLocalSearchParams<{ workOrderId?: string }>();
  const [items, setItems] = useState<LabListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [listError, setListError] = useState('');
  const [hasMore, setHasMore] = useState(false);
  const [folioFilter, setFolioFilter] = useState('');
  const [clientFilter, setClientFilter] = useState('');
  const [debouncedFolio, setDebouncedFolio] = useState('');
  const [debouncedClient, setDebouncedClient] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | 'open' | 'completed'>('all');
  const [busy, setBusy] = useState(false);
  const [open, setOpen] = useState(false);
  const [step, setStep] = useState<Step>('general');
  const [general, setGeneral] = useState<GeneralData>(emptyGeneral);
  const [workOrder, setWorkOrder] = useState<LabWorkOrder | null>(null);
  const [equipmentEditor, setEquipmentEditor] = useState<LabEquipment | 'new' | null>(null);
  const [equipment, setEquipment] = useState<EquipmentData>(emptyEquipment);
  const [signatureFlowState, setSignatureFlowState] = useState<SignatureFlowState | null>(null);
  const [signatureDrawing, setSignatureDrawing] = useState(false);
  const [ticketOpen, setTicketOpen] = useState(false);
  const [ticketReason, setTicketReason] = useState('');
  const [ticketDescription, setTicketDescription] = useState('');
  const [refreshing, setRefreshing] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const itemCount = useRef(0);
  const refreshGate = useRef(new RefreshGate());
  const deletionCoordinator = useRef(new LabWorkOrderDeletionCoordinator());
  const signatureSubmitRef = useRef(false);

  const request = useCallback(async <T,>(path: string, init?: RequestInit): Promise<T> => {
    const headers = new Headers(init?.headers);
    if (init?.body) headers.set('Content-Type', 'application/json');
    const response = await authorizedFetch(apiUrl(path), { ...init, headers });
    if (!response.ok) throw new Error(await readApiError(response));
    return response.json() as Promise<T>;
  }, [authorizedFetch]);

  const refresh = useCallback(async (reset = true) => {
    if (reset) setLoading(true);
    else setLoadingMore(true);
    setListError('');
    try {
      const offset = reset ? 0 : itemCount.current;
      const query = [
        `limit=${PAGE_SIZE}`,
        `offset=${offset}`,
        `status=${statusFilter}`,
        debouncedFolio ? `folio=${encodeURIComponent(debouncedFolio)}` : '',
        debouncedClient ? `client=${encodeURIComponent(debouncedClient)}` : '',
      ].filter(Boolean).join('&');
      const next = await request<LabListItem[]>(`/mobile/v1/technician/lab-work-orders?${query}`);
      setItems((current) => {
        const updated = reset ? next : [...current, ...next];
        itemCount.current = updated.length;
        return updated;
      });
      setHasMore(next.length === PAGE_SIZE);
    } catch (error) {
      setListError(error instanceof Error ? error.message : 'Intenta nuevamente');
    } finally {
      if (reset) setLoading(false);
      else setLoadingMore(false);
    }
  }, [debouncedClient, debouncedFolio, request, statusFilter]);

  const refreshActive = useCallback(async (force = false) => {
    if (!refreshGate.current.shouldRefresh(Date.now(), force)) return;
    setRefreshing(true);
    await refresh(true);
    setRefreshing(false);
  }, [refresh]);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedFolio(folioFilter.trim());
      setDebouncedClient(clientFilter.trim());
    }, 400);
    return () => clearTimeout(timer);
  }, [clientFilter, folioFilter]);

  useEffect(() => {
    if (user) refresh(true);
    // refresh also depends on the current item count for pagination; filters are the trigger here.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedClient, debouncedFolio, statusFilter, user]);

  useFocusEffect(useCallback(() => { if (user) refreshActive(); }, [refreshActive, user]));

  useEffect(() => subscribe((event) => {
    if (!affectsWorkOrders(event)) return;
    refreshActive(event.source === 'local');
    const targetId = event.work_order_id;
    if (workOrder && (!targetId || targetId === workOrder.id)) {
      request<LabWorkOrder>(`/mobile/v1/technician/lab-work-orders/${workOrder.id}`)
        .then((detail) => {
          const sameSignatureGroup = signatureFlowState?.rootWorkOrderId === detail.root_work_order_id;
          setSignatureFlowState((current) => current == null ? null : reconcileSignatureFlowState(current, {
            clientName: detail.contact_name ?? '',
            rootWorkOrderId: detail.root_work_order_id,
            technicianName: user?.full_name ?? '',
          }));
          if (!sameSignatureGroup) setSignatureDrawing(false);
          setWorkOrder(detail);
          setStep((current) => sameSignatureGroup && current === 'signatures'
            ? current
            : detail.status === 'completed' ? 'completed' : detail.status === 'ready_for_signatures' ? 'signatures' : 'capture');
        })
        .catch(() => undefined);
    }
  }), [refreshActive, request, signatureFlowState?.rootWorkOrderId, subscribe, user?.full_name, workOrder]);

  // MOB-003: `user` gets a new object reference on every silent token
  // refresh (see AuthProvider.authorizedFetch -> refreshSession), which
  // would otherwise re-run this effect and call openExisting(id) again —
  // reopening the modal right after the technician closed it via
  // closeFlow(). openedDeepLinkId remembers which id was already handled so
  // a stale `user` reference alone never reopens it; a genuinely new
  // deep-link id still opens normally.
  const openedDeepLinkId = useRef<number | null>(null);
  useEffect(() => {
    const id = Number(params.workOrderId);
    if (id > 0 && user && openedDeepLinkId.current !== id) {
      openedDeepLinkId.current = id;
      openExisting(id);
    }
    // openExisting is intentionally invoked only for a new deep-link id.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params.workOrderId, user]);

  const editable = workOrder?.status === 'draft';
  const canDelete = !!user && canDeleteLabWorkOrder(user.permissions);
  const canSaveEquipment = useMemo(
    () => equipment.instrument.trim() && equipment.brand.trim() && equipment.identification.trim() && equipment.serial_number.trim(),
    [equipment],
  );

  function startNew() {
    setGeneral(emptyGeneral());
    setWorkOrder(null);
    setStep('general');
    setSignatureFlowState(null);
    setSignatureDrawing(false);
    setOpen(true);
  }

  function clearFilters() {
    setFolioFilter('');
    setClientFilter('');
    setStatusFilter('all');
  }

  async function requestReopening() {
    if (!workOrder || !ticketReason.trim() || !ticketDescription.trim()) return;
    setBusy(true);
    try {
      await request('/mobile/v1/technician/tickets', {
        method: 'POST',
        body: JSON.stringify({
          work_order_id: workOrder.id,
          reason: ticketReason.trim(),
          description: ticketDescription.trim(),
          requested_signature_policy: 'preserve',
        }),
      });
      setTicketOpen(false);
      setTicketReason('');
      setTicketDescription('');
      publishLocalChange({
        event_type: 'ticket.created', entity_type: 'ticket', work_order_id: workOrder.id,
      });
      Alert.alert('Solicitud enviada', 'La OT seguirá cerrada hasta que un usuario autorizado apruebe el ticket.');
    } catch (error) {
      Alert.alert('No fue posible crear el ticket', error instanceof Error ? error.message : 'Intenta nuevamente');
    } finally {
      setBusy(false);
    }
  }

  async function openExisting(id: number) {
    setBusy(true);
    try {
      const detail = await request<LabWorkOrder>(`/mobile/v1/technician/lab-work-orders/${id}`);
      const sameSignatureGroup = signatureFlowState?.rootWorkOrderId === detail.root_work_order_id;
      setSignatureFlowState((current) => current == null ? null : reconcileSignatureFlowState(current, {
        clientName: detail.contact_name ?? '',
        rootWorkOrderId: detail.root_work_order_id,
        technicianName: user?.full_name ?? '',
      }));
      if (!sameSignatureGroup) setSignatureDrawing(false);
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
      setStep((current) => sameSignatureGroup && current === 'signatures'
        ? current
        : detail.status === 'completed' ? 'completed' : detail.status === 'ready_for_signatures' ? 'signatures' : 'capture');
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
      const path = workOrder
        ? `/mobile/v1/technician/lab-work-orders/${workOrder.id}`
        : '/mobile/v1/technician/lab-work-orders';
      const detail = await request<LabWorkOrder>(path, {
        method: workOrder ? 'PATCH' : 'POST',
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
          ...(workOrder ? { expected_edit_version: workOrder.edit_version } : {}),
        }),
      });
      setWorkOrder(detail);
      setStep('capture');
      publishLocalChange({
        event_type: 'work_order.updated', entity_type: 'work_order', entity_id: detail.id, work_order_id: detail.id,
      });
    } catch (error) {
      Alert.alert('No fue posible crear la OT', error instanceof Error ? error.message : 'Revisa los datos');
    } finally {
      setBusy(false);
    }
  }

  async function selectRelated(id: number) {
    setBusy(true);
    try {
      const detail = await request<LabWorkOrder>(`/mobile/v1/technician/lab-work-orders/${id}`);
      if (signatureFlowState && detail.root_work_order_id !== signatureFlowState.rootWorkOrderId) {
        setSignatureDrawing(false);
      }
      setSignatureFlowState((current) => current == null ? null : reconcileSignatureFlowState(current, {
        clientName: detail.contact_name ?? '',
        rootWorkOrderId: detail.root_work_order_id,
        technicianName: user?.full_name ?? '',
      }));
      setWorkOrder(detail);
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
        body: JSON.stringify({ ...equipment, expected_edit_version: workOrder.edit_version }),
      });
      setWorkOrder(detail);
      setEquipmentEditor(null);
      publishLocalChange({ event_type: detail.signature_required ? 'ticket.signature_required' : 'work_order.updated', entity_type: 'work_order', entity_id: detail.id, work_order_id: detail.id });
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
        `/mobile/v1/technician/lab-work-orders/${workOrder.id}/equipment/${equipmentEditor.id}?expected_edit_version=${workOrder.edit_version}`,
        { method: 'DELETE' },
      );
      setWorkOrder(detail);
      setEquipmentEditor(null);
      publishLocalChange({ event_type: detail.signature_required ? 'ticket.signature_required' : 'work_order.updated', entity_type: 'work_order', entity_id: detail.id, work_order_id: detail.id });
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
      const detail = await request<LabWorkOrder>(
        `/mobile/v1/technician/lab-work-orders/${workOrder.id}/additional`,
        { method: 'POST' },
      );
      setWorkOrder(detail);
      publishLocalChange({ event_type: detail.signature_required ? 'ticket.signature_required' : 'work_order.updated', entity_type: 'work_order', entity_id: detail.id, work_order_id: detail.id });
    } catch (error) {
      Alert.alert('No fue posible asignar la OT extra', error instanceof Error ? error.message : 'Intenta nuevamente');
    } finally {
      setBusy(false);
    }
  }

  function openSignatureFlow() {
    if (!workOrder) {
      Alert.alert('No hay un grupo activo', 'Abre nuevamente la orden antes de capturar firmas.');
      return;
    }
    setSignatureFlowState((current) => reconcileSignatureFlowState(current, {
      clientName: workOrder.contact_name ?? '',
      rootWorkOrderId: workOrder.root_work_order_id,
      technicianName: user?.full_name ?? '',
    }));
    setStep('signatures');
  }

  async function applySignatures(payload: SignaturePayload, capturedContextId: number) {
    if (signatureSubmitRef.current) throw new Error('Las firmas ya se están guardando.');
    if (!workOrder || workOrder.root_work_order_id !== capturedContextId) {
      setSignatureFlowState(null);
      setSignatureDrawing(false);
      throw new Error('El grupo activo cambió. Captura nuevamente las firmas.');
    }
    signatureSubmitRef.current = true;
    setBusy(true);
    const signedAt = new Date().toISOString();
    try {
      const detail = await postLabGroupSignatures({ payload, request, signedAt, workOrder });
      setWorkOrder(detail);
      setSignatureFlowState(null);
      setSignatureDrawing(false);
      publishLocalChange({ event_type: 'work_order.signatures_updated', entity_type: 'work_order', entity_id: detail.id, work_order_id: detail.id });
    } catch (error) {
      throw new Error(error instanceof Error ? error.message : 'No fue posible aplicar las firmas. Intenta nuevamente.');
    } finally {
      signatureSubmitRef.current = false;
      setBusy(false);
    }
  }

  async function completeGroup() {
    if (!workOrder) return;
    setBusy(true);
    try {
      const detail = await request<LabWorkOrder>(
        `/mobile/v1/technician/lab-work-orders/${workOrder.id}/complete`,
        { method: 'POST' },
      );
      setWorkOrder(detail);
      setStep('completed');
      await refresh();
      publishLocalChange({ event_type: 'work_order.completed', entity_type: 'work_order', entity_id: detail.id, work_order_id: detail.id });
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

  async function performWorkOrderDeletion(target: LabWorkOrder) {
    if (deletionCoordinator.current.isDeleting) return;
    setDeleting(true);
    setBusy(true);
    const result = await deletionCoordinator.current.run(
      true,
      () => deleteLabWorkOrder(
        authorizedFetch,
        apiUrl(`/mobile/v1/technician/lab-work-orders/${target.id}`),
      ),
    );
    try {
      if (result.kind === 'ignored' || result.kind === 'cancelled') return;
      if (result.kind === 'success' || result.kind === 'not_found') {
        setOpen(false);
        setWorkOrder(null);
        setSignatureFlowState(null);
        setSignatureDrawing(false);
        setEquipmentEditor(null);
        setTicketOpen(false);
        await refresh(true);
        publishLocalChange({
          event_type: 'work_order.deleted',
          entity_type: 'lab_work_order',
          entity_id: target.id,
          work_order_id: target.id,
        });
        Alert.alert(
          result.kind === 'success' ? 'Orden eliminada' : 'Orden no disponible',
          result.kind === 'success'
            ? `La OT ${target.folio} fue eliminada y el listado quedó actualizado.`
            : 'Esta OT LAB ya no existe. El listado fue actualizado.',
        );
        return;
      }
      if (result.kind === 'forbidden') {
        await refreshSession().catch(() => undefined);
        Alert.alert('Permiso requerido', 'No tienes permiso para eliminar esta orden de trabajo.');
        return;
      }
      if (result.kind === 'conflict') {
        Alert.alert('No fue posible eliminar', result.message);
        return;
      }
      if (result.kind === 'error') Alert.alert('No fue posible eliminar', result.message);
    } finally {
      setDeleting(false);
      setBusy(false);
    }
  }

  function confirmWorkOrderDeletion(target: LabWorkOrder) {
    if (deleting || deletionCoordinator.current.isDeleting) return;
    Alert.alert(
      'Eliminar orden de trabajo',
      `¿Deseas eliminar definitivamente la OT ${target.folio}?\n\nCliente: ${target.client_name}\n\nEsta acción eliminará la orden y su información exclusiva asociada.`,
      [
        { text: 'Cancelar', style: 'cancel' },
        {
          text: 'Eliminar',
          style: 'destructive',
          onPress: () => { void performWorkOrderDeletion(target); },
        },
      ],
    );
  }

  function closeFlow() {
    if (signatureSubmitRef.current) {
      Alert.alert('Guardado en curso', 'Espera a que termine el envío de las firmas.');
      return;
    }
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
          <View style={styles.filters}>
        <View style={styles.filterRow}>
          <View style={styles.filterField}>
            <Text style={styles.filterLabel}>Folio</Text>
            <TextInput
              keyboardType="number-pad"
              onChangeText={setFolioFilter}
              placeholder="6401"
              style={styles.filterInput}
              value={folioFilter}
            />
          </View>

          <View style={styles.filterField}>
            <Text style={styles.filterLabel}>Cliente</Text>
            <TextInput
              autoCapitalize="words"
              onChangeText={setClientFilter}
              placeholder="Buscar cliente"
              style={styles.filterInput}
              value={clientFilter}
            />
          </View>
        </View>

        <View style={styles.filterFooter}>
          <View style={styles.statusFilters}>
            {([
              ['all', 'Todas'],
              ['open', 'Abiertas'],
              ['completed', 'Finalizadas'],
            ] as const).map(([value, label]) => (
              <Pressable
                key={value}
                onPress={() => setStatusFilter(value)}
                style={[
                  styles.statusChip,
                  statusFilter === value && styles.statusChipActive,
                ]}
              >
                <Text
                  style={[
                    styles.statusChipText,
                    statusFilter === value && styles.statusChipTextActive,
                  ]}
                >
                  {label}
                </Text>
              </Pressable>
            ))}
          </View>

          <Pressable onPress={clearFilters} style={styles.clearFilters}>
            <Text style={styles.clearFiltersText}>Limpiar</Text>
          </Pressable>
        </View>
      </View>
      <Pressable style={[styles.primary, styles.screenPrimary]} onPress={startNew}><Text style={styles.primaryText}>+ Generar orden</Text></Pressable>
      {loading ? <ActivityIndicator style={styles.loader} /> : (
        <ScrollView contentContainerStyle={styles.list} refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => refreshActive(true)} />}>
          {!!listError && (
            <View style={styles.errorState}>
              <Text style={styles.errorText}>{listError}</Text>
              <Pressable onPress={() => refresh(true)}><Text style={styles.retry}>Reintentar</Text></Pressable>
            </View>
          )}
          {items.map((item) => (
            <Pressable key={item.id} style={styles.card} onPress={() => openExisting(item.id)}>
              <View style={styles.cardContent}><Text style={styles.folio}>OT {item.folio}</Text><Text ellipsizeMode="tail" numberOfLines={2} style={styles.client}>{item.client_name}</Text></View>
              <View style={styles.cardRight}><Text style={styles.count}>{item.equipment_count}/10</Text><Text style={styles.status}>{item.status}</Text></View>
            </Pressable>
          ))}
          {!items.length && !listError && <Text style={styles.empty}>No hay órdenes que coincidan con los filtros.</Text>}
          {hasMore && (
            <Pressable disabled={loadingMore} onPress={() => refresh(false)} style={styles.loadMore}>
              {loadingMore ? <ActivityIndicator /> : <Text style={styles.secondaryText}>Cargar más</Text>}
            </Pressable>
          )}
        </ScrollView>
      )}

      <Modal animationType="slide" onRequestClose={closeFlow} visible={open}>
        <SafeAreaProvider>
        <SafeAreaView edges={['top', 'right', 'bottom', 'left']} style={styles.modalScreen}>
          <View style={styles.modalHeader}>
            <View><Text style={styles.modalTitle}>OT LAB {workOrder ? `· ${workOrder.folio}` : ''}</Text><Text style={styles.modalHint}>Firma única para todo el grupo</Text></View>
            <Pressable disabled={deleting || signatureSubmitRef.current} onPress={closeFlow}><Text style={styles.close}>Cerrar</Text></Pressable>
          </View>
          {busy && <View style={styles.busy}><ActivityIndicator color="#fff" /><Text style={styles.busyText}>{deleting ? 'Eliminando orden…' : 'Guardando…'}</Text></View>}
          <KeyboardAvoidingView
            behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
            style={styles.flex}
          >
            <ScrollView
              automaticallyAdjustKeyboardInsets
              contentContainerStyle={styles.modalContent}
              keyboardShouldPersistTaps="handled"
              nestedScrollEnabled
              scrollEnabled={!signatureDrawing}
              style={styles.flex}
            >
              {step === 'general' && (
                <>
                  <View style={styles.sectionIntro}>
                    <Text style={styles.sectionEyebrow}>{workOrder ? `REVISIÓN ${workOrder.revision_number}` : 'NUEVA ORDEN'}</Text>
                    <Text style={styles.sectionTitle}>{workOrder ? 'Editar datos generales' : 'Datos generales'}</Text>
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
                  <Pressable disabled={!general.client_name.trim() || busy} style={styles.primary} onPress={createWorkOrder}><Text style={styles.primaryText}>{workOrder ? 'Guardar cambios' : 'Crear OT y capturar equipos'}</Text></Pressable>
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
                  {!!workOrder.reopen_ticket_id && editable && (
                    <Pressable style={styles.secondary} onPress={() => setStep('general')}>
                      <Text style={styles.secondaryText}>Editar datos generales</Text>
                    </Pressable>
                  )}
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
                  {canSkipSignaturesAfterReopen(workOrder) ? (
                    <Pressable style={styles.primary} onPress={completeGroup}><Text style={styles.primaryText}>Cerrar orden</Text></Pressable>
                  ) : (
                    <Pressable style={styles.primary} onPress={openSignatureFlow}><Text style={styles.primaryText}>Continuar a firmas</Text></Pressable>
                  )}
                </>
              )}

              {workOrder && step === 'signatures' && workOrder.status === 'draft' && (
                signatureFlowState?.rootWorkOrderId === workOrder.root_work_order_id ? (
                  <MobileSignatureFlow
                    currentContextId={workOrder.root_work_order_id}
                    key={signatureFlowState.rootWorkOrderId}
                    onDrawingChange={setSignatureDrawing}
                    onStateChange={setSignatureFlowState}
                    onSubmit={applySignatures}
                    state={signatureFlowState}
                  />
                ) : (
                  <View style={styles.errorState}>
                    <Text style={styles.errorText}>La captura anterior se descartó porque cambió el contexto del grupo.</Text>
                    <Pressable onPress={() => setStep('review')}><Text style={styles.retry}>Volver a revisión</Text></Pressable>
                  </View>
                )
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
                  <Pressable style={styles.secondary} onPress={() => setTicketOpen(true)}><Text style={styles.secondaryText}>Solicitar reapertura</Text></Pressable>
                </>
              )}

              {workOrder && canDelete && (
                <View style={styles.dangerZone}>
                  <Text style={styles.dangerTitle}>Acciones administrativas</Text>
                  <Text style={styles.dangerDescription}>La eliminación retira únicamente esta OT LAB y conserva los recursos compartidos por sus OT hermanas.</Text>
                  <Pressable
                    disabled={busy || deleting}
                    onPress={() => confirmWorkOrderDeletion(workOrder)}
                    style={[styles.deleteWorkOrder, (busy || deleting) && styles.disabled]}
                  >
                    <Text style={styles.deleteWorkOrderText}>Eliminar orden de trabajo</Text>
                  </Pressable>
                </View>
              )}
            </ScrollView>
          </KeyboardAvoidingView>

          {equipmentEditor && (
            <View style={styles.overlay}>
              <KeyboardAvoidingView
                behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
                style={styles.overlayCard}
              >
                <ScrollView
                  automaticallyAdjustKeyboardInsets
                  contentContainerStyle={styles.overlayContent}
                  keyboardShouldPersistTaps="handled"
                >
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
          {ticketOpen && (
            <View style={styles.overlay}>
              <KeyboardAvoidingView
                behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
                style={styles.overlayCard}
              >
                <ScrollView
                  automaticallyAdjustKeyboardInsets
                  contentContainerStyle={styles.overlayContent}
                  keyboardShouldPersistTaps="handled"
                >
                  <View style={styles.overlayHandle} />
                  <Text style={styles.sectionEyebrow}>TICKET DE REAPERTURA</Text>
                  <Text style={styles.sectionTitle}>¿Por qué necesitas modificar esta orden?</Text>
                  <Text style={styles.sectionDescription}>La OT permanecerá cerrada hasta que la solicitud sea aprobada.</Text>
                  <Field label="Motivo" required value={ticketReason} onChangeText={setTicketReason} />
                  <Field label="Descripción" required multiline value={ticketDescription} onChangeText={setTicketDescription} />
                  <View style={styles.actionRow}>
                    <Pressable style={styles.cancel} onPress={() => setTicketOpen(false)}><Text>Cancelar</Text></Pressable>
                    <Pressable disabled={!ticketReason.trim() || !ticketDescription.trim()} style={styles.save} onPress={requestReopening}><Text style={styles.primaryText}>Enviar solicitud</Text></Pressable>
                  </View>
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
  flex: {
    flex: 1,
  },

  center: {
    alignItems: 'center',
    flex: 1,
    justifyContent: 'center',
  },

  screen: {
    backgroundColor: '#f4f7fa',
    flex: 1,
  },

  header: {
    paddingBottom: 8,
    paddingHorizontal: 20,
    paddingTop: 18,
  },

  back: {
    color: '#0067a8',
    fontSize: 17,
    marginBottom: 18,
  },

  title: {
    color: '#142b3a',
    fontSize: 29,
    fontWeight: '800',
  },

  subtitle: {
    color: '#667582',
    marginTop: 7,
  },

  filters: {
    backgroundColor: '#fff',
    borderColor: '#dbe4ea',
    borderRadius: 12,
    borderWidth: 1,
    gap: 8,
    marginHorizontal: 20,
    padding: 10,
  },

  filterRow: {
    flexDirection: 'row',
    gap: 8,
  },

  filterField: {
    flex: 1,
    gap: 4,
    minWidth: 0,
  },

  filterLabel: {
    color: '#344553',
    fontSize: 11,
    fontWeight: '700',
  },

  filterInput: {
    backgroundColor: '#f8fafb',
    borderColor: '#b9c8d2',
    borderRadius: 8,
    borderWidth: 1,
    fontSize: 14,
    height: 38,
    paddingHorizontal: 10,
  },

  filterFooter: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: 8,
  },

  statusFilters: {
    flex: 1,
    flexDirection: 'row',
    gap: 5,
  },

  statusChip: {
    alignItems: 'center',
    backgroundColor: '#e9eef2',
    borderRadius: 14,
    flex: 1,
    paddingVertical: 6,
  },

  statusChipActive: {
    backgroundColor: '#0067a8',
  },

  statusChipText: {
    color: '#425563',
    fontSize: 11,
    fontWeight: '700',
  },

  statusChipTextActive: {
    color: '#fff',
  },

  clearFilters: {
    paddingHorizontal: 6,
    paddingVertical: 5,
  },

  clearFiltersText: {
    color: '#0067a8',
    fontSize: 12,
    fontWeight: '700',
  },

  primary: {
    alignItems: 'center',
    backgroundColor: '#0067a8',
    borderRadius: 12,
    justifyContent: 'center',
    marginTop: 18,
    minHeight: 52,
    paddingHorizontal: 18,
  },

  primaryText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '700',
  },

  screenPrimary: {
    marginHorizontal: 20,
  },

  secondary: {
    alignItems: 'center',
    borderColor: '#0067a8',
    borderRadius: 10,
    borderWidth: 1.5,
    justifyContent: 'center',
    marginTop: 14,
    minHeight: 50,
  },

  secondaryText: {
    color: '#0067a8',
    fontSize: 16,
    fontWeight: '700',
  },

  disabled: {
    opacity: 0.4,
  },

  loader: {
    marginTop: 40,
  },

  list: {
    gap: 10,
    padding: 20,
    paddingTop: 0,
  },

  card: {
    alignItems: 'flex-start',
    backgroundColor: '#fff',
    borderRadius: 12,
    flexDirection: 'row',
    justifyContent: 'space-between',
    padding: 16,
  },

  cardContent: {
    flex: 1,
    minWidth: 0,
    paddingRight: 14,
  },

  folio: {
    color: '#0067a8',
    fontSize: 18,
    fontWeight: '800',
  },

  client: {
    color: '#334451',
    lineHeight: 19,
    marginTop: 3,
  },

  cardRight: {
    alignItems: 'flex-end',
    flexShrink: 0,
    minWidth: 48,
  },

  count: {
    fontWeight: '700',
  },

  status: {
    color: '#70808d',
    fontSize: 12,
    marginTop: 3,
  },

  empty: {
    color: '#70808d',
    paddingVertical: 22,
    textAlign: 'center',
  },

  errorState: {
    alignItems: 'center',
    backgroundColor: '#fff0f0',
    borderRadius: 12,
    padding: 16,
  },

  errorText: {
    color: '#8d1f2d',
    textAlign: 'center',
  },

  retry: {
    color: '#0067a8',
    fontWeight: '800',
    marginTop: 10,
  },

  loadMore: {
    alignItems: 'center',
    borderColor: '#0067a8',
    borderRadius: 10,
    borderWidth: 1,
    justifyContent: 'center',
    minHeight: 46,
  },

  modalScreen: {
    backgroundColor: '#f4f7f9',
    flex: 1,
  },

  modalHeader: {
    alignItems: 'center',
    backgroundColor: '#fff',
    borderBottomColor: '#dce3e9',
    borderBottomWidth: 1,
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingHorizontal: 20,
    paddingVertical: 18,
  },

  modalTitle: {
    color: '#142b3a',
    fontSize: 21,
    fontWeight: '800',
  },

  modalHint: {
    color: '#637280',
    fontSize: 12,
    marginTop: 5,
  },

  close: {
    color: '#0067a8',
    fontSize: 16,
    fontWeight: '700',
    paddingVertical: 8,
  },

  modalContent: {
    alignSelf: 'center',
    maxWidth: 820,
    paddingBottom: 72,
    paddingHorizontal: 20,
    paddingTop: 26,
    width: '100%',
  },

  sectionIntro: {
    marginBottom: 20,
  },

  sectionEyebrow: {
    color: '#008f87',
    fontSize: 12,
    fontWeight: '800',
    letterSpacing: 1.1,
    marginBottom: 7,
  },

  sectionTitle: {
    color: '#142b3a',
    fontSize: 24,
    fontWeight: '800',
    marginBottom: 8,
  },

  sectionDescription: {
    color: '#637280',
    fontSize: 15,
    lineHeight: 21,
  },

  sectionRow: {
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'space-between',
  },

  counter: {
    color: '#0067a8',
    fontSize: 18,
    fontWeight: '800',
  },

  formSection: {
    backgroundColor: '#fff',
    borderColor: '#dbe4ea',
    borderRadius: 16,
    borderWidth: 1,
    marginBottom: 16,
    paddingHorizontal: 16,
    paddingTop: 18,
  },

  formSectionTitle: {
    color: '#173746',
    fontSize: 16,
    fontWeight: '800',
    marginBottom: 16,
  },

  field: {
    marginBottom: 18,
  },

  fieldLabel: {
    color: '#344553',
    fontSize: 14,
    fontWeight: '700',
    marginBottom: 8,
  },

  input: {
    backgroundColor: '#fbfcfd',
    borderColor: '#b9c8d2',
    borderRadius: 11,
    borderWidth: 1,
    fontSize: 16,
    minHeight: 50,
    paddingHorizontal: 14,
  },

  multiline: {
    minHeight: 86,
    paddingTop: 13,
    textAlignVertical: 'top',
  },

  related: {
    marginBottom: 14,
  },

  relatedChip: {
    backgroundColor: '#e5ebf0',
    borderRadius: 10,
    marginRight: 8,
    minWidth: 78,
    padding: 10,
  },

  relatedActive: {
    backgroundColor: '#0067a8',
  },

  relatedFolio: {
    fontSize: 16,
    fontWeight: '800',
  },

  relatedCount: {
    color: '#556571',
    fontSize: 12,
  },

  relatedActiveText: {
    color: '#fff',
  },

  summary: {
    backgroundColor: '#eef3f6',
    borderRadius: 10,
    marginBottom: 20,
    padding: 14,
  },

  summaryClient: {
    fontSize: 18,
    fontWeight: '800',
  },

  summaryLine: {
    color: '#53636f',
    marginTop: 4,
  },

  equipmentRow: {
    alignItems: 'center',
    backgroundColor: '#fff',
    borderBottomColor: '#e2e7eb',
    borderBottomWidth: 1,
    flexDirection: 'row',
    padding: 14,
  },

  equipmentTitle: {
    fontSize: 16,
    fontWeight: '700',
  },

  equipmentMeta: {
    color: '#61717d',
    fontSize: 13,
    marginTop: 3,
  },

  good: {
    color: '#19713b',
    fontSize: 22,
    fontWeight: '900',
  },

  bad: {
    color: '#a51c30',
    fontSize: 20,
    fontWeight: '900',
  },

  reviewLine: {
    backgroundColor: '#fff',
    borderRadius: 8,
    fontSize: 17,
    fontWeight: '700',
    marginBottom: 8,
    padding: 14,
  },

  notice: {
    backgroundColor: '#fff5cf',
    borderRadius: 10,
    color: '#5f4d00',
    fontSize: 15,
    lineHeight: 22,
    padding: 14,
  },

  overlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(16,28,38,0.58)',
    justifyContent: 'flex-end',
    zIndex: 20,
  },

  overlayCard: {
    backgroundColor: '#f4f7f9',
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    maxHeight: '92%',
    overflow: 'hidden',
  },

  overlayContent: {
    paddingBottom: 38,
    paddingHorizontal: 20,
    paddingTop: 12,
  },

  overlayHandle: {
    alignSelf: 'center',
    backgroundColor: '#b8c4cc',
    borderRadius: 3,
    height: 5,
    marginBottom: 22,
    width: 46,
  },

  conditionRow: {
    flexDirection: 'row',
    gap: 10,
    marginBottom: 20,
  },

  condition: {
    alignItems: 'center',
    backgroundColor: '#e7ecef',
    borderRadius: 11,
    flex: 1,
    padding: 15,
  },

  conditionSelected: {
    backgroundColor: '#bde8c9',
  },

  conditionBadSelected: {
    backgroundColor: '#f5c6cc',
  },

  conditionText: {
    fontSize: 16,
    fontWeight: '800',
  },

  actionRow: {
    flexDirection: 'row',
    gap: 10,
  },

  cancel: {
    alignItems: 'center',
    backgroundColor: '#e3e8ec',
    borderRadius: 11,
    flex: 1,
    justifyContent: 'center',
    minHeight: 50,
  },

  save: {
    alignItems: 'center',
    backgroundColor: '#0067a8',
    borderRadius: 11,
    flex: 2,
    justifyContent: 'center',
    minHeight: 50,
  },

  delete: {
    color: '#a51c30',
    fontSize: 16,
    fontWeight: '700',
    padding: 18,
    textAlign: 'center',
  },

  busy: {
    alignItems: 'center',
    backgroundColor: '#243844',
    flexDirection: 'row',
    gap: 10,
    justifyContent: 'center',
    padding: 11,
  },

  busyText: {
    color: '#fff',
    fontWeight: '700',
  },

  dangerZone: {
    backgroundColor: '#fff1f2',
    borderColor: '#dbaeb4',
    borderRadius: 14,
    borderWidth: 1,
    marginTop: 28,
    padding: 16,
  },

  dangerTitle: {
    color: '#8d1f2d',
    fontSize: 16,
    fontWeight: '800',
    marginBottom: 7,
  },

  dangerDescription: {
    color: '#6f363d',
    lineHeight: 20,
    marginBottom: 16,
  },

  deleteWorkOrder: {
    alignItems: 'center',
    backgroundColor: '#a51c30',
    borderRadius: 11,
    justifyContent: 'center',
    minHeight: 52,
  },

  deleteWorkOrderText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '800',
  },
});
