import Constants from 'expo-constants';
import { router } from 'expo-router';
import { useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  Image,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { useAuth } from '@/src/auth/AuthProvider';

const appVersion = Constants.expoConfig?.version;

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
      Alert.alert(
        'No fue posible iniciar sesión',
        error instanceof Error ? error.message : 'Intenta nuevamente',
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <SafeAreaView edges={['top', 'right', 'bottom', 'left']} style={styles.safeArea}>
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        style={styles.keyboardView}
      >
        <ScrollView
          bounces={false}
          contentContainerStyle={styles.scrollContent}
          keyboardShouldPersistTaps="handled"
        >
          <View style={styles.main}>
            <Image
              accessibilityLabel="Logotipo de MYC"
              resizeMode="cover"
              source={require('../../assets/images/splash-icon.png')}
              style={styles.logo}
            />

            <Text style={styles.title}>Bienvenido a MYC</Text>
            <Text style={styles.description}>Ingresa tus credenciales para continuar</Text>

            <View style={styles.form}>
              <TextInput
                autoCapitalize="none"
                autoComplete="email"
                editable={!submitting}
                keyboardType="email-address"
                onChangeText={setEmail}
                placeholder="Correo electrónico"
                placeholderTextColor="#8A8F98"
                returnKeyType="next"
                style={styles.input}
                value={email}
              />
              <TextInput
                autoCapitalize="none"
                autoComplete="current-password"
                editable={!submitting}
                onChangeText={setPassword}
                onSubmitEditing={submit}
                placeholder="Contraseña"
                placeholderTextColor="#8A8F98"
                returnKeyType="done"
                secureTextEntry
                style={styles.input}
                value={password}
              />

              <Pressable
                accessibilityRole="button"
                disabled={submitting || !email || !password}
                onPress={submit}
                style={({ pressed }) => [
                  styles.button,
                  pressed && styles.buttonPressed,
                  submitting && styles.buttonSubmitting,
                ]}
              >
                {submitting ? (
                  <ActivityIndicator color="#FFFFFF" />
                ) : (
                  <Text style={styles.buttonText}>Iniciar sesión</Text>
                )}
              </Pressable>

              <Pressable
                accessibilityHint="La recuperación de contraseña todavía no está disponible"
                accessibilityRole="button"
                accessibilityState={{ disabled: true }}
                disabled
                style={styles.forgotPassword}
              >
                <Text style={styles.forgotPasswordText}>¿Olvidaste tu contraseña?</Text>
              </Pressable>
            </View>
          </View>

          <Text style={styles.version}>
            MYC Mobile{appVersion ? ` · v${appVersion}` : ''}
          </Text>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    backgroundColor: '#ffffff',
    flex: 1,
  },
  keyboardView: {
    flex: 1,
  },
  scrollContent: {
    flexGrow: 1,
    paddingHorizontal: 24,
  },
  main: {
    alignItems: 'center',
    paddingTop: 28,
    width: '100%',
  },
  logo: {
    height: 150,
    width: 240,
  },
  title: {
    color: '#090909',
    fontSize: 24,
    fontWeight: '700',
    lineHeight: 30,
    textAlign: 'center',
  },
  description: {
    color: '#2F3135',
    fontSize: 15,
    fontWeight: '400',
    lineHeight: 20,
    marginTop: 18,
    textAlign: 'center',
  },
  form: {
    marginTop: 34,
    maxWidth: 480,
    width: '100%',
  },
  input: {
    backgroundColor: '#FFFFFF',
    borderColor: '#C4C5C8',
    borderRadius: 10,
    borderWidth: 1,
    color: '#17191C',
    fontSize: 16,
    height: 52,
    marginBottom: 15,
    paddingHorizontal: 16,
  },
  button: {
    alignItems: 'center',
    backgroundColor: '#003DA5',
    borderRadius: 10,
    height: 52,
    justifyContent: 'center',
    marginTop: 13,
  },
  buttonPressed: {
    opacity: 0.9,
  },
  buttonSubmitting: {
    opacity: 0.82,
  },
  buttonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '700',
  },
  forgotPassword: {
    alignSelf: 'center',
    marginTop: 17,
    paddingHorizontal: 8,
    paddingVertical: 2,
  },
  forgotPasswordText: {
    color: '#003DA5',
    fontSize: 14,
    fontWeight: '600',
  },
  version: {
    color: '#111111',
    fontSize: 12,
    fontWeight: '600',
    marginTop: 'auto',
    paddingBottom: 22,
    paddingTop: 36,
    textAlign: 'center',
  },
});
