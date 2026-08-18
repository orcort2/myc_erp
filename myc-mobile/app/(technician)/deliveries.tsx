import { Redirect, router } from 'expo-router';
import { useCallback, useEffect, useState } from 'react';
import { ActivityIndicator, Pressable, SafeAreaView, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';

import { apiUrl, readApiError } from '@/src/api/client';
import { useAuth } from '@/src/auth/AuthProvider';
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
    <Pressable onPress={() => router.back()}><Text style={styles.back}>‹ Inicio</Text></Pressable>
    <Text style={styles.eyebrow}>MYC Mobile · Venta</Text><Text style={styles.title}>Entregas asignadas</Text>
    {error ? <Text style={styles.error}>{error}</Text> : null}
    {items.map((item) => <View style={styles.card} key={item.id}>
      <Text style={styles.cardTitle}>Entrega #{item.id} · ETS {item.service_order_id}</Text>
      <Text style={styles.meta}>{item.lines.reduce((sum, line) => sum + line.quantity, 0)} unidad(es) · {item.status === 'scheduled' ? 'Agendada' : 'Pendiente de aceptación'}</Text>
      <Text style={styles.address}>{JSON.stringify(item.delivery_address || {})}</Text>
      {item.status === 'technician_requested' ? <Pressable disabled={busy} style={styles.primary} onPress={() => action(`/mobile/v1/technician/sale-deliveries/${item.id}/accept`, { scheduled_for: new Date().toISOString() })}><Text style={styles.primaryText}>Aceptar y agendar ahora</Text></Pressable> : <>
        <TextInput onChangeText={setReceiver} placeholder="Nombre de quien recibe" style={styles.input} value={receiver} />
        <TextInput onChangeText={setEvidence} placeholder="Evidencia / referencia de entrega" style={styles.input} value={evidence} />
        <Pressable disabled={busy || !receiver.trim() || !evidence.trim()} style={styles.primary} onPress={() => action(`/mobile/v1/technician/sale-deliveries/${item.id}/receive`, { receiver_name: receiver, evidence: { note: evidence } })}><Text style={styles.primaryText}>Confirmar entrega</Text></Pressable>
      </>}
    </View>)}
    {!items.length ? <Text style={styles.empty}>No tienes entregas de Venta pendientes.</Text> : null}
  </ScrollView></SafeAreaView>;
}

const styles = StyleSheet.create({ center:{flex:1,alignItems:'center',justifyContent:'center'},container:{flex:1,backgroundColor:'#f4f7fa'},content:{padding:24},back:{color:'#0067a8',fontWeight:'700',marginBottom:18},eyebrow:{color:'#0067a8',fontWeight:'700'},title:{fontSize:28,fontWeight:'800',marginBottom:18,marginTop:5},error:{backgroundColor:'#feecec',color:'#9b1c1c',padding:12,borderRadius:10,marginBottom:12},card:{backgroundColor:'#fff',borderRadius:14,padding:18,marginBottom:14},cardTitle:{fontSize:18,fontWeight:'800'},meta:{color:'#51606f',marginTop:5},address:{color:'#51606f',marginVertical:12},input:{borderColor:'#cad4dd',borderWidth:1,borderRadius:9,padding:12,marginTop:8},primary:{backgroundColor:'#0067a8',borderRadius:9,padding:13,marginTop:12},primaryText:{color:'#fff',fontWeight:'800',textAlign:'center'},empty:{color:'#51606f',textAlign:'center',marginTop:30}});
