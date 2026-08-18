import { router } from 'expo-router';
import { useEffect, useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  Modal,
  Pressable,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';

import { useAuth } from '@/src/auth/AuthProvider';
import { useCommunications } from '@/src/communications/CommunicationsProvider';
import { createConversation, fetchDirectory, fetchMentions } from '@/src/services/communications';
import type { CommunicationDirectory, CommunicationMentionInbox } from '@/src/types/communication';

type Section = 'conversations' | 'mentions' | 'tickets';

export default function CommunicationsScreen() {
  const { authorizedFetch } = useAuth();
  const { conversations, error, isLoading, refreshConversations } = useCommunications();
  const [section, setSection] = useState<Section>('conversations');
  const [mentions, setMentions] = useState<CommunicationMentionInbox[]>([]);
  const [directory, setDirectory] = useState<CommunicationDirectory | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [groupMode, setGroupMode] = useState(false);
  const [title, setTitle] = useState('');
  const [selected, setSelected] = useState<number[]>([]);
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  useEffect(() => {
    if (section !== 'mentions') return;
    fetchMentions(authorizedFetch).then(setMentions).catch(() => setMentions([]));
  }, [authorizedFetch, section]);

  async function openCreate() {
    setShowCreate(true);
    setCreateError(null);
    if (!directory) {
      try { setDirectory(await fetchDirectory(authorizedFetch)); } catch { setCreateError('No fue posible cargar usuarios.'); }
    }
  }

  async function submitConversation() {
    if (!selected.length || (groupMode && selected.length < 2)) return;
    setCreating(true);
    setCreateError(null);
    try {
      const conversation = await createConversation(authorizedFetch, groupMode
        ? { conversation_type: 'group', title: title.trim(), participant_user_ids: selected }
        : { conversation_type: 'internal', participant_user_id: selected[0] });
      await refreshConversations();
      setShowCreate(false);
      setSelected([]);
      setTitle('');
      router.push({ pathname: '/(technician)/communications/[id]', params: { id: String(conversation.id) } });
    } catch (caught) {
      setCreateError(caught instanceof Error ? caught.message : 'No fue posible crear la conversación');
    } finally {
      setCreating(false);
    }
  }

  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.header}>
        <Pressable onPress={() => router.back()}><Text style={styles.back}>‹ Inicio</Text></Pressable>
        <Text style={styles.title}>Comunicaciones</Text>
        <Pressable onPress={openCreate}><Text style={styles.new}>＋ Nueva</Text></Pressable>
      </View>
      <View style={styles.tabs}>
        {(['conversations', 'mentions', 'tickets'] as Section[]).map((item) => (
          <Pressable key={item} style={[styles.tab, section === item && styles.tabActive]} onPress={() => setSection(item)}>
            <Text style={[styles.tabText, section === item && styles.tabTextActive]}>
              {item === 'conversations' ? 'Conversaciones' : item === 'mentions' ? 'Menciones' : 'Tickets'}
            </Text>
          </Pressable>
        ))}
      </View>
      {error && <Text style={styles.error}>{error}</Text>}
      {section === 'conversations' && (
        <FlatList
          data={conversations}
          keyExtractor={(item) => String(item.id)}
          refreshing={isLoading}
          onRefresh={() => refreshConversations()}
          contentContainerStyle={styles.list}
          ListEmptyComponent={isLoading ? <ActivityIndicator /> : <Text style={styles.empty}>Aún no hay conversaciones.</Text>}
          renderItem={({ item }) => (
            <Pressable
              style={styles.card}
              onPress={() => router.push({ pathname: '/(technician)/communications/[id]', params: { id: String(item.id) } })}
            >
              <View style={styles.cardTop}>
                <Text style={styles.cardTitle}>{item.title}</Text>
                {!!item.unread_count && <Text style={styles.badge}>{item.unread_count}</Text>}
              </View>
              <Text numberOfLines={1} style={styles.preview}>{item.last_message?.body ?? 'Sin mensajes'}</Text>
              {!!item.last_message_at && <Text style={styles.date}>{new Date(item.last_message_at).toLocaleString()}</Text>}
            </Pressable>
          )}
        />
      )}
      {section === 'mentions' && (
        <FlatList
          data={mentions}
          keyExtractor={(item) => `${item.message.id}:${item.message.sender.id}`}
          contentContainerStyle={styles.list}
          ListEmptyComponent={<Text style={styles.empty}>No tienes menciones.</Text>}
          renderItem={({ item }) => (
            <Pressable
              style={styles.card}
              onPress={() => router.push({ pathname: '/(technician)/communications/[id]', params: { id: String(item.message.conversation_id) } })}
            >
              <Text style={styles.cardTitle}>{item.conversation_title}</Text>
              <Text style={styles.preview}>{item.message.body}</Text>
              {!item.read_at && <Text style={styles.mentionUnread}>Sin leer</Text>}
            </Pressable>
          )}
        />
      )}
      {section === 'tickets' && (
        <View style={styles.ticketPanel}>
          <Text style={styles.ticketTitle}>Tickets operativos</Text>
          <Text style={styles.preview}>Los tickets conservan su identidad y pueden relacionarse con una conversación.</Text>
          <Pressable style={styles.primaryButton} onPress={() => router.push('/(technician)/tickets')}>
            <Text style={styles.primaryText}>Abrir Tickets</Text>
          </Pressable>
        </View>
      )}

      <Modal visible={showCreate} animationType="slide" transparent onRequestClose={() => setShowCreate(false)}>
        <View style={styles.modalBackdrop}>
          <View style={styles.modalCard}>
            <View style={styles.cardTop}>
              <Text style={styles.modalTitle}>Nueva conversación</Text>
              <Pressable onPress={() => setShowCreate(false)}><Text style={styles.close}>Cerrar</Text></Pressable>
            </View>
            <View style={styles.modeRow}>
              <Pressable style={[styles.mode, !groupMode && styles.modeActive]} onPress={() => { setGroupMode(false); setSelected([]); }}><Text>Directa</Text></Pressable>
              <Pressable style={[styles.mode, groupMode && styles.modeActive]} onPress={() => { setGroupMode(true); setSelected([]); }}><Text>Grupo</Text></Pressable>
            </View>
            {groupMode && <TextInput style={styles.input} placeholder="Nombre del grupo" value={title} onChangeText={setTitle} maxLength={180} />}
            <ScrollView style={styles.people}>
              {directory?.users.map((person) => {
                const checked = selected.includes(person.id);
                return (
                  <Pressable
                    key={person.id}
                    style={[styles.person, checked && styles.personSelected]}
                    onPress={() => setSelected((current) => groupMode
                      ? checked ? current.filter((id) => id !== person.id) : [...current, person.id]
                      : [person.id])}
                  >
                    <Text style={styles.personName}>{checked ? '✓ ' : ''}{person.full_name}</Text>
                    <Text style={styles.personEmail}>{person.email}</Text>
                  </Pressable>
                );
              })}
            </ScrollView>
            {createError && <Text style={styles.error}>{createError}</Text>}
            <Pressable
              disabled={creating || !selected.length || (groupMode && (selected.length < 2 || !title.trim()))}
              style={[styles.primaryButton, (creating || !selected.length) && styles.disabled]}
              onPress={submitConversation}
            >
              <Text style={styles.primaryText}>{creating ? 'Creando…' : 'Crear conversación'}</Text>
            </Pressable>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: '#f4f7fa' },
  header: { alignItems: 'center', flexDirection: 'row', justifyContent: 'space-between', paddingHorizontal: 18, paddingVertical: 14 },
  back: { color: '#0067a8', fontSize: 16, fontWeight: '700' },
  title: { color: '#17212b', fontSize: 22, fontWeight: '800' },
  new: { color: '#0067a8', fontWeight: '800' },
  tabs: { flexDirection: 'row', marginHorizontal: 16, backgroundColor: '#e7edf2', borderRadius: 12, padding: 3 },
  tab: { flex: 1, alignItems: 'center', borderRadius: 9, paddingVertical: 9 },
  tabActive: { backgroundColor: '#fff' },
  tabText: { color: '#63717e', fontSize: 12, fontWeight: '700' },
  tabTextActive: { color: '#0067a8' },
  list: { padding: 16, flexGrow: 1 },
  card: { backgroundColor: '#fff', borderRadius: 14, marginBottom: 10, padding: 16 },
  cardTop: { alignItems: 'center', flexDirection: 'row', justifyContent: 'space-between' },
  cardTitle: { color: '#17212b', flex: 1, fontSize: 17, fontWeight: '800' },
  preview: { color: '#586775', fontSize: 14, marginTop: 5 },
  date: { color: '#87939e', fontSize: 11, marginTop: 8 },
  badge: { backgroundColor: '#0067a8', borderRadius: 12, color: '#fff', minWidth: 24, overflow: 'hidden', paddingHorizontal: 7, paddingVertical: 3, textAlign: 'center' },
  mentionUnread: { color: '#0067a8', fontSize: 12, fontWeight: '800', marginTop: 8 },
  empty: { color: '#687683', marginTop: 40, textAlign: 'center' },
  error: { color: '#a12622', marginHorizontal: 18, marginTop: 10 },
  ticketPanel: { backgroundColor: '#fff', borderRadius: 16, margin: 16, padding: 22 },
  ticketTitle: { color: '#17212b', fontSize: 20, fontWeight: '800' },
  primaryButton: { alignItems: 'center', backgroundColor: '#0067a8', borderRadius: 12, marginTop: 18, padding: 14 },
  primaryText: { color: '#fff', fontWeight: '800' },
  disabled: { opacity: 0.45 },
  modalBackdrop: { backgroundColor: 'rgba(0,0,0,0.35)', flex: 1, justifyContent: 'flex-end' },
  modalCard: { backgroundColor: '#f7f9fb', borderTopLeftRadius: 22, borderTopRightRadius: 22, maxHeight: '85%', padding: 20 },
  modalTitle: { fontSize: 21, fontWeight: '800' },
  close: { color: '#0067a8', fontWeight: '700' },
  modeRow: { flexDirection: 'row', marginTop: 18 },
  mode: { backgroundColor: '#e7edf2', borderRadius: 9, marginRight: 8, paddingHorizontal: 18, paddingVertical: 9 },
  modeActive: { backgroundColor: '#bde2f7' },
  input: { backgroundColor: '#fff', borderColor: '#d5dde4', borderRadius: 10, borderWidth: 1, marginTop: 14, padding: 12 },
  people: { marginTop: 12 },
  person: { backgroundColor: '#fff', borderRadius: 10, marginBottom: 7, padding: 12 },
  personSelected: { backgroundColor: '#e3f4fd', borderColor: '#61acd3', borderWidth: 1 },
  personName: { color: '#17212b', fontWeight: '700' },
  personEmail: { color: '#72808c', fontSize: 12, marginTop: 2 },
});
