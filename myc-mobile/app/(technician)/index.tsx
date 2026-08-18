import { Redirect, router } from 'expo-router';
import { useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Pressable,
  SafeAreaView,
  StyleSheet,
  Text,
  View,
} from 'react-native';

import { useAuth } from '@/src/auth/AuthProvider';
import { useCommunications } from '@/src/communications/CommunicationsProvider';
import { useNotificationSync } from '@/src/notifications/NotificationSyncProvider';
import { apiUrl } from '@/src/api/client';
import { hasPermission } from '@/src/permissions/permissions';
import type { OperationalTicket } from '@/src/types/operational-ticket';

export default function TechnicianHome() {
  const { authorizedFetch, isLoading, user, logout } = useAuth();
  const { unreadCount } = useNotificationSync();
  const { unreadCount: communicationUnreadCount } = useCommunications();

  const [pendingTickets, setPendingTickets] = useState<number | null>(null);

  useEffect(() => {
    if (!user || !hasPermission(user.permissions, 'tickets.view_own')) return;

    authorizedFetch(
      apiUrl('/mobile/v1/technician/tickets?status=pending&limit=25')
    )
      .then(async (response) =>
        response.ok
          ? (response.json() as Promise<OperationalTicket[]>)
          : []
      )
      .then((tickets) => setPendingTickets(tickets.length))
      .catch(() => setPendingTickets(null));
  }, [authorizedFetch, user]);

  if (isLoading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator />
      </View>
    );
  }

  if (!user) {
    return <Redirect href="/(auth)/login" />;
  }

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.content}>
        <Text style={styles.eyebrow}>MYC · Área técnica</Text>

        <Text style={styles.title}>Hola, {user.full_name}</Text>

        <Pressable
          style={styles.bell}
          onPress={() => router.push('/(technician)/notifications')}
        >
          <Text style={styles.bellText}>
            🔔 Notificaciones
            {unreadCount ? ` · ${unreadCount}` : ''}
          </Text>
        </Pressable>

        <Pressable
          style={styles.module}
          onPress={() => router.push('/(technician)/work-orders')}
        >
          <Text style={styles.moduleTitle}>OT&apos;s</Text>
          <Text style={styles.moduleText}>
            Crear y cerrar órdenes de trabajo LAB
          </Text>
        </Pressable>

        <Pressable
          style={styles.module}
          onPress={() => router.push('/(technician)/communications')}
        >
          <Text style={styles.moduleTitle}>
            Comunicaciones
            {communicationUnreadCount
              ? ` · ${communicationUnreadCount}`
              : ''}
          </Text>

          <Text style={styles.moduleText}>
            Mensajes, menciones y Tickets en tiempo real
          </Text>
        </Pressable>

        {hasPermission(user.permissions, 'tickets.view_own') && (
          <Pressable
            style={styles.module}
            onPress={() => router.push('/(technician)/tickets')}
          >
            <Text style={styles.moduleTitle}>Tickets</Text>

            <Text style={styles.moduleText}>
              {pendingTickets === null
                ? 'Solicitudes operativas'
                : `${pendingTickets} pendiente${
                    pendingTickets === 1 ? '' : 's'
                  }`}
            </Text>
          </Pressable>
        )}

        <Pressable
          onPress={async () => {
            await logout();
            router.replace('/(public)');
          }}
        >
          <Text style={styles.logout}>Cerrar sesión</Text>
        </Pressable>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  center: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },

  container: {
    flex: 1,
    backgroundColor: '#f4f7fa',
  },

  content: {
    flex: 1,
    padding: 24,
  },

  eyebrow: {
    color: '#0067a8',
    fontSize: 14,
    fontWeight: '700',
    marginTop: 20,
  },

  title: {
    fontSize: 30,
    fontWeight: '800',
    marginBottom: 28,
    marginTop: 8,
  },

  bell: {
    alignSelf: 'flex-start',
    marginBottom: 16,
  },

  bellText: {
    color: '#0067a8',
    fontSize: 16,
    fontWeight: '800',
  },

  module: {
    backgroundColor: '#fff',
    borderRadius: 14,
    marginBottom: 14,
    padding: 20,
    shadowColor: '#000',
    shadowOpacity: 0.08,
    shadowRadius: 8,
  },

  moduleTitle: {
    color: '#0067a8',
    fontSize: 24,
    fontWeight: '800',
  },

  moduleText: {
    color: '#51606f',
    fontSize: 15,
    marginTop: 4,
  },

  logout: {
    color: '#9b1c1c',
    fontSize: 16,
    fontWeight: '600',
    marginTop: 32,
  },
});