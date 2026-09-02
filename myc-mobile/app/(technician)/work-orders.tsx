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

import { apiUrl, ApiError, readApiErrorDetail } from '@/src/api/client';
import { useAuth } from '@/src/auth/AuthProvider';
import { MobileSignatureFlow } from '@/src/components/signatures/MobileSignatureFlow';
import { LabTechnicalCapture } from '@/src/components/lab/LabTechnicalCapture';
import { LabEquipmentForm } from '@/src/components/lab/LabEquipmentForm';
import { LabClientSelector } from '@/src/components/lab/LabClientSelector';
import { ActionRow, ActionTile, AdministrativeButton, BackButton, CloseButton, DangerButton, FadeIn, PrimaryButton, SecondaryButton} from '@/src/design/primitives';
import {
  buildConfiguredEquipmentPayload,
  buildEquipmentEditRequestBody,
  describeEquipmentSummary,
  diffEquipmentEdit,
  hasEquipmentEditChanges,
  hydrateEquipmentFormValues,
  type EquipmentFormValues,
} from '@/src/services/lab-equipment-configured-payload';
import { shouldResetFormAfterSubmit } from '@/src/services/lab-client-selector';
import {
  reconcileSignatureFlowState,
  type SignatureFlowState,
  type SignaturePayload,
} from '@/src/components/signatures/signature-flow-state';
import { useNotificationSync } from '@/src/notifications/NotificationSyncProvider';
import { deriveMobileCapabilities } from '@/src/permissions/mobile-capabilities';
import { hasPermission } from '@/src/permissions/permissions';
import { affectsWorkOrders, RefreshGate } from '@/src/notifications/refresh-policy';
import {
  canDeleteLabWorkOrder,
  deleteLabWorkOrder,
  LabWorkOrderDeletionCoordinator,
} from '@/src/services/lab-work-order-deletion';
import { canSkipSignaturesAfterReopen } from '@/src/services/lab-work-order-signature-policy';
import {
  deriveLabClosureOptions,
  labClosureContextId,
  type LabClosureScope,
} from '@/src/services/lab-work-order-closure';
import {
  postLabCompletion,
  postLabSignatures,
} from '@/src/services/lab-work-order-signature-submission';
import {
  flowContextLabel,
  inferStepForStatus,
  isReceptionEditable,
  resolveStepAfterStatusUpdate,
  statusPresentation,
  type Step,
} from '@/src/services/lab-work-order-step';
import type {
  GeneralData,
  LabEquipment,
  LabClient,
  LabListItem,
  LabWorkOrder,
  LabWorkOrderGroupRequest,
} from '@/src/types/lab-work-order';

