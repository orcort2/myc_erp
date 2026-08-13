import { Redirect, router } from 'expo-router';
import { ActivityIndicator, Pressable, SafeAreaView, StyleSheet, Text, View } from 'react-native';

import { useAuth } from '@/src/auth/AuthProvider';

export default function TechnicianHome() {
  const { isLoading, user, logout } = useAuth();
  if (isLoading) return <View style={styles.center}><ActivityIndicator /></View>;
  if (!user) return <Redirect href="/(auth)/login" />;
  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.content}>
        <Text style={styles.eyebrow}>MYC · Área técnica</Text>
        <Text style={styles.title}>Hola, {user.full_name}</Text>
        <Pressable style={styles.module} onPress={() => router.push('/(technician)/work-orders')}>
          <Text style={styles.moduleTitle}>OT&apos;s</Text>
          <Text style={styles.moduleText}>Crear y cerrar órdenes de trabajo LAB</Text>
        </Pressable>
        <Pressable onPress={async () => { await logout(); router.replace('/(public)'); }}>
          <Text style={styles.logout}>Cerrar sesión</Text>
        </Pressable>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  center: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  container: { flex: 1, backgroundColor: '#f4f7fa' },
  content: { flex: 1, padding: 24 },
  eyebrow: { color: '#0067a8', fontSize: 14, fontWeight: '700', marginTop: 20 },
  title: { fontSize: 30, fontWeight: '800', marginBottom: 28, marginTop: 8 },
  module: { backgroundColor: '#fff', borderRadius: 14, padding: 20, shadowColor: '#000', shadowOpacity: 0.08, shadowRadius: 8 },
  moduleTitle: { color: '#0067a8', fontSize: 24, fontWeight: '800' },
  moduleText: { color: '#51606f', fontSize: 15, marginTop: 4 },
  logout: { color: '#9b1c1c', fontSize: 16, fontWeight: '600', marginTop: 32 },
});
