import { Stack } from 'expo-router';
import { SafeAreaProvider } from 'react-native-safe-area-context';

import { AuthProvider } from '@/src/auth/AuthProvider';
import { DeveloperProvider } from '@/src/auth/DeveloperProvider';
import { CommunicationsProvider } from '@/src/communications/CommunicationsProvider';
import { NotificationSyncProvider } from '@/src/notifications/NotificationSyncProvider';
import { RealtimeProvider } from '@/src/realtime/RealtimeProvider';
import { setEvidenceMediaProvider } from '@/src/services/technical-report-media';
import { expoEvidenceMediaProvider } from '@/src/services/technical-report-media-expo';

// Cámara/galería de evidencia de reportes técnicos (requiere build nativo con
// expo-image-picker y expo-image-manipulator).
setEvidenceMediaProvider(expoEvidenceMediaProvider);

export default function RootLayout() {
  return (
    <SafeAreaProvider>
      <AuthProvider>
        <DeveloperProvider>
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
        </DeveloperProvider>
      </AuthProvider>
    </SafeAreaProvider>
  );
}
