import { Redirect } from 'expo-router';
import { useCallback, useEffect, useState } from 'react';
import { ActivityIndicator, SafeAreaView, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';

import { apiUrl, readApiError } from '@/src/api/client';
import { useAuth } from '@/src/auth/AuthProvider';
import { AlertBanner, BackButton, Card, EmptyState, PrimaryButton } from '@/src/design/primitives';
import { colors, radius, spacing, typography } from '@/src/design/tokens';
import type { SaleDelivery } from '@/src/types/sale-delivery';

export default function SaleDeliveriesScreen() {
  const { authorizedFetch, isLoading, user } = useAuth();
  const [items, setItems] = useState<SaleDelivery[]>([]);
  const [receiver, setReceiver] = useState('');
  const [evidence, setEvidence] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    const response = await authorizedFetch(apiUrl('/mobile/v1/technician/sale-deliveries'));
    if (!response.ok) throw new Error(await readApiError(response));
    setItems(await response.json() as SaleDelivery[]);
  }, [authorizedFetch]);

  useEffect(() => { if (user) load().catch((requestError) => setError(requestError.message)); }, [load, user]);

  async function action(path: string, body: object) {
    setBusy(true); setError('');
    try {
      const response = await authorizedFetch(apiUrl(path), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
      if (!response.ok) throw new Error(await readApiError(response));
      await load(); setReceiver(''); setEvidence('');
    } catch (requestError) { setError(requestError instanceof Error ? requestError.message : 'No fue posible actualizar la entrega'); }
    finally { setBusy(false); }
  }

  if (isLoading) return <View style={styles.center}><ActivityIndicator /></View>;
  if (!user) return <Redirect href="/(auth)/login" />;
  return <SafeAreaView style={styles.container}><ScrollView contentContainerStyle={styles.content}>
    <BackButton />
    <View style={styles.headerBlock}>
      <Text style={styles.eyebrow}>MYC Mobile · Venta</Text>
      <Text style={styles.title}>Entregas asignadas</Text>
    </View>
    {error ? <AlertBanner tone="danger">{error}</AlertBanner> : null}
    <View style={styles.list}>
      {items.map((item) => <Card key={item.id}>
        <Text style={styles.cardTitle}>Entrega #{item.id} · ETS {item.service_order_id}</Text>
        <Text style={styles.meta}>{item.lines.reduce((sum, line) => sum + line.quantity, 0)} unidad(es) · {item.status === 'scheduled' ? 'Agendada' : 'Pendiente de aceptación'}</Text>
        <Text style={styles.address}>{JSON.stringify(item.delivery_address || {})}</Text>
        {item.status === 'technician_requested' ? (
          <PrimaryButton disabled={busy} label="Aceptar y agendar ahora" onPress={() => action(`/mobile/v1/technician/sale-deliveries/${item.id}/accept`, { scheduled_for: new Date().toISOString() })} />
        ) : (
          <View>
            <TextInput onChangeText={setReceiver} placeholder="Nombre de quien recibe" style={styles.input} value={receiver} />
            <TextInput onChangeText={setEvidence} placeholder="Evidencia / referencia de entrega" style={[styles.input, styles.fieldGap]} value={evidence} />
            <View style={styles.actionGap}>
              <PrimaryButton disabled={busy || !receiver.trim() || !evidence.trim()} label="Confirmar entrega" onPress={() => action(`/mobile/v1/technician/sale-deliveries/${item.id}/receive`, { receiver_name: receiver, evidence: { type: 'technician_attestation', note: evidence } })} />
            </View>
          </View>
        )}
      </Card>)}
      {!items.length ? <EmptyState title="Sin entregas" description="No tienes entregas de Venta pendientes." /> : null}
    </View>
  </ScrollView></SafeAreaView>;
}

const styles = StyleSheet.create({
  center: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  container: { flex: 1, backgroundColor: colors.background },
  content: { padding: spacing.lg },
  headerBlock: { gap: spacing.xs, marginTop: spacing.md, marginBottom: spacing.lg },
  eyebrow: { color: colors.primary, fontWeight: '700' },
  title: { ...typography.title, fontSize: 28 },
  list: { gap: spacing.md },
  cardTitle: { fontSize: 18, fontWeight: '800', color: colors.text },
  meta: { color: colors.textMuted, marginTop: spacing.xs },
  address: { color: colors.textMuted, marginTop: spacing.sm, marginBottom: spacing.md },
  input: { borderColor: colors.borderStrong, borderWidth: 1, borderRadius: radius.md, padding: spacing.md },
  fieldGap: { marginTop: spacing.sm },
  actionGap: { marginTop: spacing.md },
});
