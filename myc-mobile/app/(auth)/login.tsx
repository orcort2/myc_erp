import { Link, router } from 'expo-router';
import { useState } from 'react';
import { ActivityIndicator, Alert, Pressable, SafeAreaView, StyleSheet, Text, TextInput, View } from 'react-native';

import { useAuth } from '@/src/auth/AuthProvider';

export default function LoginScreen() {
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);

  async function submit() {
    if (!email || !password) return;
    setSubmitting(true);
    try {
      await login(email, password);
      router.replace('/(technician)');
    } catch (error) {
      Alert.alert('No fue posible iniciar sesión', error instanceof Error ? error.message : 'Intenta nuevamente');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.content}>
        <Text style={styles.title}>Iniciar sesión</Text>

        <Text style={styles.description}>Acceso interno para personal técnico autorizado.</Text>

        <TextInput
          autoCapitalize="none"
          autoComplete="email"
          keyboardType="email-address"
          onChangeText={setEmail}
          placeholder="Correo"
          style={styles.input}
          value={email}
        />
        <TextInput
          autoCapitalize="none"
          autoComplete="current-password"
          onChangeText={setPassword}
          onSubmitEditing={submit}
          placeholder="Contraseña"
          secureTextEntry
          style={styles.input}
          value={password}
        />
        <Pressable disabled={submitting || !email || !password} onPress={submit} style={styles.button}>
          {submitting ? <ActivityIndicator color="#fff" /> : <Text style={styles.buttonText}>Entrar</Text>}
        </Pressable>

        <Link href="/(public)" style={styles.back}>
          Volver
        </Link>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#ffffff',
  },
  content: {
    flex: 1,
    justifyContent: 'center',
    paddingHorizontal: 24,
  },
  title: {
    fontSize: 32,
    fontWeight: '700',
    marginBottom: 12,
  },
  description: {
    fontSize: 16,
    marginBottom: 32,
  },
  input: { borderColor: '#b9c4d0', borderRadius: 10, borderWidth: 1, fontSize: 17, marginBottom: 12, padding: 14 },
  button: { alignItems: 'center', backgroundColor: '#0067a8', borderRadius: 10, marginBottom: 24, minHeight: 52, justifyContent: 'center' },
  buttonText: { color: '#fff', fontSize: 17, fontWeight: '700' },
  back: {
    fontSize: 18,
    fontWeight: '600',
  },
});
