import { apiUrl, readApiError } from '@/src/api/client';
import type {
  CommunicationConversation,
  CommunicationConversationDetail,
  CommunicationDirectory,
  CommunicationMentionInbox,
  CommunicationMessage,
  CommunicationMessagePage,
  CommunicationSyncPage,
  MentionDraft,
} from '@/src/types/communication';

export type AuthorizedFetch = (url: string, init?: RequestInit) => Promise<Response>;

async function json<T>(response: Response): Promise<T> {
  if (!response.ok) throw new Error(await readApiError(response));
  return response.json() as Promise<T>;
}

export async function fetchConversations(fetcher: AuthorizedFetch) {
  return json<CommunicationConversation[]>(await fetcher(apiUrl('/communications/conversations')));
}

export async function fetchConversation(fetcher: AuthorizedFetch, id: number) {
  return json<CommunicationConversationDetail>(await fetcher(apiUrl(`/communications/conversations/${id}`)));
}

export async function fetchOlderMessages(
  fetcher: AuthorizedFetch, id: number, beforeSequence: number,
) {
  return json<CommunicationMessagePage>(await fetcher(
    apiUrl(`/communications/conversations/${id}/messages?before_sequence=${beforeSequence}&limit=50`),
  ));
}

export async function syncConversation(
  fetcher: AuthorizedFetch, id: number, afterSequence: number,
) {
  return json<CommunicationSyncPage>(await fetcher(
    apiUrl(`/communications/conversations/${id}/sync?after_sequence=${afterSequence}&limit=200`),
  ));
}

export async function sendMessage(
  fetcher: AuthorizedFetch,
  conversationId: number,
  body: string,
  clientMessageId: string,
  mentions: MentionDraft[],
) {
  return json<CommunicationMessage>(await fetcher(
    apiUrl(`/communications/conversations/${conversationId}/messages`),
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ body, client_message_id: clientMessageId, mentions }),
    },
  ));
}

export async function markMessages(
  fetcher: AuthorizedFetch,
  conversationId: number,
  messageIds: number[],
  state: 'delivered' | 'read',
) {
  if (!messageIds.length) return;
  const response = await fetcher(apiUrl(`/communications/conversations/${conversationId}/receipts`), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ state, message_ids: messageIds }),
  });
  if (!response.ok) throw new Error(await readApiError(response));
}

export async function fetchDirectory(fetcher: AuthorizedFetch) {
  return json<CommunicationDirectory>(await fetcher(apiUrl('/communications/directory')));
}

export async function fetchMentions(fetcher: AuthorizedFetch) {
  return json<CommunicationMentionInbox[]>(await fetcher(apiUrl('/communications/mentions')));
}

export async function createConversation(
  fetcher: AuthorizedFetch,
  payload: Record<string, unknown>,
) {
  return json<CommunicationConversationDetail>(await fetcher(apiUrl('/communications/conversations'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  }));
}
