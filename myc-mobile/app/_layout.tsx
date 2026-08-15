import { Stack } from 'expo-router';
import { SafeAreaProvider } from 'react-native-safe-area-context';

import { AuthProvider } from '@/src/auth/AuthProvider';
import { NotificationSyncProvider } from '@/src/notifications/NotificationSyncProvider';

export default function RootLayout() {
  return (
    <SafeAreaProvider>
      <AuthProvider>
        <NotificationSyncProvider>
          <Stack
            screenOptions={{
              headerShown: false,
            }}
          />
        </NotificationSyncProvider>
      </AuthProvider>
    </SafeAreaProvider>
  );
}
