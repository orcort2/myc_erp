import { useFocusEffect } from '@react-navigation/native';
import { Redirect, router, useLocalSearchParams } from 'expo-router';
import { useCallback, useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  Modal,
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
import { deriveMobileCapabilities } from '@/src/permissions/mobile-capabilities';
import { hasPermission } from '@/src/permissions/permissions';
import { useNotificationSync } from '@/src/notifications/NotificationSyncProvider';
import { affectsTickets, RefreshGate } from '@/src/notifications/refresh-policy';
import { filterGroupRequests, type RequestInboxKind, visibleRequestKinds } from '@/src/requests/request-inbox';
import type { LabWorkOrderGroupRequest } from '@/src/types/lab-work-order';
import type { OperationalTicket, SignaturePolicy, TicketStatus } from '@/src/types/operational-ticket';

const PAGE_SIZE = 25;
const STATUS_LABELS: Record<TicketStatus, string> = {
  pending: 'Pendiente',
  approved: 'Aprobado',
  rejected: 'Rechazado',
  in_progress: 'En proceso',
  resolved: 'Resuelto',
  cancelled: 'Cancelado',
};
const GROUP_STATUS_LABELS: Record<LabWorkOrderGroupRequest['status'], string> = {
  pending: 'Pendiente',
  in_review: 'En atención',
  approved: 'Aprobada',
  rejected: 'Rechazada',
};
const TICKET_TYPE_LABELS: Record<OperationalTicket['type'], string> = {
  reopen_work_order: 'Reapertura de OT',
  manual_myc_folio: 'Folio MYC manual',
  linked_folio: 'Folio Vinculado',
  partial_close: 'Cierre parcial',
  certificate_folio_block: 'Folios certificados',
  field_sheet_template_request: 'Hoja de campo no encontrada',
  field_sheet_reopen: 'Desbloqueo de hoja de campo',
};

export default function TicketsScreen() {
  const { authorizedFetch, isLoading: authLoading, user } = useAuth();
  const { publishLocalChange, subscribe } = useNotificationSync();
  const params = useLocalSearchParams<{ ticketId?: string; groupRequestId?: string; requestKind?: string }>();
  const capabilities = deriveMobileCapabilities(user);
  const [items, setItems] = useState<OperationalTicket[]>([]);
  const [groupRequests, setGroupRequests] = useState<LabWorkOrderGroupRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(false);
  const [error, setError] = useState('');
  const [status, setStatus] = useState<TicketStatus | 'all'>('all');
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [selected, setSelected] = useState<OperationalTicket | null>(null);
  const [selectedGroup, setSelectedGroup] = useState<LabWorkOrderGroupRequest | null>(null);
  const [kind, setKind] = useState<RequestInboxKind>('all');
  const [comment, setComment] = useState('');
  const [busy, setBusy] = useState(false);
  const [newRequestOpen, setNewRequestOpen] = useState(false);
  const [accreditedQuantity, setAccreditedQuantity] = useState('0');
  const [traceableQuantity, setTraceableQuantity] = useState('0');
  const [authorizedFolio, setAuthorizedFolio] = useState('');
  const [refreshing, setRefreshing] = useState(false);
  const itemCount = useRef(0);
  const refreshGate = useRef(new RefreshGate());

  const request = useCallback(async <T,>(path: string, init?: RequestInit): Promise<T> => {
    const headers = new Headers(init?.headers);
    if (init?.body) headers.set('Content-Type', 'application/json');
    const response = await authorizedFetch(apiUrl(path), { ...init, headers });
    if (!response.ok) throw new Error(await readApiError(response));
    return response.json() as Promise<T>;
  }, [authorizedFetch]);

  const load = useCallback(async (reset = true) => {
    if (reset) setLoading(true); else setLoadingMore(true);
    setError('');
    try {
      const query = [
        `limit=${PAGE_SIZE}`,
        `offset=${reset ? 0 : itemCount.current}`,
        status !== 'all' ? `status=${status}` : '',
        debouncedSearch ? `search=${encodeURIComponent(debouncedSearch)}` : '',
      ].filter(Boolean).join('&');
      const [next, groups] = await Promise.all([
        capabilities.canReadTickets
          ? request<OperationalTicket[]>(`/mobile/v1/technician/tickets?${query}`)
          : Promise.resolve([]),
        reset && capabilities.canReadWorkOrderGroupRequests
          ? request<LabWorkOrderGroupRequest[]>('/mobile/v1/technician/lab-work-orders/group-requests/review')
          : Promise.resolve(null),
      ]);
      setItems((current) => {
        const updated = reset ? next : [...current, ...next];
        itemCount.current = updated.length;
        return updated;
      });
      if (groups) setGroupRequests(groups);
      setHasMore(next.length === PAGE_SIZE);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Intenta nuevamente');
    } finally {
      if (reset) setLoading(false); else setLoadingMore(false);
    }
  }, [capabilities.canReadTickets, capabilities.canReadWorkOrderGroupRequests, debouncedSearch, request, status]);

  const refreshSelected = useCallback(async (ticketId?: number) => {
    const id = ticketId ?? selected?.id;
    if (!id) return;
    try { setSelected(await request<OperationalTicket>(`/mobile/v1/technician/tickets/${id}`)); } catch { /* ownership or deletion is reflected by the list */ }
  }, [request, selected?.id]);

  const refreshActive = useCallback(async (force = false) => {
    if (!refreshGate.current.shouldRefresh(Date.now(), force)) return;
    setRefreshing(true);
    await Promise.all([load(true), refreshSelected()]);
    setRefreshing(false);
  }, [load, refreshSelected]);

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(search.trim()), 400);
    return () => clearTimeout(timer);
  }, [search]);

  useEffect(() => {
    if (user && (capabilities.canReadTickets || capabilities.canReadWorkOrderGroupRequests)) load(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedSearch, status, user]);

  useFocusEffect(useCallback(() => { if (user) refreshActive(); }, [refreshActive, user]));

  useEffect(() => subscribe((event) => {
    if (!affectsTickets(event)) return;
    refreshActive(event.source === 'local');
    const ticketId = event.ticket_id ?? (event.entity_type === 'ticket' ? event.entity_id ?? undefined : undefined);
    if (ticketId && selected?.id === ticketId) refreshSelected(ticketId);
  }), [refreshActive, refreshSelected, selected?.id, subscribe]);

  // MOB-003: `user` gets a new object reference on every silent token
  // refresh, which would otherwise re-run this effect and call
  // refreshSelected(id) again — which sets `selected` and reopens the
  // ticket modal right after the technician closed it (setSelected(null)).
  // openedDeepLinkId remembers which id was already handled so a stale
  // `user` reference alone never reopens it.
  const openedDeepLinkId = useRef<number | null>(null);
  useEffect(() => {
    const id = Number(params.ticketId);
    if (id > 0 && user && openedDeepLinkId.current !== id) {
      openedDeepLinkId.current = id;
      refreshSelected(id);
    }
  }, [params.ticketId, refreshSelected, user]);

  const openedGroupDeepLinkId = useRef<number | null>(null);
  useEffect(() => {
    const id = Number(params.groupRequestId);
    if (id <= 0 || !user || openedGroupDeepLinkId.current === id || !groupRequests.length) return;
    openedGroupDeepLinkId.current = id;
    setKind('groups');
    setSelectedGroup(groupRequests.find((item) => item.id === id) ?? null);
  }, [groupRequests, params.groupRequestId, user]);

  async function review(action: 'approve' | 'reject', signaturePolicy?: SignaturePolicy) {
    if (!selected) return;
    setBusy(true);
    try {
      const body = action === 'approve'
        ? { signature_policy: signaturePolicy, comment: comment.trim() || null }
        : { comment: comment.trim() || 'Solicitud rechazada por el revisor.' };
      const updated = await request<OperationalTicket>(
        `/mobile/v1/technician/tickets/${selected.id}/${action}`,
        { method: 'POST', body: JSON.stringify(body) },
      );
      setSelected(updated);
      setComment('');
      await load(true);
      publishLocalChange({
        event_type: `ticket.${action === 'approve' ? 'approved' : 'rejected'}`,
        entity_type: 'ticket',
        entity_id: updated.id,
        ticket_id: updated.id,
        work_order_id: updated.work_order_id ?? undefined,
      });
    } catch (reviewError) {
      Alert.alert('No fue posible revisar el ticket', reviewError instanceof Error ? reviewError.message : 'Intenta nuevamente');
    } finally {
      setBusy(false);
    }
  }

  async function createCertificateBlockRequest() {
    const accredited = Number(accreditedQuantity) || 0;
    const traceable = Number(traceableQuantity) || 0;
    if (accredited + traceable < 1 || accredited + traceable > 100) {
      Alert.alert('Cantidad inválida', 'La suma de MYCA y MYCT debe estar entre 1 y 100.');
      return;
    }
    setBusy(true);
    try {
      await request('/mobile/v1/technician/tickets/certificate-block', {
        method: 'POST',
        body: JSON.stringify({
          accredited_quantity: accredited,
          traceable_quantity: traceable,
          reason: 'Folios certificados',
          description: `Reserva solicitada: ${accredited} MYCA y ${traceable} MYCT`,
        }),
      });
      setNewRequestOpen(false);
      setAccreditedQuantity('0');
      setTraceableQuantity('0');
      await load(true);
      Alert.alert('Solicitud enviada', 'Admin resolverá el bloque y conservará la conversación y auditoría.');
    } catch (requestError) {
      Alert.alert('No fue posible crear la solicitud', requestError instanceof Error ? requestError.message : 'Intenta nuevamente');
    } finally { setBusy(false); }
  }

  async function resolveSelected() {
    if (!selected) return;
    const needsFolio = selected.type === 'manual_myc_folio' || selected.type === 'linked_folio';
    if (needsFolio && !authorizedFolio.trim()) return;
    setBusy(true);
    try {
      const updated = await request<OperationalTicket>(
        `/mobile/v1/technician/tickets/${selected.id}/resolve`,
        { method: 'POST', body: JSON.stringify({ authorized_folio: needsFolio ? authorizedFolio.trim() : null, comment: comment.trim() || null }) },
      );
      setSelected(updated);
      setAuthorizedFolio('');
      setComment('');
      await load(true);
    } catch (resolveError) {
      Alert.alert('No fue posible resolver', resolveError instanceof Error ? resolveError.message : 'Intenta nuevamente');
    } finally { setBusy(false); }
  }

  async function claimGroupRequest() {
    if (!selectedGroup) return;
    setBusy(true);
    try {
      const updated = await request<LabWorkOrderGroupRequest>(
        `/mobile/v1/technician/lab-work-orders/group-requests/${selectedGroup.id}/claim`,
        { method: 'POST' },
      );
      setSelectedGroup(updated);
      await load(true);
    } catch (claimError) {
      Alert.alert('No fue posible tomar la solicitud', claimError instanceof Error ? claimError.message : 'Intenta nuevamente');
    } finally {
      setBusy(false);
    }
  }

  async function decideGroupRequest(action: 'approve' | 'reject') {
    if (!selectedGroup) return;
    if (action === 'reject' && !comment.trim()) {
      Alert.alert('Motivo requerido', 'Escribe el motivo del rechazo.');
      return;
    }
    setBusy(true);
    try {
      const updated = await request<LabWorkOrderGroupRequest>(
        `/mobile/v1/technician/lab-work-orders/group-requests/${selectedGroup.id}/${action}`,
        {
          method: 'POST',
          ...(action === 'reject' ? { body: JSON.stringify({ reason: comment.trim() }) } : {}),
        },
      );
      setSelectedGroup(updated);
      setComment('');
      await load(true);
    } catch (decisionError) {
      Alert.alert('No fue posible decidir la solicitud', decisionError instanceof Error ? decisionError.message : 'Intenta nuevamente');
    } finally {
      setBusy(false);
    }
  }

  if (authLoading) return <View style={styles.center}><ActivityIndicator /></View>;
  if (!user) return <Redirect href="/(auth)/login" />;
  const canReview = capabilities.canReviewTickets;
  const canResolve = !!user && hasPermission(user.permissions, 'lab_folios.resolve');
  const requestVisibility = visibleRequestKinds(kind);
  const visibleGroups = filterGroupRequests(groupRequests, status, debouncedSearch);

  return (
    <SafeAreaView edges={['top', 'right', 'bottom', 'left']} style={styles.screen}>
      <View style={styles.header}>
        <Pressable onPress={() => router.back()}><Text style={styles.back}>‹ Volver</Text></Pressable>
        <Text style={styles.title}>Solicitudes</Text>
        <Text style={styles.subtitle}>{capabilities.canReadWorkOrderGroupRequests ? 'Reaperturas y grupos anticipados por revisar' : 'Tus solicitudes operativas'}</Text>
      </View>
      <View style={styles.filters}>
        {capabilities.canCreateTickets && <Pressable style={styles.primary} onPress={() => setNewRequestOpen(true)}><Text style={styles.primaryText}>+ Nueva solicitud</Text></Pressable>}
        <TextInput onChangeText={setSearch} placeholder="Buscar cliente o motivo" style={styles.input} value={search} />
        <ScrollView horizontal showsHorizontalScrollIndicator={false}>
          {([
            ['all', 'Todas'], ['reopenings', 'Reaperturas'], ['groups', 'Grupos OT'],
          ] as const).map(([value, label]) => (
            <Pressable key={value} onPress={() => setKind(value)} style={[styles.chip, kind === value && styles.chipActive]}>
              <Text style={[styles.chipText, kind === value && styles.chipTextActive]}>{label}</Text>
            </Pressable>
          ))}
        </ScrollView>
        <ScrollView horizontal showsHorizontalScrollIndicator={false}>
          {([
            ['all', 'Todos'], ['pending', 'Pendientes'], ['in_progress', 'En proceso'],
            ['rejected', 'Rechazados'], ['resolved', 'Resueltos'],
          ] as const).map(([value, label]) => (
            <Pressable key={value} onPress={() => setStatus(value)} style={[styles.chip, status === value && styles.chipActive]}>
              <Text style={[styles.chipText, status === value && styles.chipTextActive]}>{label}</Text>
            </Pressable>
          ))}
        </ScrollView>
      </View>
      {loading ? <ActivityIndicator style={styles.loader} /> : (
        <ScrollView contentContainerStyle={styles.list} refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => refreshActive(true)} />}>
          {!!error && <Text style={styles.error}>{error}</Text>}
          {requestVisibility.showTickets && items.map((ticket) => (
            <Pressable key={ticket.id} onPress={() => { setSelected(ticket); setComment(''); }} style={styles.card}>
              <View style={styles.cardTop}>
                <Text style={styles.folio}>{TICKET_TYPE_LABELS[ticket.type]}{ticket.work_order_folio ? ` · OT ${ticket.work_order_folio}` : ''}</Text>
                <Text style={styles.status}>{STATUS_LABELS[ticket.status]}</Text>
              </View>
              {!!ticket.client_name && <Text style={styles.client}>{ticket.client_name}</Text>}
              <Text style={styles.reason}>{ticket.reason}</Text>
              <Text style={styles.meta}>{ticket.requested_by_name} · {new Date(ticket.created_at).toLocaleDateString()}</Text>
            </Pressable>
          ))}
          {requestVisibility.showGroups && visibleGroups.map((group) => (
            <Pressable key={`group-${group.id}`} onPress={() => { setSelectedGroup(group); setComment(''); }} style={styles.card}>
              <View style={styles.cardTop}>
                <Text style={styles.folio}>Grupo anticipado · #{group.id}</Text>
                <Text style={styles.status}>{GROUP_STATUS_LABELS[group.status]}</Text>
              </View>
              <Text style={styles.client}>{group.client_name}</Text>
              <Text style={styles.reason}>{group.quantity} OT · {group.operator_client_name}</Text>
              <Text style={styles.meta}>{group.requested_by_name} · {new Date(group.created_at).toLocaleDateString()}{group.handled_by_name ? ` · Atiende ${group.handled_by_name}` : ''}</Text>
              {!!group.folios.length && <Text style={styles.reason}>Folios: {group.folios.join(', ')}</Text>}
            </Pressable>
          ))}
          {(!requestVisibility.showTickets || !items.length) && (!requestVisibility.showGroups || !visibleGroups.length) && !error && <Text style={styles.empty}>No hay solicitudes que coincidan con los filtros.</Text>}
          {requestVisibility.showTickets && hasMore && <Pressable disabled={loadingMore} onPress={() => load(false)} style={styles.more}>{loadingMore ? <ActivityIndicator /> : <Text style={styles.moreText}>Cargar más</Text>}</Pressable>}
        </ScrollView>
      )}

      <Modal animationType="slide" onRequestClose={() => setSelected(null)} visible={!!selected}>
        <SafeAreaProvider>
          <SafeAreaView edges={['top', 'right', 'bottom', 'left']} style={styles.modal}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Ticket #{selected?.id}</Text>
              <Pressable onPress={() => setSelected(null)}><Text style={styles.close}>Cerrar</Text></Pressable>
            </View>
            {selected && <ScrollView contentContainerStyle={styles.modalContent}>
              <Text style={styles.folio}>{TICKET_TYPE_LABELS[selected.type]}{selected.work_order_folio ? ` · OT ${selected.work_order_folio}` : ''}</Text>
              <Text style={styles.detailStatus}>{STATUS_LABELS[selected.status]}</Text>
              <Text style={styles.detailLabel}>Motivo</Text><Text style={styles.detail}>{selected.reason}</Text>
              <Text style={styles.detailLabel}>Descripción</Text><Text style={styles.detail}>{selected.description}</Text>
              <Text style={styles.detailLabel}>Solicitante</Text><Text style={styles.detail}>{selected.requested_by_name}</Text>
              {!!selected.automatic_folio && <><Text style={styles.detailLabel}>Folio automático preservado</Text><Text style={styles.detail}>{selected.automatic_folio}</Text></>}
              {!!selected.requested_folio && <><Text style={styles.detailLabel}>Folio solicitado</Text><Text style={styles.detail}>{selected.requested_folio}</Text></>}
              {!!selected.authorized_folio && <><Text style={styles.detailLabel}>Folio autorizado</Text><Text style={styles.detail}>{selected.authorized_folio}</Text></>}
              {selected.type === 'certificate_folio_block' && <Text style={styles.detail}>{selected.accredited_quantity ?? 0} MYCA + {selected.traceable_quantity ?? 0} MYCT</Text>}
              {(selected.type === 'field_sheet_reopen' || selected.type === 'field_sheet_template_request') && !!selected.equipment_id && (
                <><Text style={styles.detailLabel}>Equipo</Text><Text style={styles.detail}>Equipo #{selected.equipment_id} de la OT{selected.work_order_folio ? ` ${selected.work_order_folio}` : ''}</Text></>
              )}
              {selected.type === 'field_sheet_reopen' && !!selected.resolution_snapshot?.revision_number && (
                <><Text style={styles.detailLabel}>Revisión de la hoja</Text><Text style={styles.detail}>Revisión {String(selected.resolution_snapshot.revision_number)}</Text></>
              )}
              {!!selected.decision_comment && <><Text style={styles.detailLabel}>Decisión</Text><Text style={styles.detail}>{selected.decision_comment}</Text></>}
              {canReview && selected.type === 'reopen_work_order' && selected.status === 'pending' && <>
                <Text style={styles.warning}>Si durante la edición se realiza un cambio estructural, el backend invalidará automáticamente las firmas existentes.</Text>
                <TextInput multiline onChangeText={setComment} placeholder="Comentario de decisión" style={[styles.input, styles.comment]} value={comment} />
                <Pressable disabled={busy} onPress={() => review('approve', 'preserve')} style={styles.primary}><Text style={styles.primaryText}>Aprobar conservando firma</Text></Pressable>
                <Pressable disabled={busy} onPress={() => review('approve', 'invalidate')} style={styles.secondary}><Text style={styles.secondaryText}>Aprobar y requerir nuevas firmas</Text></Pressable>
                <Pressable disabled={busy} onPress={() => review('reject')} style={styles.reject}><Text style={styles.rejectText}>Rechazar</Text></Pressable>
              </>}
              {canResolve && selected.type !== 'reopen_work_order' && selected.status === 'pending' && <>
                {(selected.type === 'manual_myc_folio' || selected.type === 'linked_folio') && <TextInput autoCapitalize="characters" onChangeText={setAuthorizedFolio} placeholder="Folio completo autorizado" style={styles.input} value={authorizedFolio} />}
                <TextInput multiline onChangeText={setComment} placeholder="Comentario de resolución" style={[styles.input, styles.comment]} value={comment} />
                <Pressable disabled={busy || ((selected.type === 'manual_myc_folio' || selected.type === 'linked_folio') && !authorizedFolio.trim())} onPress={resolveSelected} style={styles.primary}><Text style={styles.primaryText}>Resolver solicitud</Text></Pressable>
                <Pressable disabled={busy || !comment.trim()} onPress={() => review('reject')} style={styles.reject}><Text style={styles.rejectText}>Rechazar</Text></Pressable>
              </>}
              {!!selected.conversation_id && <Pressable style={styles.secondary} onPress={() => { const id = selected.conversation_id; setSelected(null); router.push({ pathname: '/(technician)/communications/[id]', params: { id: String(id) } }); }}><Text style={styles.secondaryText}>Abrir conversación</Text></Pressable>}
            </ScrollView>}
          </SafeAreaView>
        </SafeAreaProvider>
      </Modal>
      <Modal animationType="slide" onRequestClose={() => setNewRequestOpen(false)} visible={newRequestOpen}>
        <SafeAreaProvider>
          <SafeAreaView edges={['top', 'right', 'bottom', 'left']} style={styles.modal}>
            <View style={styles.modalHeader}><Text style={styles.modalTitle}>Nueva solicitud</Text><Pressable onPress={() => setNewRequestOpen(false)}><Text style={styles.close}>Cerrar</Text></Pressable></View>
            <ScrollView contentContainerStyle={styles.modalContent}>
              <Text style={styles.detailLabel}>Folios OT</Text><Pressable style={styles.secondary} onPress={() => { setNewRequestOpen(false); router.push('/(technician)/work-orders'); }}><Text style={styles.secondaryText}>Ir a solicitud de grupo OT</Text></Pressable>
              <Text style={styles.detailLabel}>Folios certificados</Text>
              <Text style={styles.detail}>Máximo 100 combinados entre MYCA y MYCT.</Text>
              <TextInput keyboardType="number-pad" onChangeText={setAccreditedQuantity} placeholder="Cantidad MYCA" style={styles.input} value={accreditedQuantity} />
              <TextInput keyboardType="number-pad" onChangeText={setTraceableQuantity} placeholder="Cantidad MYCT" style={[styles.input, { marginTop: 10 }]} value={traceableQuantity} />
              <Pressable disabled={busy} style={styles.primary} onPress={createCertificateBlockRequest}><Text style={styles.primaryText}>Solicitar bloque</Text></Pressable>
              <Text style={styles.detailLabel}>Folio MYC manual / Vinculado</Text><Text style={styles.detail}>Se solicita desde el equipo correspondiente para conservar OT, servicio, folio automático y procedencia.</Text>
            </ScrollView>
          </SafeAreaView>
        </SafeAreaProvider>
      </Modal>
      <Modal animationType="slide" onRequestClose={() => setSelectedGroup(null)} visible={!!selectedGroup}>
        <SafeAreaProvider>
          <SafeAreaView edges={['top', 'right', 'bottom', 'left']} style={styles.modal}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Solicitud de grupo #{selectedGroup?.id}</Text>
              <Pressable onPress={() => setSelectedGroup(null)}><Text style={styles.close}>Cerrar</Text></Pressable>
            </View>
            {selectedGroup && <ScrollView contentContainerStyle={styles.modalContent}>
              <Text style={styles.folio}>{selectedGroup.quantity} órdenes de trabajo</Text>
              <Text style={styles.detailStatus}>{GROUP_STATUS_LABELS[selectedGroup.status]}</Text>
              <Text style={styles.detailLabel}>Organización operadora</Text><Text style={styles.detail}>{selectedGroup.operator_client_name}</Text>
              <Text style={styles.detailLabel}>Solicitante</Text><Text style={styles.detail}>{selectedGroup.requested_by_name}</Text>
              <Text style={styles.detailLabel}>Cliente final</Text><Text style={styles.detail}>{selectedGroup.client_name}</Text>
              <Text style={styles.detailLabel}>Fecha</Text><Text style={styles.detail}>{new Date(selectedGroup.created_at).toLocaleString()}</Text>
              <Text style={styles.detailLabel}>Handler</Text><Text style={styles.detail}>{selectedGroup.handled_by_name ?? 'Sin asignar'}</Text>
              {!!selectedGroup.folios.length && <><Text style={styles.detailLabel}>Folios asignados</Text><Text style={styles.detail}>{selectedGroup.folios.join(', ')}</Text></>}
              {!!selectedGroup.decision_reason && <><Text style={styles.detailLabel}>Motivo</Text><Text style={styles.detail}>{selectedGroup.decision_reason}</Text></>}
              {selectedGroup.status === 'pending' && capabilities.canClaimWorkOrderGroupRequests && <Pressable disabled={busy} onPress={claimGroupRequest} style={styles.primary}><Text style={styles.primaryText}>Tomar solicitud</Text></Pressable>}
              {selectedGroup.status === 'in_review' && selectedGroup.handled_by_user_id === user.id && capabilities.canDecideWorkOrderGroupRequests && <>
                <TextInput multiline onChangeText={setComment} placeholder="Motivo requerido para rechazo" style={[styles.input, styles.comment]} value={comment} />
                <Pressable disabled={busy} onPress={() => decideGroupRequest('approve')} style={styles.primary}><Text style={styles.primaryText}>Aprobar y materializar grupo</Text></Pressable>
                <Pressable disabled={busy || !comment.trim()} onPress={() => decideGroupRequest('reject')} style={styles.reject}><Text style={styles.rejectText}>Rechazar solicitud</Text></Pressable>
              </>}
              {!!selectedGroup.conversation_id && <Pressable style={styles.secondary} onPress={() => { const id = selectedGroup.conversation_id; setSelectedGroup(null); router.push({ pathname: '/(technician)/communications/[id]', params: { id: String(id) } }); }}><Text style={styles.secondaryText}>Abrir conversación</Text></Pressable>}
            </ScrollView>}
          </SafeAreaView>
        </SafeAreaProvider>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  center: { alignItems: 'center', flex: 1, justifyContent: 'center' }, screen: { backgroundColor: '#f4f7fa', flex: 1 }, header: { padding: 20 }, back: { color: '#0067a8', fontSize: 17, marginBottom: 18 }, title: { color: '#142b3a', fontSize: 30, fontWeight: '800' }, subtitle: { color: '#667582', marginTop: 6 },
  filters: { gap: 12, paddingHorizontal: 20 }, input: { backgroundColor: '#fff', borderColor: '#b9c8d2', borderRadius: 11, borderWidth: 1, fontSize: 16, minHeight: 48, paddingHorizontal: 13 }, chip: { backgroundColor: '#e5ebef', borderRadius: 18, marginRight: 8, paddingHorizontal: 14, paddingVertical: 9 }, chipActive: { backgroundColor: '#0067a8' }, chipText: { color: '#425563', fontWeight: '700' }, chipTextActive: { color: '#fff' }, loader: { marginTop: 44 }, list: { gap: 10, padding: 20 },
  card: { backgroundColor: '#fff', borderRadius: 13, padding: 16 }, cardTop: { alignItems: 'center', flexDirection: 'row', justifyContent: 'space-between' }, folio: { color: '#0067a8', fontSize: 19, fontWeight: '800' }, status: { backgroundColor: '#e7f0f5', borderRadius: 12, color: '#24516d', fontSize: 12, fontWeight: '800', overflow: 'hidden', paddingHorizontal: 9, paddingVertical: 5 }, client: { color: '#263b48', fontSize: 16, fontWeight: '700', marginTop: 8 }, reason: { color: '#51616c', marginTop: 5 }, meta: { color: '#7a8892', fontSize: 12, marginTop: 10 }, empty: { color: '#70808d', padding: 24, textAlign: 'center' }, error: { backgroundColor: '#fff0f0', borderRadius: 10, color: '#8d1f2d', padding: 14, textAlign: 'center' }, more: { alignItems: 'center', borderColor: '#0067a8', borderRadius: 10, borderWidth: 1, minHeight: 46, justifyContent: 'center' }, moreText: { color: '#0067a8', fontWeight: '800' },
  modal: { backgroundColor: '#f4f7fa', flex: 1 }, modalHeader: { alignItems: 'center', backgroundColor: '#fff', borderBottomColor: '#dce3e9', borderBottomWidth: 1, flexDirection: 'row', justifyContent: 'space-between', padding: 20 }, modalTitle: { fontSize: 22, fontWeight: '800' }, close: { color: '#0067a8', fontSize: 16, fontWeight: '700' }, modalContent: { padding: 20 }, detailStatus: { color: '#24516d', fontWeight: '800', marginBottom: 18, marginTop: 8 }, detailLabel: { color: '#344553', fontSize: 13, fontWeight: '800', marginTop: 13, textTransform: 'uppercase' }, detail: { color: '#233944', fontSize: 16, lineHeight: 22, marginTop: 5 }, warning: { backgroundColor: '#fff5cf', borderRadius: 10, color: '#5f4d00', lineHeight: 21, marginTop: 24, padding: 14 }, comment: { marginTop: 16, minHeight: 90, paddingTop: 12, textAlignVertical: 'top' }, primary: { alignItems: 'center', backgroundColor: '#0067a8', borderRadius: 11, justifyContent: 'center', marginTop: 14, minHeight: 52 }, primaryText: { color: '#fff', fontSize: 15, fontWeight: '800' }, secondary: { alignItems: 'center', borderColor: '#0067a8', borderRadius: 11, borderWidth: 1.5, justifyContent: 'center', marginTop: 10, minHeight: 52 }, secondaryText: { color: '#0067a8', fontSize: 15, fontWeight: '800' }, reject: { alignItems: 'center', marginTop: 18, padding: 12 }, rejectText: { color: '#a51c30', fontSize: 16, fontWeight: '800' },
});
