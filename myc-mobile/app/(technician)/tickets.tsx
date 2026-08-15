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
import { hasPermission } from '@/src/permissions/permissions';
import { useNotificationSync } from '@/src/notifications/NotificationSyncProvider';
import { affectsTickets, RefreshGate } from '@/src/notifications/refresh-policy';
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

export default function TicketsScreen() {
  const { authorizedFetch, isLoading: authLoading, user } = useAuth();
  const { publishLocalChange, subscribe } = useNotificationSync();
  const params = useLocalSearchParams<{ ticketId?: string }>();
  const [items, setItems] = useState<OperationalTicket[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(false);
  const [error, setError] = useState('');
  const [status, setStatus] = useState<TicketStatus | 'all'>('all');
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [selected, setSelected] = useState<OperationalTicket | null>(null);
  const [comment, setComment] = useState('');
  const [busy, setBusy] = useState(false);
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
      const next = await request<OperationalTicket[]>(`/mobile/v1/technician/tickets?${query}`);
      setItems((current) => {
        const updated = reset ? next : [...current, ...next];
        itemCount.current = updated.length;
        return updated;
      });
      setHasMore(next.length === PAGE_SIZE);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Intenta nuevamente');
    } finally {
      if (reset) setLoading(false); else setLoadingMore(false);
    }
  }, [debouncedSearch, request, status]);

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
    if (user) load(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedSearch, status, user]);

  useFocusEffect(useCallback(() => { if (user) refreshActive(); }, [refreshActive, user]));

  useEffect(() => subscribe((event) => {
    if (!affectsTickets(event)) return;
    refreshActive(event.source === 'local');
    const ticketId = event.ticket_id ?? (event.entity_type === 'ticket' ? event.entity_id ?? undefined : undefined);
    if (ticketId && selected?.id === ticketId) refreshSelected(ticketId);
  }), [refreshActive, refreshSelected, selected?.id, subscribe]);

  useEffect(() => {
    const id = Number(params.ticketId);
    if (id > 0 && user) refreshSelected(id);
  }, [params.ticketId, refreshSelected, user]);

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
        work_order_id: updated.work_order_id,
      });
    } catch (reviewError) {
      Alert.alert('No fue posible revisar el ticket', reviewError instanceof Error ? reviewError.message : 'Intenta nuevamente');
    } finally {
      setBusy(false);
    }
  }

  if (authLoading) return <View style={styles.center}><ActivityIndicator /></View>;
  if (!user) return <Redirect href="/(auth)/login" />;
  const canReview = hasPermission(user.permissions, 'tickets.review');

  return (
    <SafeAreaView edges={['top', 'right', 'bottom', 'left']} style={styles.screen}>
      <View style={styles.header}>
        <Pressable onPress={() => router.back()}><Text style={styles.back}>‹ Inicio</Text></Pressable>
        <Text style={styles.title}>Tickets</Text>
        <Text style={styles.subtitle}>{canReview ? 'Solicitudes operativas por revisar' : 'Tus solicitudes operativas'}</Text>
      </View>
      <View style={styles.filters}>
        <TextInput onChangeText={setSearch} placeholder="Buscar cliente o motivo" style={styles.input} value={search} />
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
          {items.map((ticket) => (
            <Pressable key={ticket.id} onPress={() => { setSelected(ticket); setComment(''); }} style={styles.card}>
              <View style={styles.cardTop}>
                <Text style={styles.folio}>OT {ticket.work_order_folio}</Text>
                <Text style={styles.status}>{STATUS_LABELS[ticket.status]}</Text>
              </View>
              <Text style={styles.client}>{ticket.client_name}</Text>
              <Text style={styles.reason}>{ticket.reason}</Text>
              <Text style={styles.meta}>{ticket.requested_by_name} · {new Date(ticket.created_at).toLocaleDateString()}</Text>
            </Pressable>
          ))}
          {!items.length && !error && <Text style={styles.empty}>No hay tickets que coincidan con los filtros.</Text>}
          {hasMore && <Pressable disabled={loadingMore} onPress={() => load(false)} style={styles.more}>{loadingMore ? <ActivityIndicator /> : <Text style={styles.moreText}>Cargar más</Text>}</Pressable>}
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
              <Text style={styles.folio}>OT {selected.work_order_folio} · {selected.client_name}</Text>
              <Text style={styles.detailStatus}>{STATUS_LABELS[selected.status]}</Text>
              <Text style={styles.detailLabel}>Motivo</Text><Text style={styles.detail}>{selected.reason}</Text>
              <Text style={styles.detailLabel}>Descripción</Text><Text style={styles.detail}>{selected.description}</Text>
              <Text style={styles.detailLabel}>Solicitante</Text><Text style={styles.detail}>{selected.requested_by_name}</Text>
              {!!selected.decision_comment && <><Text style={styles.detailLabel}>Decisión</Text><Text style={styles.detail}>{selected.decision_comment}</Text></>}
              {canReview && selected.status === 'pending' && <>
                <Text style={styles.warning}>Si durante la edición se realiza un cambio estructural, el backend invalidará automáticamente las firmas existentes.</Text>
                <TextInput multiline onChangeText={setComment} placeholder="Comentario de decisión" style={[styles.input, styles.comment]} value={comment} />
                <Pressable disabled={busy} onPress={() => review('approve', 'preserve')} style={styles.primary}><Text style={styles.primaryText}>Aprobar conservando firma</Text></Pressable>
                <Pressable disabled={busy} onPress={() => review('approve', 'invalidate')} style={styles.secondary}><Text style={styles.secondaryText}>Aprobar y requerir nuevas firmas</Text></Pressable>
                <Pressable disabled={busy} onPress={() => review('reject')} style={styles.reject}><Text style={styles.rejectText}>Rechazar</Text></Pressable>
              </>}
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
