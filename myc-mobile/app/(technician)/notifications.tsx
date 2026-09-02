import { useFocusEffect } from '@react-navigation/native';
import { Redirect, router } from 'expo-router';
import { useCallback, useEffect, useState } from 'react';
import { ActivityIndicator, Pressable, RefreshControl, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { apiUrl, readApiError } from '@/src/api/client';
import { useAuth } from '@/src/auth/AuthProvider';
import { useNotificationSync } from '@/src/notifications/NotificationSyncProvider';
import { eventFromData, markReadThenNavigate, targetFor } from '@/src/notifications/refresh-policy';
import type { MobileNotification, NotificationPage, NotificationSyncEvent } from '@/src/types/notification';

const PAGE_SIZE = 25;

function friendlyDate(value: string): string {
  const date = new Date(value);
  const minutes = Math.floor((Date.now() - date.getTime()) / 60_000);
  if (minutes < 1) return 'Ahora';
  if (minutes < 60) return `Hace ${minutes} min`;
  const today = new Date();
  if (date.toDateString() === today.toDateString()) return `Hoy ${date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
  const yesterday = new Date(today); yesterday.setDate(today.getDate() - 1);
  if (date.toDateString() === yesterday.toDateString()) return 'Ayer';
  return date.toLocaleDateString();
}

export default function NotificationsScreen() {
  const { authorizedFetch, isLoading: authLoading, user } = useAuth();
  const { refreshUnread, subscribe } = useNotificationSync();
  const [items, setItems] = useState<MobileNotification[]>([]);
  const [unreadOnly, setUnreadOnly] = useState(false);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(false);
  const [error, setError] = useState('');

  const load = useCallback(async (reset = true, requestedOffset = 0) => {
    if (reset) setRefreshing(true); else setLoadingMore(true);
    setError('');
    try {
      const offset = reset ? 0 : requestedOffset;
      const response = await authorizedFetch(apiUrl(`/mobile/v1/notifications?limit=${PAGE_SIZE}&offset=${offset}&unread_only=${unreadOnly}`));
      if (!response.ok) throw new Error(await readApiError(response));
      const page = await response.json() as NotificationPage;
      setItems((current) => reset ? page.items : [...current, ...page.items]);
      setHasMore(offset + page.items.length < page.total);
      await refreshUnread();
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'No fue posible cargar notificaciones');
    } finally {
      setLoading(false); setRefreshing(false); setLoadingMore(false);
    }
  }, [authorizedFetch, refreshUnread, unreadOnly]);

  useFocusEffect(useCallback(() => { if (user) load(true); }, [load, user]));
  useEffect(() => subscribe((_event: NotificationSyncEvent) => { load(true); }), [load, subscribe]);

  async function open(item: MobileNotification) {
    await markReadThenNavigate(async () => {
      if (!item.read_at) {
        await authorizedFetch(apiUrl(`/mobile/v1/notifications/${item.id}/read`), { method: 'POST' });
        setItems((current) => current.map((value) => value.id === item.id ? { ...value, read_at: new Date().toISOString() } : value));
        await refreshUnread();
      }
    }, () => {
      const target = targetFor(eventFromData({
        ...item.metadata_json,
        entity_type: item.entity_type,
        entity_id: item.entity_id,
        event_type: item.notification_type,
      }, 'local', `notification:${item.id}`));
      if (target) router.push(target);
    });
  }

  async function readAll() {
    await authorizedFetch(apiUrl('/mobile/v1/notifications/read-all'), { method: 'POST' });
    setItems((current) => current.map((item) => ({ ...item, read_at: item.read_at ?? new Date().toISOString() })));
    await refreshUnread();
  }

  if (authLoading) return <View style={styles.center}><ActivityIndicator /></View>;
  if (!user) return <Redirect href="/(auth)/login" />;
  return (
    <SafeAreaView edges={['top', 'right', 'bottom', 'left']} style={styles.screen}>
      <View style={styles.header}>
        <Pressable onPress={() => router.back()}><Text style={styles.back}>‹ Volver</Text></Pressable>
        <Text style={styles.title}>Notificaciones</Text>
        <Pressable onPress={readAll}><Text style={styles.readAll}>Marcar todas como leídas</Text></Pressable>
      </View>
      <View style={styles.filters}>
        <Pressable onPress={() => setUnreadOnly(false)} style={[styles.chip, !unreadOnly && styles.chipActive]}><Text style={!unreadOnly ? styles.chipTextActive : styles.chipText}>Todas</Text></Pressable>
        <Pressable onPress={() => setUnreadOnly(true)} style={[styles.chip, unreadOnly && styles.chipActive]}><Text style={unreadOnly ? styles.chipTextActive : styles.chipText}>No leídas</Text></Pressable>
      </View>
      {loading ? <ActivityIndicator style={styles.loader} /> : <ScrollView
        contentContainerStyle={styles.list}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => load(true)} />}
      >
        {!!error && <Text style={styles.error}>{error}</Text>}
        {items.map((item) => <Pressable key={item.id} onPress={() => open(item)} style={[styles.card, !item.read_at && styles.unreadCard]}>
          <View style={styles.cardTop}><Text style={[styles.cardTitle, !item.read_at && styles.unreadTitle]}>{item.title}</Text><Text style={styles.state}>{item.read_at ? 'Leída' : 'No leída'}</Text></View>
          {!!item.body && <Text style={styles.body}>{item.body}</Text>}
          <Text style={styles.date}>{friendlyDate(item.created_at)}</Text>
        </Pressable>)}
        {!items.length && !error && <Text style={styles.empty}>No hay notificaciones.</Text>}
        {hasMore && <Pressable disabled={loadingMore} onPress={() => load(false, items.length)} style={styles.more}>{loadingMore ? <ActivityIndicator /> : <Text style={styles.moreText}>Cargar más</Text>}</Pressable>}
      </ScrollView>}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  center: { alignItems: 'center', flex: 1, justifyContent: 'center' }, screen: { backgroundColor: '#f4f7fa', flex: 1 }, header: { padding: 20 }, back: { color: '#0067a8', fontSize: 17, marginBottom: 16 }, title: { color: '#142b3a', fontSize: 30, fontWeight: '800' }, readAll: { color: '#0067a8', fontWeight: '700', marginTop: 10 }, filters: { flexDirection: 'row', gap: 8, paddingHorizontal: 20 }, chip: { backgroundColor: '#e5ebef', borderRadius: 18, paddingHorizontal: 14, paddingVertical: 9 }, chipActive: { backgroundColor: '#0067a8' }, chipText: { color: '#425563', fontWeight: '700' }, chipTextActive: { color: '#fff', fontWeight: '700' }, loader: { marginTop: 44 }, list: { gap: 10, padding: 20 }, card: { backgroundColor: '#fff', borderRadius: 13, borderWidth: 1, borderColor: 'transparent', padding: 16 }, unreadCard: { borderColor: '#0067a8' }, cardTop: { alignItems: 'flex-start', flexDirection: 'row', gap: 10, justifyContent: 'space-between' }, cardTitle: { color: '#263b48', flex: 1, fontSize: 16 }, unreadTitle: { fontWeight: '800' }, state: { color: '#526775', fontSize: 12, fontWeight: '700' }, body: { color: '#51616c', lineHeight: 20, marginTop: 7 }, date: { color: '#7a8892', fontSize: 12, marginTop: 10 }, error: { backgroundColor: '#fff0f0', color: '#8d1f2d', padding: 14 }, empty: { color: '#70808d', padding: 24, textAlign: 'center' }, more: { alignItems: 'center', borderColor: '#0067a8', borderRadius: 10, borderWidth: 1, minHeight: 46, justifyContent: 'center' }, moreText: { color: '#0067a8', fontWeight: '800' },
});