const today = () => new Date().toISOString().slice(0, 10);
const PAGE_SIZE = 25;
const emptyGeneral = (): GeneralData => ({
  lab_client_id: null,
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
type TicketDialogMode = 'reopen' | 'partial' | 'cancel' | 'reopen_direct';

function inferClosureScope(workOrder: LabWorkOrder): LabClosureScope {
  if (workOrder.signature_scope) return workOrder.signature_scope;
  if (workOrder.signature_session_id == null) return 'group';
  const activeCohortSize = workOrder.related_work_orders.filter(
    (item) => item.status !== 'completed'
      && item.signature_session_id === workOrder.signature_session_id,
  ).length;
  return workOrder.related_work_orders.length > 1 && activeCohortSize === 1
    ? 'individual'
    : 'group';
}

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
  const params = useLocalSearchParams<{ workOrderId?: string; groupRequestId?: string }>();
  const [items, setItems] = useState<LabListItem[]>([]);
  const [groupRequests, setGroupRequests] = useState<LabWorkOrderGroupRequest[]>([]);
  const [selectedGroupRequest, setSelectedGroupRequest] = useState<LabWorkOrderGroupRequest | null>(null);
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
  const [groupMode, setGroupMode] = useState<'none' | 'request' | 'direct'>('none');
  const [groupQuantity, setGroupQuantity] = useState('2');
  const [step, setStep] = useState<Step>('general');
  const [general, setGeneral] = useState<GeneralData>(emptyGeneral);
  const [workOrder, setWorkOrder] = useState<LabWorkOrder | null>(null);
  const [receptionOrders, setReceptionOrders] = useState<LabWorkOrder[]>([]);
  const [equipmentEditor, setEquipmentEditor] = useState<LabEquipment | 'new' | null>(null);
  const [signatureFlowState, setSignatureFlowState] = useState<SignatureFlowState | null>(null);
  const [signatureDrawing, setSignatureDrawing] = useState(false);
  const [closureScope, setClosureScope] = useState<LabClosureScope>('group');
  const [ticketOpen, setTicketOpen] = useState(false);
  const [ticketDialogMode, setTicketDialogMode] = useState<TicketDialogMode>('reopen');
  const [ticketReason, setTicketReason] = useState('');
  const [ticketDescription, setTicketDescription] = useState('');
  const [reopenSignaturePolicy, setReopenSignaturePolicy] = useState<'preserve' | 'invalidate'>('preserve');
  const [restoring, setRestoring] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [adminActionsOpen, setAdminActionsOpen] = useState(false);
  const itemCount = useRef(0);
  const refreshGate = useRef(new RefreshGate());
  const deletionCoordinator = useRef(new LabWorkOrderDeletionCoordinator());
  const signatureSubmitRef = useRef(false);
  const capabilities = deriveMobileCapabilities(user);

  const request = useCallback(async <T,>(path: string, init?: RequestInit): Promise<T> => {
    const headers = new Headers(init?.headers);
    if (init?.body) headers.set('Content-Type', 'application/json');
    const response = await authorizedFetch(apiUrl(path), { ...init, headers });
    if (!response.ok) {
      const detail = await readApiErrorDetail(response);
      throw new ApiError(detail.message, response.status, detail.missingFields, detail.code, detail.items);
    }
    return response.json() as Promise<T>;
  }, [authorizedFetch]);

  const receptionOrderIds = workOrder?.related_work_orders.map((item) => item.id).join(',') ?? '';

  useEffect(() => {
    if (!workOrder || step !== 'signatures' || workOrder.status !== 'draft') {
      setReceptionOrders([]);
      return;
    }
    if (workOrder.related_work_orders.length <= 1) {
      setReceptionOrders([workOrder]);
      return;
    }
    let active = true;
    Promise.all(workOrder.related_work_orders.map((item) => (
      request<LabWorkOrder>(`/mobile/v1/technician/lab-work-orders/${item.id}`)
    )))
      .then((orders) => { if (active) setReceptionOrders(orders); })
      .catch(() => { if (active) setReceptionOrders([workOrder]); });
    return () => { active = false; };
  }, [receptionOrderIds, request, step, workOrder]);

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

  useEffect(() => {
    if (!capabilities.canRequestWorkOrderGroups) return;
    request<LabWorkOrderGroupRequest[]>('/mobile/v1/technician/lab-work-orders/group-requests').then(setGroupRequests).catch(() => undefined);
  }, [capabilities.canRequestWorkOrderGroups, request]);
  const openedGroupRequestId = useRef<number | null>(null);
  useEffect(() => {
    const requestId = Number(params.groupRequestId);
    if (!requestId || !groupRequests.length || openedGroupRequestId.current === requestId) return;
    openedGroupRequestId.current = requestId;
    setSelectedGroupRequest(groupRequests.find((item) => item.id === requestId) ?? null);
  }, [groupRequests, params.groupRequestId]);

  useFocusEffect(useCallback(() => { if (user) refreshActive(); }, [refreshActive, user]));

  useEffect(() => subscribe((event) => {
    if (!affectsWorkOrders(event)) return;
    refreshActive(event.source === 'local');
    const targetId = event.work_order_id;
    if (workOrder && (!targetId || targetId === workOrder.id)) {
      request<LabWorkOrder>(`/mobile/v1/technician/lab-work-orders/${workOrder.id}`)
        .then((detail) => {
          const contextId = labClosureContextId(detail, closureScope);
          const skipPreservedSignatures = canSkipSignaturesAfterReopen(detail);
          const sameSignatureCohort = !skipPreservedSignatures
            && signatureFlowState?.rootWorkOrderId === contextId;
          setSignatureFlowState((current) => skipPreservedSignatures || current == null ? null : reconcileSignatureFlowState(current, {
            clientName: detail.contact_name ?? '',
            rootWorkOrderId: contextId,
            technicianName: user?.full_name ?? '',
          }));
          if (!sameSignatureCohort) setSignatureDrawing(false);
          setWorkOrder(detail);
          setStep((current) => resolveStepAfterStatusUpdate(current, sameSignatureCohort, detail.status));
        })
        .catch(() => undefined);
    }
  }), [closureScope, refreshActive, request, signatureFlowState?.rootWorkOrderId, subscribe, user?.full_name, workOrder]);

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

  const {
    canCreateTickets,
    canCreateWorkOrders, canRequestWorkOrderGroups, canCreateWorkOrderGroupsDirect,
    canExecuteWorkOrders,
    canCloseWorkOrders,
    canManageEquipment,
    canCaptureSignatures,
    canCaptureFieldSheets,
    canDownloadLabPackages,
  } = capabilities;
  const editable = !!workOrder && isReceptionEditable(workOrder.status) && canExecuteWorkOrders;
  const canDelete = !!user && canDeleteLabWorkOrder(user.permissions);
  const canCancel = !!user && hasPermission(user.permissions, 'lab_work_orders.cancel');
  // Cierre UX 2026-09: quien YA tiene autoridad de reapertura directa
  // (work_orders.reopen + al menos una política) ve "Reabrir orden" y la
  // ejecuta en una sola llamada -- no se le ofrece "Solicitar reapertura"
  // (eso generaría un ticket artificial para algo que puede hacer él mismo).
  const canReopenDirectly = !!user
    && hasPermission(user.permissions, 'work_orders.reopen')
    && (hasPermission(user.permissions, 'work_orders.reopen_preserve_signatures')
      || hasPermission(user.permissions, 'work_orders.reopen_invalidate_signatures'));
  const closureOptions = useMemo(
    () => workOrder ? deriveLabClosureOptions(workOrder) : null,
    [workOrder],
  );

  function startNew() {
    setGroupMode('none');
    setGeneral(emptyGeneral());
    setWorkOrder(null);
    setStep('general');
    setSignatureFlowState(null);
    setSignatureDrawing(false);
    setClosureScope('group');
    setOpen(true);
  }

  // Cierre UX 2026-09: el picker de cliente receptor de la OT reutiliza el
  // mismo LabClientSelector que ya usaba el cliente documental del equipo
  // (LabEquipmentForm) -- ya no un segundo buscador/alta duplicado aquí. La
  // importación XLSX se movió al módulo Clientes (app/(technician)/clients.tsx).
  function selectLabClient(client: LabClient) {
    setGeneral((current) => ({
      ...current,
      lab_client_id: client.id,
      client_name: client.company,
      address: client.address,
      contact_name: client.attention,
      postal_code: client.postal_code ?? current.postal_code,
      city: client.city ?? current.city,
      state_name: client.state ?? current.state_name,
    }));
  }

  function startGroupRequest() {
    startNew();
    setGroupMode('request');
  }

  function startDirectGroup() {
    startNew();
    setGroupMode('direct');
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

  // Cierre UX 2026-09: Admin con autoridad directa (canReopenDirectly) ya no
  // pasa por "Solicitar reapertura" -- ejecuta la reapertura en una sola
  // llamada (POST .../reopen), sin crear ni aprobar un ticket artificial.
  // Misma confirmación/auditoría que el flujo mediado por ticket, sólo sin
  // el paso intermedio que el usuario no necesita.
  async function reopenDirectly() {
    if (!workOrder || !ticketReason.trim() || !ticketDescription.trim()) return;
    setBusy(true);
    try {
      const detail = await request<LabWorkOrder>(
        `/mobile/v1/technician/lab-work-orders/${workOrder.id}/reopen`,
        {
          method: 'POST',
          body: JSON.stringify({
            requested_signature_policy: reopenSignaturePolicy,
            reason: `${ticketReason.trim()}: ${ticketDescription.trim()}`,
          }),
        },
      );
      setTicketOpen(false);
      setTicketReason('');
      setTicketDescription('');
      setWorkOrder(detail);
      publishLocalChange({ event_type: 'work_order.reopened', entity_type: 'work_order', entity_id: detail.id, work_order_id: detail.id });
      Alert.alert('OT reabierta', `La OT ${detail.folio} volvió a draft y puede editarse.`);
      await refresh(true);
    } catch (error) {
      Alert.alert('No fue posible reabrir la OT', error instanceof Error ? error.message : 'Intenta nuevamente');
    } finally {
      setBusy(false);
    }
  }

  async function restoreWorkOrder(target: LabWorkOrder) {
    setRestoring(true);
    try {
      const detail = await request<LabWorkOrder>(
        `/mobile/v1/technician/lab-work-orders/${target.id}/restore`, { method: 'POST' },
      );
      setWorkOrder(detail);
      publishLocalChange({ event_type: 'work_order.restored', entity_type: 'work_order', entity_id: detail.id, work_order_id: detail.id });
      Alert.alert('OT restaurada', `La OT ${detail.folio} volvió a su estado anterior a la cancelación.`);
    } catch (error) {
      Alert.alert('No fue posible restaurar la OT', error instanceof Error ? error.message : 'Intenta nuevamente');
    } finally {
      setRestoring(false);
    }
  }

  function confirmRestoreWorkOrder(target: LabWorkOrder) {
    Alert.alert(
      'Restaurar OT',
      `La OT ${target.folio} volverá exactamente al estado que tenía antes de cancelarse (${target.previous_status ? statusPresentation(target.previous_status).label : 'estado anterior'}). ¿Continuar?`,
      [
        { text: 'Cancelar', style: 'cancel' },
        { text: 'Restaurar', onPress: () => void restoreWorkOrder(target) },
      ],
    );
  }

  async function submitOperationalAction() {
    if (!workOrder || !ticketReason.trim() || !ticketDescription.trim()) return;
    if (ticketDialogMode === 'reopen') return requestReopening();
    if (ticketDialogMode === 'reopen_direct') return reopenDirectly();
    setBusy(true);
    try {
      if (ticketDialogMode === 'cancel') {
        const detail = await request<LabWorkOrder>(
          `/mobile/v1/technician/lab-work-orders/${workOrder.id}/cancel`,
          { method: 'POST', body: JSON.stringify({ reason: `${ticketReason.trim()}: ${ticketDescription.trim()}` }) },
        );
        setWorkOrder(detail);
        setStep('completed');
        Alert.alert('OT cancelada', `La OT ${detail.folio} permanece disponible para auditoría.`);
      } else {
        await request('/mobile/v1/technician/tickets/partial-close', {
          method: 'POST',
          body: JSON.stringify({
            work_order_id: workOrder.id,
            reason: ticketReason.trim(),
            description: ticketDescription.trim(),
          }),
        });
        Alert.alert('Excepción solicitada', 'Admin debe aprobarla antes del cierre parcial.');
      }
      setTicketOpen(false);
      setTicketReason('');
      setTicketDescription('');
      await refresh(true);
    } catch (error) {
      Alert.alert('No fue posible completar la acción', error instanceof Error ? error.message : 'Intenta nuevamente');
    } finally { setBusy(false); }
  }

  async function openExisting(id: number) {
    setBusy(true);
    try {
      const detail = await request<LabWorkOrder>(`/mobile/v1/technician/lab-work-orders/${id}`);
      const nextScope = inferClosureScope(detail);
      const contextId = labClosureContextId(detail, nextScope);
      const skipPreservedSignatures = canSkipSignaturesAfterReopen(detail);
      const sameSignatureCohort = !skipPreservedSignatures
        && signatureFlowState?.rootWorkOrderId === contextId;
      setClosureScope(nextScope);
      setSignatureFlowState((current) => skipPreservedSignatures || current == null ? null : reconcileSignatureFlowState(current, {
        clientName: detail.contact_name ?? '',
        rootWorkOrderId: contextId,
        technicianName: user?.full_name ?? '',
      }));
      if (!sameSignatureCohort) setSignatureDrawing(false);
      setWorkOrder(detail);
      setGeneral({
        lab_client_id: detail.lab_client_id,
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
      setStep((current) => resolveStepAfterStatusUpdate(current, sameSignatureCohort, detail.status));
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
      const path = groupMode === 'request'
        ? '/mobile/v1/technician/lab-work-orders/group-requests'
        : groupMode === 'direct'
        ? '/mobile/v1/technician/lab-work-orders/groups'
        : workOrder
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
          ...(groupMode !== 'none' ? { quantity: Number(groupQuantity) } : {}),
        }),
      });
      if (groupMode === 'request') {
        Alert.alert('Solicitud enviada', 'Los folios se asignarán únicamente cuando un administrador la apruebe.');
        setOpen(false);
        request<LabWorkOrderGroupRequest[]>('/mobile/v1/technician/lab-work-orders/group-requests').then(setGroupRequests).catch(() => undefined);
        return;
      }
      setWorkOrder(detail);
      setStep('capture');
      if (groupMode === 'direct') {
        Alert.alert('Grupo creado', `Se materializaron ${detail.related_work_orders.length} OT con folios consecutivos.`);
        setGroupMode('none');
      }
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
      const nextScope = inferClosureScope(detail);
      const contextId = labClosureContextId(detail, nextScope);
      const skipPreservedSignatures = canSkipSignaturesAfterReopen(detail);
      if (skipPreservedSignatures || (signatureFlowState && contextId !== signatureFlowState.rootWorkOrderId)) {
        setSignatureDrawing(false);
      }
      setClosureScope(nextScope);
      setSignatureFlowState((current) => skipPreservedSignatures || current == null ? null : reconcileSignatureFlowState(current, {
        clientName: detail.contact_name ?? '',
        rootWorkOrderId: contextId,
        technicianName: user?.full_name ?? '',
      }));
      setWorkOrder(detail);
      setStep(inferStepForStatus(detail.status));
    } catch (error) {
      Alert.alert('No fue posible cambiar de OT', error instanceof Error ? error.message : 'Intenta nuevamente');
    } finally {
      setBusy(false);
    }
  }

  function showEquipmentEditor(item: LabEquipment | 'new') {
    setEquipmentEditor(item);
  }

  // Fase 2 hardening (endurecimiento de consistencia): la edición completa es
  // UNA sola transacción backend (PATCH .../equipment/{id}/configured), igual
  // que el alta (Fase 2E). Mobile sigue calculando el diff sólo para decidir
  // si vale la pena hacer la llamada (hasEquipmentEditChanges) -- si algo
  // cambió, se manda la configuración completa (equipo + cliente documental +
  // servicio) y el backend aplica o revierte todo junto; ya no hay estado
  // parcial posible.
  async function saveEquipmentEdit(values: EquipmentFormValues) {
    if (!workOrder || !equipmentEditor || equipmentEditor === 'new') return;
    const initial = hydrateEquipmentFormValues(equipmentEditor);
    const changes = diffEquipmentEdit(initial, values);
    if (!hasEquipmentEditChanges(changes)) {
      setEquipmentEditor(null);
      return;
    }
    setBusy(true);
    try {
      const body = buildEquipmentEditRequestBody(values, workOrder.edit_version);
      const detail = await request<LabWorkOrder>(
        `/mobile/v1/technician/lab-work-orders/${workOrder.id}/equipment/${equipmentEditor.id}/configured`,
        { method: 'PATCH', body: JSON.stringify(body) },
      );
      setWorkOrder(detail);
      if (shouldResetFormAfterSubmit('success')) {
        setEquipmentEditor(null);
      }
      publishLocalChange({ event_type: 'work_order.updated', entity_type: 'work_order', entity_id: detail.id, work_order_id: detail.id });
    } catch (error) {
      // shouldResetFormAfterSubmit('error') === false: el modal NO se cierra
      // ni se limpia. Al ser una sola transacción, un 409 (folio ya
      // reservado, etc.) garantiza que NADA de la edición quedó a medias --
      // ni datos básicos ni cliente documental.
      Alert.alert('No fue posible guardar los cambios', error instanceof Error ? error.message : 'Revisa los datos');
    } finally {
      setBusy(false);
    }
  }

  // Fase 2E/2F: alta integrada -- equipo + cliente documental + servicio/folio
  // como una sola operación atómica (POST .../equipment/configured). Reutiliza
  // el mismo endpoint que backend expone para no duplicar la orquestación acá.
  async function saveConfiguredEquipment(values: EquipmentFormValues) {
    if (!workOrder) return;
    setBusy(true);
    try {
      const payload = buildConfiguredEquipmentPayload(values.equipment, values.documentaryClient, values.service);
      const detail = await request<LabWorkOrder>(
        `/mobile/v1/technician/lab-work-orders/${workOrder.id}/equipment/configured`,
        { method: 'POST', body: JSON.stringify(payload) },
      );
      setWorkOrder(detail);
      setEquipmentEditor(null);
      publishLocalChange({ event_type: detail.signature_required ? 'ticket.signature_required' : 'work_order.updated', entity_type: 'work_order', entity_id: detail.id, work_order_id: detail.id });
    } catch (error) {
      // El formulario NO se limpia ni se cierra en error: shouldResetFormAfterSubmit('error') === false.
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

  function openSignatureFlow(scope: LabClosureScope) {
    if (!workOrder) {
      Alert.alert('No hay un grupo activo', 'Abre nuevamente la orden antes de capturar firmas.');
      return;
    }
    const contextId = labClosureContextId(workOrder, scope);
    setClosureScope(scope);
    setSignatureFlowState(() => reconcileSignatureFlowState(null, {
      clientName: workOrder.contact_name ?? '',
      rootWorkOrderId: contextId,
      technicianName: user?.full_name ?? '',
    }));
    setStep('signatures');
  }

  async function applySignatures(payload: SignaturePayload, capturedContextId: number) {
    if (signatureSubmitRef.current) throw new Error('Las firmas ya se están guardando.');
    if (!workOrder || labClosureContextId(workOrder, closureScope) !== capturedContextId) {
      setSignatureFlowState(null);
      setSignatureDrawing(false);
      throw new Error('El grupo activo cambió. Captura nuevamente las firmas.');
    }
    signatureSubmitRef.current = true;
    setBusy(true);
    const signedAt = new Date().toISOString();
    try {
      const detail = await postLabSignatures({
        payload,
        request,
        scope: closureScope,
        signedAt,
        workOrder,
      });
      // No se limpia signatureFlowState aquí -- MobileSignatureFlow muestra
      // su propia confirmación breve con esta respuesta autoritativa y
      // avisa vía onComplete cuándo desmontarse (evita que el flujo
      // desaparezca de golpe apenas responde el backend).
      setWorkOrder(detail);
      publishLocalChange({ event_type: 'work_order.signatures_updated', entity_type: 'work_order', entity_id: detail.id, work_order_id: detail.id });
    } catch (error) {
      throw new Error(error instanceof Error ? error.message : 'No fue posible aplicar las firmas. Intenta nuevamente.');
    } finally {
      signatureSubmitRef.current = false;
      setBusy(false);
    }
  }

  // Cierre UX 2026-09: cerrar con hojas en borrador ya no exige que el
  // técnico las complete manualmente antes -- el backend detecta los
  // borradores, pide confirmación (LAB_DRAFT_SHEETS_REQUIRE_CONFIRMATION) y,
  // si el usuario confirma, valida y completa TODAS en la misma llamada
  // atómica (confirm_draft_completion=true). Si alguna no pasa validación
  // (LAB_DRAFT_SHEETS_INVALID), no se completa ni se cierra nada -- se
  // muestran los blockers exactos y la OT sigue abierta.
  async function completeClosure(scope: LabClosureScope = closureScope, confirmDraftCompletion = false) {
    if (!workOrder) return;
    setBusy(true);
    try {
      const detail = await postLabCompletion({ confirmDraftCompletion, request, scope, workOrder });
      setWorkOrder(detail);
      setStep('completed');
      await refresh();
      publishLocalChange({ event_type: 'work_order.completed', entity_type: 'work_order', entity_id: detail.id, work_order_id: detail.id });
    } catch (error) {
      if (error instanceof ApiError && error.code === 'LAB_DRAFT_SHEETS_REQUIRE_CONFIRMATION') {
        const count = error.items?.length ?? 0;
        Alert.alert(
          'Hojas en borrador',
          `Esta OT contiene ${count} hoja${count === 1 ? '' : 's'} guardada${count === 1 ? '' : 's'} como borrador.\nSi continúas, el sistema validará y completará las hojas pendientes antes de cerrar la orden.\n¿Deseas continuar?`,
          [
            { text: 'No', style: 'cancel' },
            { text: 'Completar y cerrar', onPress: () => { void completeClosure(scope, true); } },
          ],
        );
        return;
      }
      if (error instanceof ApiError && error.code === 'LAB_DRAFT_SHEETS_INVALID') {
        const items = error.items ?? [];
        const bullets = items.map((item) => {
          const equipmentLabel = typeof item.equipment === 'string' ? item.equipment : `equipo #${item.equipment_id}`;
          const missing = Array.isArray(item.missing_fields) ? item.missing_fields.join(', ') : 'datos requeridos';
          return `• ${equipmentLabel}: falta ${missing}`;
        }).join('\n');
        Alert.alert('No se puede cerrar todavía', `Completa estas hojas antes de cerrar:\n${bullets}`);
        return;
      }
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

  async function downloadPackage(action: 'print' | 'share', group = false) {
    if (!workOrder || !session) return;
    setBusy(true);
    try {
      const uri = `${FileSystem.cacheDirectory}PAQUETE-${group ? 'GRUPO-' : ''}${workOrder.folio}.pdf`;
      const result = await FileSystem.downloadAsync(
        apiUrl(`/mobile/v1/technician/lab-work-orders/${workOrder.id}/package?group=${group}`),
        uri,
        { headers: { Authorization: `Bearer ${session.access_token}` } },
      );
      if (result.status !== 200) throw new Error(`No fue posible descargar el paquete (${result.status})`);
      if (action === 'print') await Print.printAsync({ uri: result.uri });
      else if (await Sharing.isAvailableAsync()) await Sharing.shareAsync(result.uri, { UTI: 'com.adobe.pdf', mimeType: 'application/pdf' });
    } catch (error) {
      Alert.alert('No fue posible abrir el paquete', error instanceof Error ? error.message : 'Intenta nuevamente');
    } finally { setBusy(false); }
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
        <BackButton />
        <Text style={styles.title}>Órdenes de Trabajo</Text>
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

      <View style={styles.screenActions}>
        {canCreateWorkOrders && (
          <ActionTile
            icon="file-document-plus-outline"
            label="Generar orden"
            onPress={startNew}
            tone="primary"
          />
        )}

        {canCreateWorkOrderGroupsDirect && (
          <ActionTile
            icon="folder-multiple-plus-outline"
            label="Generar grupo"
            onPress={startDirectGroup}
            tone="secondary"
          />
        )}

        {canRequestWorkOrderGroups && (
          <ActionTile
            icon="send-outline"
            label="Solicitar grupo"
            onPress={startGroupRequest}
            tone="administrative"
          />
        )}
      </View>
      {canRequestWorkOrderGroups && groupRequests.length > 0 && <View style={styles.filters}><Text style={styles.filterLabel}>Mis solicitudes de grupo</Text>{groupRequests.map((item) => <Pressable key={item.id} onPress={() => setSelectedGroupRequest(item)}><Text style={styles.status}>#{item.id} · {item.quantity} OT · {item.status}{item.folios.length ? ` · folios ${item.folios.join(', ')}` : ' · sin folios'}</Text></Pressable>)}</View>}
      {loading ? <ActivityIndicator style={styles.loader} /> : (
        <ScrollView contentContainerStyle={styles.list} refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => refreshActive(true)} />}>
          {!!listError && (
            <View style={styles.errorState}>
              <Text style={styles.errorText}>{listError}</Text>
              <Pressable onPress={() => refresh(true)}><Text style={styles.retry}>Reintentar</Text></Pressable>
            </View>
          )}
          {items.map((item) => {
            const presentation = statusPresentation(item.status);
            return (
            <Pressable key={item.id} style={[styles.card, styles.statusStripe, { borderLeftColor: presentation.color }]} onPress={() => openExisting(item.id)}>
              <View style={styles.cardContent}><Text style={styles.folio}>OT {item.folio}</Text><Text ellipsizeMode="tail" numberOfLines={2} style={styles.client}>{item.client_name}</Text></View>
              <View style={styles.cardRight}><Text style={styles.count}>{item.completed_equipment_count}/{item.equipment_count} equipos</Text><Text style={styles.status}>{presentation.label}</Text></View>
            </Pressable>
          );})}
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
            <View><Text style={styles.modalTitle}>OT LAB {workOrder ? `· ${workOrder.folio}` : ''}</Text><Text style={styles.modalHint}>{flowContextLabel(step, workOrder?.status)}</Text></View>
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
                <FadeIn transitionKey={step}>
                  <View style={styles.sectionIntro}>
                    <Text style={styles.sectionEyebrow}>{workOrder ? `REVISIÓN ${workOrder.revision_number}` : 'NUEVA ORDEN'}</Text>
                    <Text style={styles.sectionTitle}>{workOrder ? 'Editar datos generales' : 'Datos generales'}</Text>
                    <Text style={styles.sectionDescription}>Captura esta información una sola vez. Las OT adicionales la heredarán automáticamente.</Text>
                  </View>
                  <FormSection title="Servicio y cliente">
                    {groupMode !== 'none' && <Field label="Cantidad de OT (1–50)" required keyboardType="phone-pad" value={groupQuantity} onChangeText={setGroupQuantity} />}
                    <Field label="Fecha de recepción (AAAA-MM-DD)" required value={general.reception_date} onChangeText={(value) => setGeneral({ ...general, reception_date: value })} />
                    <Field label="Fecha de salida (AAAA-MM-DD)" required value={general.departure_date} onChangeText={(value) => setGeneral({ ...general, departure_date: value })} />
                    <Text style={styles.fieldLabel}>Cliente *</Text>
                    {general.lab_client_id ? (
                      <View style={styles.selectedClient}>
                        <Text style={styles.clientChoiceTitle}>{general.client_name}</Text>
                        <Text style={styles.clientChoiceMeta}>{general.address}</Text>
                        <Pressable onPress={() => setGeneral({ ...general, lab_client_id: null, client_name: '' })}>
                          <Text style={styles.change}>Cambiar</Text>
                        </Pressable>
                      </View>
                    ) : (
                      <LabClientSelector request={request} onSelect={selectLabClient} />
                    )}
                    <Field label="Atención / contacto" value={general.contact_name} onChangeText={(value) => setGeneral({ ...general, contact_name: value })} />
                  </FormSection>
                  <FormSection title="Ubicación y referencia">
                    {!general.lab_client_id && <Field label="Domicilio" multiline value={general.address} onChangeText={(value) => setGeneral({ ...general, address: value })} />}
                    <Field label="C.P." value={general.postal_code} onChangeText={(value) => setGeneral({ ...general, postal_code: value })} />
                    <Field label="Ciudad" value={general.city} onChangeText={(value) => setGeneral({ ...general, city: value })} />
                    <Field label="Estado" value={general.state_name} onChangeText={(value) => setGeneral({ ...general, state_name: value })} />
                    <Field label="Orden de compra / cotización" value={general.purchase_order} onChangeText={(value) => setGeneral({ ...general, purchase_order: value })} />
                    <Field label="Observaciones" multiline value={general.notes} onChangeText={(value) => setGeneral({ ...general, notes: value })} />
                  </FormSection>
                  <Pressable disabled={!general.lab_client_id || busy || (groupMode !== 'none' && (Number(groupQuantity) < 1 || Number(groupQuantity) > 50))} style={[styles.primary, (!general.lab_client_id || busy) && styles.disabled]} onPress={createWorkOrder}><Text style={styles.primaryText}>{groupMode === 'request' ? 'Enviar solicitud sin reservar folios' : groupMode === 'direct' ? 'Crear grupo y asignar folios' : workOrder ? 'Guardar cambios' : 'Crear OT y capturar equipos'}</Text></Pressable>
                </FadeIn>
              )}

              {workOrder && step !== 'general' && (
                <>
                  <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.related}>
                    {workOrder.related_work_orders.map((item) => (
                      <Pressable key={item.id} onPress={() => selectRelated(item.id)} style={[styles.relatedChip, item.id === workOrder.id && styles.relatedActive]}>
                        <Text style={[styles.relatedFolio, item.id === workOrder.id && styles.relatedActiveText]}>{item.folio}</Text>
                        <Text style={[styles.relatedCount, item.id === workOrder.id && styles.relatedActiveText]}>{item.equipment_count}/10</Text>
                        <Text style={[styles.relatedStatus, item.id === workOrder.id && styles.relatedActiveText]}>{statusPresentation(item.status).label}</Text>
                      </Pressable>
                    ))}
                  </ScrollView>
                  <View style={styles.summary}><Text style={styles.summaryClient}>{workOrder.client_name}</Text><Text style={styles.summaryLine}>{workOrder.reception_date} → {workOrder.departure_date}</Text><Text style={styles.summaryLine}>{workOrder.address}</Text></View>
                </>
              )}

              {workOrder && step === 'capture' && (
                <FadeIn transitionKey={step}>
                  {!!workOrder.reopen_ticket_id && editable && (
                    <Pressable style={styles.secondary} onPress={() => setStep('general')}>
                      <Text style={styles.secondaryText}>Editar datos generales</Text>
                    </Pressable>
                  )}
                  <View style={styles.sectionRow}><Text style={styles.sectionTitle}>Equipos</Text><Text style={styles.counter}>{workOrder.equipment.length}/10</Text></View>
                  {workOrder.equipment.map((item) => {
                    const summary = describeEquipmentSummary(item, workOrder.client_name);
                    return (
                      <Pressable key={item.id} style={styles.equipmentRow} onPress={() => editable && canManageEquipment && showEquipmentEditor(item)}>
                        <View style={styles.flex}>
                          <Text style={styles.equipmentTitle}>{item.position}. {item.instrument}</Text>
                          <Text style={styles.equipmentMeta}>{item.brand} · {item.identification} · {item.serial_number}</Text>
                          <Text style={styles.equipmentMeta}>{summary.client} · {summary.service}{summary.linkedCompany ? ` (${summary.linkedCompany})` : ''} · Folio: {summary.folio}</Text>
                        </View>
                        <Text style={item.is_good_condition ? styles.good : styles.bad}>{item.is_good_condition ? '✓' : 'X'}</Text>
                      </Pressable>
                    );
                  })}
                  {!workOrder.equipment.length && <Text style={styles.empty}>Aún no hay equipos.</Text>}
                  {editable && canManageEquipment && workOrder.equipment.length < 10 && <Pressable style={styles.secondary} onPress={() => showEquipmentEditor('new')}><Text style={styles.secondaryText}>+ Añadir equipo</Text></Pressable>}
                  {editable && canCreateWorkOrders && workOrder.equipment.length === 10 && <Pressable style={styles.secondary} onPress={addAdditional}><Text style={styles.secondaryText}>Asignar OT extra</Text></Pressable>}
                  {/* Fase 3: la recepción se firma ANTES de la captura técnica.
                      Una OT reabierta con "preserve" ya conserva una firma de
                      recepción válida (canSkipSignaturesAfterReopen) -- no debe
                      pedirse otra, así que salta directo a captura técnica. */}
                  <Pressable
                    disabled={!workOrder.equipment.length}
                    style={[styles.primary, !workOrder.equipment.length && styles.disabled]}
                    onPress={() => setStep(canSkipSignaturesAfterReopen(workOrder) ? 'technical' : 'signatures')}
                  >
                    <Text style={styles.primaryText}>
                      {canSkipSignaturesAfterReopen(workOrder) ? 'Continuar proceso' : 'Continuar a recepción de equipos'}
                    </Text>
                  </Pressable>
                </FadeIn>
              )}

              {workOrder && step === 'technical' && (
                <FadeIn transitionKey={step}>
                  <View style={styles.sectionIntro}>
                    <Text style={styles.sectionEyebrow}>CAPTURA TÉCNICA</Text>
                    <Text style={styles.sectionTitle}>Servicio, folio y hoja por equipo</Text>
                  </View>
                  <LabTechnicalCapture
                    accessToken={session?.access_token ?? ''}
                    canCapture={canCaptureFieldSheets}
                    external={user.actor_type === 'client'}
                    onUpdated={setWorkOrder}
                    request={request}
                    workOrder={workOrder}
                  />
                  {editable && <Pressable style={styles.secondary} onPress={() => setStep('capture')}><Text style={styles.secondaryText}>Volver a equipos</Text></Pressable>}
                  {canExecuteWorkOrders && <Pressable style={styles.primary} onPress={() => setStep('review')}><Text style={styles.primaryText}>Continuar a cierre</Text></Pressable>}
                  {canDownloadLabPackages && <Pressable style={styles.secondary} onPress={() => downloadPackage('share')}><Text style={styles.secondaryText}>Descargar paquete disponible</Text></Pressable>}
                </FadeIn>
              )}

              {/* Fase 3: la recepción ya quedó firmada antes de este paso -- el
                  cierre sólo confirma que el trabajo técnico terminó, nunca
                  vuelve a pedir firma (ver step 'signatures' para eso). */}
              {workOrder && step === 'review' && (
                <>
                  <Text style={styles.sectionTitle}>Confirmar cierre</Text>
                  {workOrder.related_work_orders.map((item) => <Text key={item.id} style={styles.reviewLine}>OT {item.folio}: {item.equipment_count} equipo(s) · {item.status === 'completed' ? 'cerrada' : item.status === 'ready_to_close' ? 'lista para cerrar' : item.status === 'ready_for_signatures' ? 'firmada' : 'en captura'}</Text>)}
                  <Text style={styles.notice}>El grupo conserva siempre sus folios y parentesco. El cierre aplica únicamente a la OT o cohorte elegida al firmar la recepción.</Text>
                  <Pressable style={styles.secondary} onPress={() => setStep('technical')}><Text style={styles.secondaryText}>Revisar captura técnica</Text></Pressable>
                  {canCreateTickets && closureOptions?.hasEligiblePartialCloseCohort && <Pressable style={styles.secondary} onPress={() => { setTicketDialogMode('partial'); setTicketOpen(true); }}><Text style={styles.secondaryText}>Solicitar excepción de cierre parcial</Text></Pressable>}
                  {canCloseWorkOrders && canSkipSignaturesAfterReopen(workOrder) ? (
                    <Pressable style={styles.primary} onPress={() => completeClosure(closureScope)}><Text style={styles.primaryText}>Cerrar OT individual reabierta</Text></Pressable>
                  ) : canCloseWorkOrders ? (
                    <Pressable style={styles.primary} onPress={() => completeClosure(closureScope)}>
                      <Text style={styles.primaryText}>
                        {closureScope === 'group' && closureOptions?.hasHistoricalSiblings
                          ? `Cerrar grupo activo (${closureOptions.activeCohortSize} OT)`
                          : `Cerrar OT ${workOrder.folio}`}
                      </Text>
                    </Pressable>
                  ) : <Text style={styles.notice}>Tu perfil permite consultar esta OT, pero no cerrarla.</Text>}
                </>
              )}

              {/* Fase 3: recepción de equipos + firma -- ocurre ANTES de la
                  captura técnica. La firma representa que MYC y el cliente
                  aceptan los equipos y condiciones recibidos, no que el
                  trabajo técnico terminó. */}
              {workOrder && step === 'signatures' && workOrder.status === 'draft' && (
                <FadeIn transitionKey={step}>
                {signatureFlowState == null ? (
                  <>
                    <Text style={styles.sectionTitle}>RECEPCIÓN DE EQUIPOS</Text>
                    {(receptionOrders.length ? receptionOrders : [workOrder]).map((receptionOrder) => (
                      <View key={receptionOrder.id} style={styles.summary}>
                        <Text style={styles.summaryLine}>OT {receptionOrder.folio}</Text>
                        {receptionOrder.equipment.map((item) => {
                          const summary = describeEquipmentSummary(item, receptionOrder.client_name);
                          return (
                            <View key={item.id} style={styles.equipmentRow}>
                              <View style={styles.flex}>
                                <Text style={styles.equipmentTitle}>{item.position}. {item.instrument}</Text>
                                <Text style={styles.equipmentMeta}>{item.brand} · {item.identification} · {item.serial_number}</Text>
                                <Text style={styles.equipmentMeta}>{summary.client} · {summary.service}{summary.linkedCompany ? ` (${summary.linkedCompany})` : ''}</Text>
                                <Text style={styles.equipmentMeta}>Folio: {summary.folio}</Text>
                              </View>
                            </View>
                          );
                        })}
                        {!receptionOrder.equipment.length && <Text style={styles.empty}>Aún no hay equipos.</Text>}
                      </View>
                    ))}
                    <Pressable style={styles.secondary} onPress={() => setStep('capture')}><Text style={styles.secondaryText}>Volver a equipos</Text></Pressable>
                    {canCaptureSignatures ? (
                      <>
                        {closureOptions?.hasHistoricalSiblings && (
                          <>
                            <Pressable
                              disabled={!closureOptions.canFinalizeGroup}
                              onPress={() => openSignatureFlow('group')}
                              style={[styles.primary, !closureOptions.canFinalizeGroup && styles.disabled]}
                            >
                              <Text style={styles.primaryText}>Firmar recepción del grupo ({closureOptions.groupParticipantCount} OT)</Text>
                            </Pressable>
                            {!!closureOptions.groupMissingEquipmentCount && (
                              <Text style={styles.notice}>{closureOptions.groupMissingEquipmentCount} OT todavía no tienen equipos; la firma grupal no está disponible.</Text>
                            )}
                            <Pressable
                              disabled={!closureOptions.canFinalizeIndividual}
                              onPress={() => openSignatureFlow('individual')}
                              style={[styles.secondary, !closureOptions.canFinalizeIndividual && styles.disabled]}
                            >
                              <Text style={styles.secondaryText}>Firmar sólo OT {workOrder.folio}</Text>
                            </Pressable>
                          </>
                        )}
                        {!closureOptions?.hasHistoricalSiblings && (
                          <Pressable style={styles.primary} onPress={() => openSignatureFlow('group')}><Text style={styles.primaryText}>Continuar a firmas</Text></Pressable>
                        )}
                      </>
                    ) : <Text style={styles.notice}>Tu perfil permite consultar esta OT, pero no capturar firmas.</Text>}
                  </>
                ) : signatureFlowState.rootWorkOrderId === labClosureContextId(workOrder, closureScope) ? (
                  <MobileSignatureFlow
                    currentContextId={labClosureContextId(workOrder, closureScope)}
                    key={signatureFlowState.rootWorkOrderId}
                    onComplete={() => { setSignatureFlowState(null); setSignatureDrawing(false); }}
                    onDrawingChange={setSignatureDrawing}
                    onStateChange={setSignatureFlowState}
                    onSubmit={applySignatures}
                    state={signatureFlowState}
                  />
                ) : (
                  <View style={styles.errorState}>
                    <Text style={styles.errorText}>La captura anterior se descartó porque cambió el contexto de recepción.</Text>
                    <Pressable onPress={() => setStep('capture')}><Text style={styles.retry}>Volver a equipos</Text></Pressable>
                  </View>
                )}
                </FadeIn>
              )}

              {/* Legacy: OT firmada bajo el flujo anterior a Fase 3 (recepción
                  y cierre técnico en un solo paso). Se conserva tal cual para
                  no falsear historicidad -- el nuevo flujo nunca produce este
                  status. */}
              {workOrder && step === 'signatures' && workOrder.status === 'ready_for_signatures' && (
                <FadeIn transitionKey={step}>
                {closureOptions?.isSingleOtSignatureSession !== false ? (
                  <>
                    <Text style={styles.sectionTitle}>Firma completada</Text>
                    {canCloseWorkOrders && <Pressable style={styles.primary} onPress={() => completeClosure(closureScope)}><Text style={styles.primaryText}>Cerrar y generar PDFs</Text></Pressable>}
                  </>
                ) : (
                  <>
                    <Text style={styles.sectionTitle}>OT individual firmada</Text>
                    <Text style={styles.notice}>Esta sesión quedó vinculada a {closureOptions.activeCohortSize} OT. Las demás OT del grupo histórico conservan su estado y podrán cerrarse después.</Text>
                    {canCloseWorkOrders && <Pressable style={styles.primary} onPress={() => completeClosure(closureScope)}><Text style={styles.primaryText}>Cierre individual y generar PDF</Text></Pressable>}
                  </>
                )}
                </FadeIn>
              )}

              {/* Fase 3: confirmación inmediatamente después de firmar la
                  recepción -- la sección administrativa (equipo/servicio/
                  cliente) ya quedó de sólo lectura (ver `editable`, gateado
                  por status === 'draft'; backend también lo bloquea). */}
              {workOrder && step === 'signatures' && workOrder.status !== 'draft' && workOrder.status !== 'ready_for_signatures' && (
                <FadeIn transitionKey={step}>
                  <Text style={styles.sectionTitle}>Recepción firmada</Text>
                  <Text style={styles.notice}>Técnico y cliente confirmaron los equipos y condiciones recibidos. La recepción queda de sólo lectura; continúa a la captura técnica.</Text>
                  <Pressable style={styles.primary} onPress={() => setStep('technical')}><Text style={styles.primaryText}>Continuar a captura técnica</Text></Pressable>
                </FadeIn>
              )}

              {workOrder && step === 'completed' && (
                <>
                  <Text style={styles.sectionTitle}>OT {workOrder.folio} · {statusPresentation(workOrder.status).label}</Text>
                  <Text style={styles.notice}>Selecciona arriba cada folio para abrir, imprimir o compartir su PDF individual.</Text>
                  {workOrder.status !== 'cancelled' && <Pressable style={styles.primary} onPress={() => downloadPdf('print')}><Text style={styles.primaryText}>Ver / imprimir OT {workOrder.folio}</Text></Pressable>}
                  {workOrder.status !== 'cancelled' && <Pressable style={styles.secondary} onPress={() => downloadPdf('share')}><Text style={styles.secondaryText}>Compartir OT {workOrder.folio}</Text></Pressable>}
                  {canDownloadLabPackages && <Pressable style={styles.secondary} onPress={() => downloadPackage('share', false)}><Text style={styles.secondaryText}>Descargar paquete de esta OT</Text></Pressable>}
                  {canDownloadLabPackages && workOrder.related_work_orders.length > 1 && <Pressable style={styles.secondary} onPress={() => downloadPackage('share', true)}><Text style={styles.secondaryText}>Descargar paquete del grupo</Text></Pressable>}
                  {workOrder.status !== 'cancelled' && (
                    canReopenDirectly ? (
                      <Pressable style={styles.secondary} onPress={() => { setTicketDialogMode('reopen_direct'); setReopenSignaturePolicy('preserve'); setTicketOpen(true); }}><Text style={styles.secondaryText}>Reabrir orden</Text></Pressable>
                    ) : canCreateTickets ? (
                      <Pressable style={styles.secondary} onPress={() => { setTicketDialogMode('reopen'); setTicketOpen(true); }}><Text style={styles.secondaryText}>Solicitar reapertura</Text></Pressable>
                    ) : null
                  )}
                  {workOrder.status === 'cancelled' && canCancel && !!workOrder.previous_status && (
                    <Pressable disabled={restoring} style={styles.secondary} onPress={() => confirmRestoreWorkOrder(workOrder)}>
                      {restoring ? <ActivityIndicator /> : <Text style={styles.secondaryText}>Restaurar OT</Text>}
                    </Pressable>
                  )}
                </>
              )}

              {workOrder && canDelete && (
                <View style={styles.dangerZone}>
                  <Pressable onPress={() => setAdminActionsOpen((value) => !value)}>
                    <Text style={styles.dangerTitle}>Acciones administrativas {adminActionsOpen ? '▾' : '▸'}</Text>
                  </Pressable>
                  {adminActionsOpen && <>
                    {canCancel && workOrder.status !== 'cancelled' && <Pressable style={styles.cancelWorkOrder} onPress={() => { setTicketDialogMode('cancel'); setTicketOpen(true); }}><Text style={styles.cancelWorkOrderText}>Cancelar y conservar OT</Text></Pressable>}
                    <Text style={styles.dangerDescription}>La eliminación retira únicamente esta OT LAB y conserva los recursos compartidos por sus OT hermanas.</Text>
                    <Pressable
                      disabled={busy || deleting}
                      onPress={() => confirmWorkOrderDeletion(workOrder)}
                      style={[styles.deleteWorkOrder, (busy || deleting) && styles.disabled]}
                    >
                      <Text style={styles.deleteWorkOrderText}>Eliminar orden de trabajo</Text>
                    </Pressable>
                  </>}
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
                  <FadeIn transitionKey={equipmentEditor === 'new' ? 'new' : equipmentEditor?.id}>
                  {equipmentEditor === 'new' ? (
                    <>
                      <Text style={styles.sectionTitle}>Añadir equipo</Text>
                      <Text style={styles.sectionDescription}>Datos del equipo, cliente documental y servicio en una sola operación.</Text>
                      <LabEquipmentForm
                        busy={busy}
                        mode="create"
                        onCancel={() => setEquipmentEditor(null)}
                        onSubmit={saveConfiguredEquipment}
                        request={request}
                        workOrderClientName={workOrder?.client_name ?? ''}
                      />
                    </>
                  ) : equipmentEditor ? (
                    <>
                      <Text style={styles.sectionTitle}>Editar equipo</Text>
                      <Text style={styles.sectionDescription}>Datos del equipo, cliente documental y servicio. El folio se muestra de referencia y no se edita aquí.</Text>
                      <LabEquipmentForm
                        busy={busy}
                        folioDisplay={describeEquipmentSummary(equipmentEditor, workOrder?.client_name ?? '').folio}
                        initialValues={hydrateEquipmentFormValues(equipmentEditor)}
                        mode="edit"
                        onCancel={() => setEquipmentEditor(null)}
                        onSubmit={saveEquipmentEdit}
                        request={request}
                        workOrderClientName={workOrder?.client_name ?? ''}
                      />
                      <Pressable onPress={removeEquipment}><Text style={styles.delete}>Eliminar equipo</Text></Pressable>
                    </>
                  ) : null}
                  </FadeIn>
                </ScrollView>
              </KeyboardAvoidingView>
            </View>
          )}
          {ticketOpen && (canCreateTickets || (ticketDialogMode === 'cancel' && canCancel) || (ticketDialogMode === 'reopen_direct' && canReopenDirectly)) && (
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
                  <Text style={styles.sectionEyebrow}>{ticketDialogMode === 'cancel' ? 'CANCELACIÓN ADMINISTRATIVA' : ticketDialogMode === 'partial' ? 'EXCEPCIÓN DE CIERRE' : ticketDialogMode === 'reopen_direct' ? 'REAPERTURA ADMINISTRATIVA' : 'TICKET DE REAPERTURA'}</Text>
                  <Text style={styles.sectionTitle}>{ticketDialogMode === 'cancel' ? 'Cancelar sin borrar la orden' : ticketDialogMode === 'partial' ? 'Solicitar cierre parcial' : ticketDialogMode === 'reopen_direct' ? 'Reabrir esta OT' : '¿Por qué necesitas modificar esta orden?'}</Text>
                  <Text style={styles.sectionDescription}>{ticketDialogMode === 'cancel' ? 'El folio no se reutiliza y la OT permanece auditable.' : ticketDialogMode === 'reopen_direct' ? 'Tienes autoridad directa: se reabre de inmediato, sin ticket.' : 'La solicitud requiere resolución de Admin.'}</Text>
                  {ticketDialogMode === 'reopen_direct' && (
                    <View style={styles.row}>
                      <Pressable onPress={() => setReopenSignaturePolicy('preserve')} style={[styles.choice, reopenSignaturePolicy === 'preserve' && styles.choiceActive]}><Text>Conservar firma</Text></Pressable>
                      <Pressable onPress={() => setReopenSignaturePolicy('invalidate')} style={[styles.choice, reopenSignaturePolicy === 'invalidate' && styles.choiceActive]}><Text>Requerir nueva firma</Text></Pressable>
                    </View>
                  )}
                  <Field label="Motivo" required value={ticketReason} onChangeText={setTicketReason} />
                  <Field label="Descripción" required multiline value={ticketDescription} onChangeText={setTicketDescription} />
                  <View style={styles.actionRow}>
                    <Pressable style={styles.cancel} onPress={() => setTicketOpen(false)}><Text>Cancelar</Text></Pressable>
                    <Pressable disabled={!ticketReason.trim() || !ticketDescription.trim()} style={styles.save} onPress={submitOperationalAction}><Text style={styles.primaryText}>{ticketDialogMode === 'cancel' ? 'Cancelar OT' : ticketDialogMode === 'reopen_direct' ? 'Reabrir orden' : 'Enviar solicitud'}</Text></Pressable>
                  </View>
                </ScrollView>
              </KeyboardAvoidingView>
            </View>
          )}
        </SafeAreaView>
        </SafeAreaProvider>
      </Modal>
      <Modal
        animationType="fade"
        onRequestClose={() => setSelectedGroupRequest(null)}
        transparent
        visible={Boolean(selectedGroupRequest)}
      >
        <View style={styles.requestOverlay}>
          <View style={styles.requestDialog}>
            <View style={styles.requestHeader}>
              <View style={styles.requestHeaderCopy}>
                <Text style={styles.requestEyebrow}>GRUPO DE ÓRDENES</Text>
                <Text style={styles.requestTitle}>
                  Solicitud #{selectedGroupRequest?.id}
                </Text>
                <Text style={styles.requestClient}>
                  {selectedGroupRequest?.client_name}
                </Text>
              </View>

              <View
                style={[
                  styles.requestStatusBadge,
                  selectedGroupRequest?.status === 'approved' &&
                    styles.requestStatusApproved,
                  selectedGroupRequest?.status === 'rejected' &&
                    styles.requestStatusRejected,
                  selectedGroupRequest?.status === 'in_review' &&
                    styles.requestStatusReview,
                ]}
              >
                <Text style={styles.requestStatusText}>
                  {selectedGroupRequest?.status === 'pending'
                    ? 'Pendiente'
                    : selectedGroupRequest?.status === 'in_review'
                      ? 'En revisión'
                      : selectedGroupRequest?.status === 'approved'
                        ? 'Aprobada'
                        : selectedGroupRequest?.status === 'rejected'
                          ? 'Rechazada'
                          : selectedGroupRequest?.status}
                </Text>
              </View>
            </View>

            <View style={styles.requestSummary}>
              <View style={styles.requestSummaryItem}>
                <Text style={styles.requestSummaryLabel}>Órdenes solicitadas</Text>
                <Text style={styles.requestSummaryValue}>
                  {selectedGroupRequest?.quantity ?? 0}
                </Text>
              </View>

              <View style={styles.requestSummaryDivider} />

              <View style={styles.requestSummaryItem}>
                <Text style={styles.requestSummaryLabel}>Estado</Text>
                <Text style={styles.requestSummaryValueSmall}>
                  {selectedGroupRequest?.status === 'pending'
                    ? 'Pendiente'
                    : selectedGroupRequest?.status === 'in_review'
                      ? 'En revisión'
                      : selectedGroupRequest?.status === 'approved'
                        ? 'Aprobada'
                        : selectedGroupRequest?.status === 'rejected'
                          ? 'Rechazada'
                          : selectedGroupRequest?.status}
                </Text>
              </View>
            </View>

            <View style={styles.requestSection}>
              <Text style={styles.requestSectionLabel}>Folios asignados</Text>

              {selectedGroupRequest?.folios.length ? (
                <View style={styles.requestFolios}>
                  {selectedGroupRequest.folios.map((folio) => (
                    <View key={folio} style={styles.requestFolioChip}>
                      <Text style={styles.requestFolioText}>{folio}</Text>
                    </View>
                  ))}
                </View>
              ) : (
                <Text style={styles.requestMuted}>
                  Todavía no hay folios asignados.
                </Text>
              )}
            </View>

            {!!selectedGroupRequest?.decision_reason && (
              <View style={styles.requestRejection}>
                <Text style={styles.requestRejectionLabel}>Motivo del rechazo</Text>
                <Text style={styles.requestRejectionText}>
                  {selectedGroupRequest.decision_reason}
                </Text>
              </View>
            )}

            {!!selectedGroupRequest?.conversation_id && (
              <Pressable
                style={styles.requestConversationButton}
                onPress={() => {
                  const id = selectedGroupRequest.conversation_id;
                  setSelectedGroupRequest(null);
                  router.push({
                    pathname: '/(technician)/communications/[id]',
                    params: { id: String(id) },
                  });
                }}
              >
                <Text style={styles.requestConversationText}>
                  Abrir conversación
                </Text>
              </Pressable>
            )}

            <Pressable
              style={styles.requestCloseButton}
              onPress={() => setSelectedGroupRequest(null)}
            >
              <Text style={styles.requestCloseText}>Cerrar</Text>
            </Pressable>
          </View>
        </View>
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
    paddingBottom: 18,
    paddingHorizontal: 20,
    paddingTop: 18,
  },

  title: {
    color: '#142b3a',
    fontSize: 29,
    fontWeight: '800',
    marginTop: 8,
  },

  filters: {
    backgroundColor: '#fff',
    borderColor: '#dbe4ea',
    borderRadius: 14,
    borderWidth: 1,
    gap: 10,
    marginBottom: 20,
    marginHorizontal: 20,
    padding: 12,
  },

  filterRow: {
    flexDirection: 'row',
    gap: 10,
  },

  filterField: {
    flex: 1,
    gap: 5,
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
    borderRadius: 9,
    borderWidth: 1,
    fontSize: 14,
    height: 40,
    paddingHorizontal: 10,
  },

  filterFooter: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: 10,
    marginTop: 2,
  },

  statusFilters: {
    flex: 1,
    flexDirection: 'row',
    gap: 6,
  },

  statusChip: {
    alignItems: 'center',
    backgroundColor: '#e9eef2',
    borderRadius: 14,
    flex: 1,
    paddingVertical: 7,
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
    paddingVertical: 7,
  },

  clearFiltersText: {
    color: '#0067a8',
    fontSize: 12,
    fontWeight: '700',
  },

  screenActions: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'center',
    gap: 14,
    marginBottom: 22,
    marginHorizontal: 20,
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
    gap: 14,
    paddingBottom: 28,
    paddingHorizontal: 20,
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

  statusStripe: {
    borderLeftWidth: 6,
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

  clientChoiceTitle: {
    color: '#142b3a',
    fontWeight: '800',
  },

  clientChoiceMeta: {
    color: '#667582',
    fontSize: 12,
    marginTop: 3,
  },

  selectedClient: {
    backgroundColor: '#e4f4ef',
    borderColor: '#75b9a7',
    borderRadius: 10,
    borderWidth: 1,
    gap: 4,
    padding: 11,
  },

  change: {
    color: '#0067a8',
    fontWeight: '700',
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

  relatedStatus: {
    color: '#64748b',
    fontSize: 10,
    marginTop: 2,
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

  requestOverlay: {
    ...StyleSheet.absoluteFillObject,
    alignItems: 'center',
    backgroundColor: 'rgba(16,28,38,0.58)',
    justifyContent: 'center',
    padding: 20,
  },

  requestDialog: {
    backgroundColor: '#fff',
    borderRadius: 18,
    gap: 8,
    maxWidth: 520,
    padding: 22,
    width: '100%',
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

  row: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
    marginTop: 10,
  },

  choice: {
    backgroundColor: '#f5f8fa',
    borderColor: '#cbd7df',
    borderRadius: 9,
    borderWidth: 1,
    padding: 10,
  },

  choiceActive: {
    backgroundColor: '#dff3f1',
    borderColor: '#008f87',
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

  cancelWorkOrder: {
    alignItems: 'center',
    borderColor: '#c36b18',
    borderRadius: 11,
    borderWidth: 1.5,
    justifyContent: 'center',
    marginBottom: 14,
    minHeight: 50,
  },

  cancelWorkOrderText: {
    color: '#a5530b',
    fontSize: 15,
    fontWeight: '800',
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

  requestHeader: {
    alignItems: 'flex-start',
    flexDirection: 'row',
    gap: 12,
    justifyContent: 'space-between',
  },

  requestHeaderCopy: {
    flex: 1,
    minWidth: 0,
  },

  requestEyebrow: {
    color: '#0067a8',
    fontSize: 11,
    fontWeight: '800',
    letterSpacing: 1,
    marginBottom: 5,
  },

  requestTitle: {
    color: '#142b3a',
    fontSize: 24,
    fontWeight: '800',
  },

  requestClient: {
    color: '#566874',
    fontSize: 15,
    marginTop: 5,
  },

  requestStatusBadge: {
    backgroundColor: '#e8edf1',
    borderRadius: 999,
    paddingHorizontal: 10,
    paddingVertical: 6,
  },

  requestStatusApproved: {
    backgroundColor: '#dff3e5',
  },

  requestStatusRejected: {
    backgroundColor: '#f8dfe2',
  },

  requestStatusReview: {
    backgroundColor: '#fff1c9',
  },

  requestStatusText: {
    color: '#314956',
    fontSize: 12,
    fontWeight: '800',
  },

  requestSummary: {
    backgroundColor: '#f4f7f9',
    borderRadius: 14,
    flexDirection: 'row',
    marginTop: 20,
    padding: 14,
  },

  requestSummaryItem: {
    flex: 1,
  },

  requestSummaryDivider: {
    backgroundColor: '#d9e1e6',
    marginHorizontal: 14,
    width: 1,
  },

  requestSummaryLabel: {
    color: '#74838e',
    fontSize: 11,
    fontWeight: '700',
    marginBottom: 5,
    textTransform: 'uppercase',
  },

  requestSummaryValue: {
    color: '#142b3a',
    fontSize: 26,
    fontWeight: '800',
  },

  requestSummaryValueSmall: {
    color: '#142b3a',
    fontSize: 17,
    fontWeight: '800',
  },

  requestSection: {
    marginTop: 22,
  },

  requestSectionLabel: {
    color: '#344553',
    fontSize: 13,
    fontWeight: '800',
    marginBottom: 10,
    textTransform: 'uppercase',
  },

  requestFolios: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },

  requestFolioChip: {
    backgroundColor: '#e9f3fa',
    borderColor: '#b7d5e8',
    borderRadius: 10,
    borderWidth: 1,
    paddingHorizontal: 13,
    paddingVertical: 9,
  },

  requestFolioText: {
    color: '#0067a8',
    fontSize: 16,
    fontWeight: '800',
  },

  requestMuted: {
    color: '#72818c',
    fontSize: 14,
  },

  requestRejection: {
    backgroundColor: '#fff0f1',
    borderRadius: 12,
    marginTop: 18,
    padding: 14,
  },

  requestRejectionLabel: {
    color: '#8d1f2d',
    fontSize: 12,
    fontWeight: '800',
    marginBottom: 5,
    textTransform: 'uppercase',
  },

  requestRejectionText: {
    color: '#75333c',
    lineHeight: 20,
  },

  requestConversationButton: {
    alignItems: 'center',
    borderColor: '#0067a8',
    borderRadius: 11,
    borderWidth: 1.5,
    justifyContent: 'center',
    marginTop: 22,
    minHeight: 50,
  },

  requestConversationText: {
    color: '#0067a8',
    fontSize: 15,
    fontWeight: '800',
  },

  requestCloseButton: {
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 10,
    minHeight: 44,
  },

  requestCloseText: {
    color: '#465964',
    fontSize: 15,
    fontWeight: '700',
  },
});
