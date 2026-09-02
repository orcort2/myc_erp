import { useLocalSearchParams } from 'expo-router';
import { useEffect, useMemo, useRef, useState } from 'react';
import {
  FlatList,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  SafeAreaView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';

import { useAuth } from '@/src/auth/AuthProvider';
import { useCommunications } from '@/src/communications/CommunicationsProvider';
import { BackButton } from '@/src/design/primitives';
import { deliveryState } from '@/src/communications/message-state';
import { fetchDirectory } from '@/src/services/communications';
import type { CommunicationDirectory, MentionDraft } from '@/src/types/communication';

export default function ConversationScreen() {
  const params = useLocalSearchParams<{ id: string }>();
  const conversationId = Number(params.id);
  const { authorizedFetch, user } = useAuth();
  const {
    beforeCursorByConversation,
    closeConversation,
    conversations,
    loadOlder,
    messagesByConversation,
    notifyTyping,
    openConversation,
    retryMessage,
    sendMessage,
    typingByConversation,
  } = useCommunications();
  const [body, setBody] = useState('');
  const [mentions, setMentions] = useState<MentionDraft[]>([]);
  const [directory, setDirectory] = useState<CommunicationDirectory | null>(null);
  const listRef = useRef<FlatList>(null);
  const conversation = conversations.find((item) => item.id === conversationId);
  const messages = messagesByConversation[conversationId] ?? [];
  const typing = typingByConversation[conversationId] ?? [];

  useEffect(() => {
    if (!Number.isFinite(conversationId)) return;
    openConversation(conversationId).catch(() => undefined);
    fetchDirectory(authorizedFetch).then(setDirectory).catch(() => undefined);
    return () => closeConversation(conversationId);
  }, [authorizedFetch, closeConversation, conversationId, openConversation]);

  const mentionQuery = useMemo(() => {
    const match = body.match(/(?:^|\s)@([^\s@]*)$/);
    return match ? match[1].toLocaleLowerCase() : null;
  }, [body]);
  const participantIds = new Set(conversation?.participants.map((item) => item.id) ?? []);
  const suggestions = mentionQuery === null ? [] : [
    ...(directory?.users ?? [])
      .filter((person) => participantIds.has(person.id) && person.id !== user?.id)
      .filter((person) => person.full_name.toLocaleLowerCase().includes(mentionQuery))
      .slice(0, 5)
      .map((person) => ({ label: person.full_name, draft: { kind: 'user' as const, user_id: person.id } })),
    ...(directory?.mention_groups ?? [])
      .filter((group) => group.label.toLocaleLowerCase().includes(mentionQuery) || group.key.includes(mentionQuery))
      .slice(0, 3)
      .map((group) => ({
        label: group.key === 'all' ? 'todos' : group.label,
        draft: group.key === 'all'
          ? { kind: 'all' as const }
          : { kind: 'role' as const, key: group.key },
      })),
  ];

  function chooseMention(label: string, draft: MentionDraft) {
    setBody((current) => current.replace(/@[^\s@]*$/, `@${label.replaceAll(' ', '_')} `));
    setMentions((current) => [...current.filter((item) => JSON.stringify(item) !== JSON.stringify(draft)), draft]);
  }

  async function submit() {
    const content = body.trim();
    if (!content) return;
    setBody('');
    const pendingMentions = mentions;
    setMentions([]);
    await sendMessage(conversationId, content, pendingMentions);
    listRef.current?.scrollToEnd({ animated: true });
  }

  return (
    <SafeAreaView style={styles.safe}>
      <KeyboardAvoidingView style={styles.flex} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
        <View style={styles.header}>
          <BackButton label="‹" />
          <View style={styles.heading}>
            <Text numberOfLines={1} style={styles.title}>{conversation?.title ?? 'Conversación'}</Text>
            {!!typing.length && <Text style={styles.typing}>{typing.map((item) => item.full_name).join(' y ')} está escribiendo…</Text>}
          </View>
        </View>
        <FlatList
          ref={listRef}
          data={messages}
          keyExtractor={(item) => item.id > 0 ? `id:${item.id}` : `client:${item.client_message_id}`}
          contentContainerStyle={styles.messages}
          ListHeaderComponent={beforeCursorByConversation[conversationId]
            ? <Pressable onPress={() => loadOlder(conversationId)}><Text style={styles.older}>Cargar mensajes anteriores</Text></Pressable>
            : null}
          onContentSizeChange={() => listRef.current?.scrollToEnd({ animated: false })}
          renderItem={({ item }) => {
            const own = item.sender.id === user?.id;
            const state = user ? deliveryState(item, user.id) : 'sent';
            return (
              <View style={[styles.bubble, own ? styles.ownBubble : styles.otherBubble]}>
                {!own && conversation?.conversation_type === 'group' && <Text style={styles.author}>{item.sender.full_name}</Text>}
                <Text style={styles.body}>{item.body}</Text>
                <View style={styles.metaRow}>
                  <Text style={styles.time}>{new Date(item.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</Text>
                  {own && <Text style={[styles.state, state === 'failed' && styles.failed]}>{state}</Text>}
                </View>
                {state === 'failed' && item.client_message_id && (
                  <Pressable onPress={() => retryMessage(conversationId, item.client_message_id!)}><Text style={styles.retry}>Reintentar</Text></Pressable>
                )}
              </View>
            );
          }}
        />
        {!!suggestions.length && (
          <View style={styles.suggestions}>
            {suggestions.map((suggestion) => (
              <Pressable key={`${suggestion.draft.kind}:${suggestion.label}`} onPress={() => chooseMention(suggestion.label, suggestion.draft)}>
                <Text style={styles.suggestion}>@{suggestion.label}</Text>
              </Pressable>
            ))}
          </View>
        )}
        <View style={styles.composer}>
          <TextInput
            multiline
            style={styles.input}
            placeholder="Escribe un mensaje… Usa @ para mencionar"
            value={body}
            onChangeText={(value) => { setBody(value); if (value.trim()) notifyTyping(conversationId); }}
            maxLength={10000}
          />
          <Pressable style={[styles.send, !body.trim() && styles.disabled]} disabled={!body.trim()} onPress={submit}>
            <Text style={styles.sendText}>Enviar</Text>
          </Pressable>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  safe: { backgroundColor: '#edf2f5', flex: 1 },
  header: { alignItems: 'center', backgroundColor: '#fff', flexDirection: 'row', paddingHorizontal: 16, paddingVertical: 12 },
  heading: { flex: 1 },
  title: { color: '#17212b', fontSize: 18, fontWeight: '800' },
  typing: { color: '#0067a8', fontSize: 12, marginTop: 2 },
  messages: { flexGrow: 1, justifyContent: 'flex-end', padding: 14 },
  older: { color: '#0067a8', fontWeight: '700', marginBottom: 14, textAlign: 'center' },
  bubble: { borderRadius: 14, marginBottom: 9, maxWidth: '82%', paddingHorizontal: 13, paddingVertical: 9 },
  ownBubble: { alignSelf: 'flex-end', backgroundColor: '#d7effc', borderBottomRightRadius: 4 },
  otherBubble: { alignSelf: 'flex-start', backgroundColor: '#fff', borderBottomLeftRadius: 4 },
  author: { color: '#0067a8', fontSize: 12, fontWeight: '800', marginBottom: 3 },
  body: { color: '#17212b', fontSize: 16, lineHeight: 21 },
  metaRow: { alignItems: 'center', flexDirection: 'row', justifyContent: 'flex-end', marginTop: 4 },
  time: { color: '#788590', fontSize: 10 },
  state: { color: '#0067a8', fontSize: 10, marginLeft: 6 },
  failed: { color: '#a12622' },
  retry: { color: '#a12622', fontSize: 12, fontWeight: '800', marginTop: 4, textAlign: 'right' },
  suggestions: { backgroundColor: '#fff', borderTopColor: '#d8e0e6', borderTopWidth: 1, paddingHorizontal: 14, paddingVertical: 6 },
  suggestion: { color: '#0067a8', fontWeight: '700', paddingVertical: 8 },
  composer: { alignItems: 'flex-end', backgroundColor: '#fff', flexDirection: 'row', padding: 10 },
  input: { backgroundColor: '#f0f3f5', borderRadius: 18, flex: 1, maxHeight: 110, minHeight: 42, paddingHorizontal: 14, paddingVertical: 10 },
  send: { backgroundColor: '#0067a8', borderRadius: 18, marginLeft: 8, paddingHorizontal: 15, paddingVertical: 11 },
  sendText: { color: '#fff', fontWeight: '800' },
  disabled: { opacity: 0.4 },
});
