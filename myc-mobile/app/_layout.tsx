import { Stack } from 'expo-router';
import { SafeAreaProvider } from 'react-native-safe-area-context';

import { AuthProvider } from '@/src/auth/AuthProvider';
import { CommunicationsProvider } from '@/src/communications/CommunicationsProvider';
import { NotificationSyncProvider } from '@/src/notifications/NotificationSyncProvider';
import { RealtimeProvider } from '@/src/realtime/RealtimeProvider';

export default function RootLayout() {
  return (
    <SafeAreaProvider>
      <AuthProvider>
        <RealtimeProvider>
          <CommunicationsProvider>
            <NotificationSyncProvider>
              <Stack
                screenOptions={{
                  headerShown: false,
                }}
              />
            </NotificationSyncProvider>
          </CommunicationsProvider>
        </RealtimeProvider>
      </AuthProvider>
    </SafeAreaProvider>
  );
}
