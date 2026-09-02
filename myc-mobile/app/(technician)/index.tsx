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
import { deriveMobileCapabilities } from '@/src/permissions/mobile-capabilities';
import { actionableRequestCount } from '@/src/requests/request-inbox';
import type { LabWorkOrderGroupRequest } from '@/src/types/lab-work-order';
import type { OperationalTicket } from '@/src/types/operational-ticket';

export default function TechnicianHome() {
  const { authorizedFetch, isLoading, user, logout } = useAuth();
  const { unreadCount } = useNotificationSync();
  const { unreadCount: communicationUnreadCount } = useCommunications();

  const [pendingRequests, setPendingRequests] = useState<number | null>(null);
  const capabilities = deriveMobileCapabilities(user);
  const {
    canCaptureFieldSheets,
    canClaimWorkOrderGroupRequests,
    canCreateWorkOrders,
    canReadTickets,
    canReadWorkOrderGroupRequests,
    canReadWorkOrders,
    canReviewTickets,
    canUseCommunications,
  } = capabilities;

  useEffect(() => {
    if (!user || (!canReviewTickets && !canClaimWorkOrderGroupRequests)) {
      setPendingRequests(0);
      return;
    }
    Promise.all([
      canReviewTickets
        ? authorizedFetch(apiUrl('/mobile/v1/technician/tickets?status=pending&limit=100')).then((response) => response.ok ? response.json() as Promise<OperationalTicket[]> : [])
        : Promise.resolve([] as OperationalTicket[]),
      canClaimWorkOrderGroupRequests
        ? authorizedFetch(apiUrl('/mobile/v1/technician/lab-work-orders/group-requests/review')).then((response) => response.ok ? response.json() as Promise<LabWorkOrderGroupRequest[]> : [])
        : Promise.resolve([] as LabWorkOrderGroupRequest[]),
    ])
      .then(([tickets, groups]) => setPendingRequests(actionableRequestCount(tickets, groups, {
        canReviewTickets,
        canClaimGroups: canClaimWorkOrderGroupRequests,
      })))
      .catch(() => setPendingRequests(null));
  }, [authorizedFetch, canClaimWorkOrderGroupRequests, canReviewTickets, user]);

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
        <Text style={styles.eyebrow}>
          {user.actor_type === 'client' ? 'MYC · Organización vinculada' : 'MYC · Área técnica'}
        </Text>

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

        {canReadWorkOrders && <Pressable
          style={styles.module}
          onPress={() => router.push('/(technician)/work-orders')}
        >
          <Text style={styles.moduleTitle}>OT&apos;s</Text>
          <Text style={styles.moduleText}>
            {canCreateWorkOrders
              ? 'Crear y gestionar órdenes de trabajo LAB'
              : 'Consultar órdenes de trabajo de tu organización'}
          </Text>
        </Pressable>}

        {canCaptureFieldSheets && <Pressable
          style={styles.module}
          onPress={() => router.push('/(technician)/field-sheets')}
        >
          <Text style={styles.moduleTitle}>Hojas de Campo</Text>
          <Text style={styles.moduleText}>Pendientes, en captura y completadas</Text>
        </Pressable>}

        {canUseCommunications && <Pressable
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
        </Pressable>}

        {(canReadTickets || canReadWorkOrderGroupRequests) && (
          <Pressable
            style={styles.module}
            onPress={() => router.push('/(technician)/tickets')}
          >
            <Text style={styles.moduleTitle}>Solicitudes</Text>

            <Text style={styles.moduleText}>
              {pendingRequests === null
                ? 'Solicitudes operativas'
                : `${pendingRequests} pendiente${
                    pendingRequests === 1 ? '' : 's'
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
