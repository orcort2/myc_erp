import { Link } from 'expo-router';
import { SafeAreaView, StyleSheet, Text, View } from 'react-native';

export default function PublicHomeScreen() {
  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.content}>
        <Text style={styles.brand}>MYC</Text>

        <Text style={styles.title}>
          Sistema de Gestión Empresarial
        </Text>

        <Text style={styles.description}>
          Bienvenido a la aplicación oficial de MYC.
        </Text>

        <Link href="/(auth)/login" style={styles.login}>
          Iniciar sesión
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
  brand: {
    fontSize: 18,
    fontWeight: '700',
    marginBottom: 12,
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
  login: {
    fontSize: 18,
    fontWeight: '600',
  },
});
