import { Redirect } from 'expo-router';
import { useEffect, useState } from 'react';
import { ActivityIndicator, Alert, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { useAuth } from '@/src/auth/AuthProvider';
import { useDeveloper } from '@/src/auth/DeveloperProvider';

// DEV-0: placeholder only -- none of these tools exist yet (DEV-1+). This
// screen exists to prove the Developer authority end-to-end: biometric
// unlock, TTL countdown, expiration warning and lock.
const PLACEHOLDER_TOOLS = ['Base de datos', 'Terminal', 'Logs', 'Servicios', 'Git'];

function formatCountdown(remainingSeconds: number): string {
  const minutes = Math.floor(remainingSeconds / 60);
  const seconds = remainingSeconds % 60;
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
}

export default function DeveloperScreen() {
  const { user, isLoading } = useAuth();
  const {
    isDeveloperAvailable,
    isDeveloperUnlocked,
    remainingSeconds,
    showExpirationWarning,
    unlockDeveloper,
    lockDeveloper,
    dismissExpirationWarning,
  } = useDeveloper();

  const [unlocking, setUnlocking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Exactly one Alert per expiration cycle -- DeveloperProvider only flips
  // showExpirationWarning back to true again for a NEW cycle (a fresh
  // unlock), never as a side effect of this screen re-rendering.
  useEffect(() => {
    if (!showExpirationWarning) return;
    Alert.alert(
      'Tu sesión Developer está por finalizar',
      'La terminal y las herramientas Developer quedarán bloqueadas. Los procesos activos podrán continuar temporalmente en el servidor.',
      [
        {
          text: 'Bloquear ahora',
          style: 'destructive',
          onPress: () => {
            dismissExpirationWarning();
            lockDeveloper();
          },
        },
        {
          text: 'Extender con Face ID',
          onPress: async () => {
            dismissExpirationWarning();
            try {
              await unlockDeveloper();
            } catch {
              Alert.alert('No fue posible extender tu sesión Developer.');
            }
          },
        },
      ],
    );
  }, [showExpirationWarning, dismissExpirationWarning, lockDeveloper, unlockDeveloper]);

  if (isLoading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator />
      </View>
    );
  }

  if (!user) return <Redirect href="/(auth)/login" />;
  if (!isDeveloperAvailable) return <Redirect href="/(technician)" />;

  async function handleUnlock() {
    setError(null);
    setUnlocking(true);
    try {
      await unlockDeveloper();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No fue posible desbloquear Developer');
    } finally {
      setUnlocking(false);
    }
  }

  if (!isDeveloperUnlocked) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.lockedContent}>
          <Text style={styles.lockedTitle}>Developer</Text>
          <Text style={styles.lockedSubtitle}>Acceso protegido</Text>
          {error && <Text style={styles.error}>{error}</Text>}
          <Pressable style={styles.unlockButton} onPress={handleUnlock} disabled={unlocking}>
            <Text style={styles.unlockButtonText}>
              {unlocking ? 'Verificando…' : 'Desbloquear con Face ID'}
            </Text>
          </Pressable>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
        <Text style={styles.title}>Developer Center</Text>
        <Text style={styles.sessionStatus}>
          Sesión activa · {remainingSeconds !== null ? formatCountdown(remainingSeconds) : '--:--'} restantes
        </Text>

        {PLACEHOLDER_TOOLS.map((tool) => (
          <View key={tool} style={styles.module}>
            <Text style={styles.moduleTitle}>{tool}</Text>
            <Text style={styles.moduleText}>Próximamente</Text>
          </View>
        ))}

        <Pressable onPress={() => lockDeveloper()}>
          <Text style={styles.lockText}>Bloquear Developer</Text>
        </Pressable>
      </ScrollView>
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
    paddingHorizontal: 20,
    paddingTop: 16,
    paddingBottom: 32,
  },

  lockedContent: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 32,
  },

  lockedTitle: {
    fontSize: 30,
    fontWeight: '800',
  },

  lockedSubtitle: {
    color: '#51606f',
    fontSize: 16,
    fontWeight: '600',
    marginTop: 6,
    marginBottom: 28,
  },

  error: {
    color: '#9b1c1c',
    fontSize: 14,
    marginBottom: 16,
    textAlign: 'center',
  },

  unlockButton: {
    backgroundColor: '#0067a8',
    borderRadius: 14,
    paddingHorizontal: 28,
    paddingVertical: 16,
  },

  unlockButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '700',
  },

  title: {
    fontSize: 30,
    fontWeight: '800',
    marginBottom: 6,
    marginTop: 8,
  },

  sessionStatus: {
    color: '#0067a8',
    fontSize: 14,
    fontWeight: '700',
    marginBottom: 20,
  },

  module: {
    backgroundColor: '#fff',
    borderRadius: 14,
    marginBottom: 10,
    padding: 16,
    shadowColor: '#000',
    shadowOpacity: 0.08,
    shadowRadius: 8,
  },

  moduleTitle: {
    color: '#0067a8',
    fontSize: 22,
    fontWeight: '800',
  },

  moduleText: {
    color: '#51606f',
    fontSize: 15,
    marginTop: 4,
  },

  lockText: {
    color: '#9b1c1c',
    fontSize: 16,
    fontWeight: '600',
    marginTop: 20,
  },
});
