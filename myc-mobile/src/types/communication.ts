export type CommunicationActor = {
  id: number;
  full_name: string;
  email: string | null;
};

export type CommunicationReceipt = {
  user_id: number;
  delivered_at: string | null;
  read_at: string | null;
};

export type CommunicationMention = {
  mentioned_user_id: number;
  mention_kind: 'user' | 'all' | 'role';
  mention_key: string | null;
  read_at: string | null;
};

export type MessageDeliveryState = 'sending' | 'sent' | 'delivered' | 'read' | 'failed';

export type CommunicationMessage = {
  id: number;
  conversation_id: number;
  client_message_id: string | null;
  sequence: number;
  body: string;
  message_type: string;
  created_at: string;
  edited_at: string | null;
  sender: CommunicationActor;
  receipts: CommunicationReceipt[];
  mentions: CommunicationMention[];
  delivery_state?: MessageDeliveryState;
};

export type CommunicationConversation = {
  id: number;
  conversation_type: 'internal' | 'group' | 'client';
  title: string;
  ticket_id: number | null;
  participants: CommunicationActor[];
  last_message: CommunicationMessage | null;
  last_message_at: string | null;
  latest_sequence: number;
  unread_count: number;
  created_at: string;
};

export type CommunicationConversationDetail = CommunicationConversation & {
  messages: CommunicationMessage[];
  next_before_sequence: number | null;
};

export type CommunicationMessagePage = {
  items: CommunicationMessage[];
  next_before_sequence: number | null;
  latest_sequence: number;
  unread_count: number;
};

export type CommunicationSyncPage = {
  items: CommunicationMessage[];
  latest_sequence: number;
  unread_count: number;
  has_more: boolean;
};

export type CommunicationDirectory = {
  users: CommunicationActor[];
  clients: { id: number; name: string; email: string | null }[];
  mention_groups: { key: string; label: string }[];
};

export type CommunicationMentionInbox = {
  message: CommunicationMessage;
  conversation_title: string;
  read_at: string | null;
};

export type MentionDraft = {
  kind: 'user' | 'all' | 'role';
  user_id?: number;
  key?: string;
};
