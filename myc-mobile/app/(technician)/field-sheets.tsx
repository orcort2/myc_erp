import { router } from 'expo-router';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { Pressable, RefreshControl, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { useAuth } from '@/src/auth/AuthProvider';
import { ApiError, apiUrl, readApiErrorDetail } from '@/src/api/client';
import { Card, EmptyState, LoadingState, ReadOnlyField, StatusBadge } from '@/src/design/primitives';
import { colors, spacing } from '@/src/design/tokens';
import {
  groupTrayEntriesByBucket,
  trayEntryFromApi,
  type FieldSheetTrayBucket,
  type FieldSheetTrayEntry,
  type LabFieldSheetTrayApiPage,
} from '@/src/services/field-sheets-tray';

const BUCKET_ORDER: { key: FieldSheetTrayBucket; title: string; tone: 'warning' | 'info' | 'success' }[] = [
  { key: 'pending', title: 'Pendientes', tone: 'warning' },
  { key: 'in_progress', title: 'En captura', tone: 'info' },
  { key: 'completed', title: 'Completadas', tone: 'success' },
];

/**
 * Fase 6: bandeja Mobile específica de Hojas de Campo -- reutiliza los
 * endpoint agregado LAB específico (una sola llamada paginable, sin fan-out
 * por OT/equipo). "Continuar/Abrir" navega a la pantalla de OT ya
 * existente (Mesa Técnica), no duplica esa captura aquí.
 */
export default function FieldSheetsTray() {
  const { authorizedFetch, user } = useAuth();
  const [entries, setEntries] = useState<FieldSheetTrayEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const request = useCallback(async <T,>(path: string, init?: RequestInit): Promise<T> => {
    const response = await authorizedFetch(apiUrl(path), init);
    if (!response.ok) {
      const detail = await readApiErrorDetail(response);
      throw new ApiError(detail.message, response.status, detail.missingFields);
    }
    return response.json() as Promise<T>;
  }, [authorizedFetch]);

  const load = useCallback(async (isRefresh: boolean) => {
    if (isRefresh) setRefreshing(true); else setLoading(true);
    setError(null);
    try {
      const page = await request<LabFieldSheetTrayApiPage>(
        '/mobile/v1/technician/lab-field-sheets?offset=0&limit=100',
      );
      setEntries(page.items.map(trayEntryFromApi));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No fue posible cargar la bandeja de Hojas de Campo');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [request]);

  useEffect(() => { if (user) load(false); }, [load, user]);

  const buckets = useMemo(() => groupTrayEntriesByBucket(entries), [entries]);
  const totalEntries = entries.length;

  return (
    <SafeAreaView edges={['top', 'right', 'bottom', 'left']} style={styles.screen}>
      <View style={styles.header}>
        <Text style={styles.eyebrow}>MYC · LAB</Text>
        <Text style={styles.title}>Hojas de Campo</Text>
      </View>

      {loading ? <LoadingState label="Cargando bandeja…" /> : (
        <ScrollView
          contentContainerStyle={styles.content}
          refreshControl={<RefreshControl onRefresh={() => load(true)} refreshing={refreshing} />}
        >
          {error && <Text style={styles.error}>{error}</Text>}
          {!error && totalEntries === 0 && (
            <EmptyState
              description="No hay equipos con captura técnica pendiente, en curso o completada en tus OT abiertas."
              title="Nada por aquí todavía"
            />
          )}
          {BUCKET_ORDER.map(({ key, title, tone }) => {
            const bucketEntries = buckets[key];
            if (bucketEntries.length === 0) return null;
            return (
              <View key={key} style={styles.bucket}>
                <View style={styles.bucketHeader}>
                  <Text style={styles.bucketTitle}>{title}</Text>
                  <StatusBadge label={String(bucketEntries.length)} tone={tone} />
                </View>
                {bucketEntries.map((entry) => (
                  <Card key={`${entry.workOrderId}-${entry.equipmentId}`}>
                    <Text style={styles.cardTitle}>{entry.instrument}</Text>
                    <Text style={styles.cardMeta}>OT {entry.workOrderFolio} · {entry.templateName ?? 'Sin plantilla seleccionada'}</Text>
                    <ReadOnlyField label="Folio" value={entry.certificateFolio ?? 'Sin resolver'} />
                    <ReadOnlyField label="Cliente documental" value={entry.documentaryClient} />
                    {entry.progress && (
                      <Text style={styles.cardProgress}>{entry.progress.completed} / {entry.progress.total} resultados completos</Text>
                    )}
                    <Pressable
                      onPress={() => router.push({ pathname: '/(technician)/work-orders', params: { workOrderId: String(entry.workOrderId) } })}
                      style={styles.action}
                    >
                      <Text style={styles.actionText}>{entry.fieldSheetId ? 'Continuar' : 'Abrir'}</Text>
                    </Pressable>
                  </Card>
                ))}
              </View>
            );
          })}
        </ScrollView>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.background },
  header: { padding: spacing.lg, paddingBottom: spacing.sm },
  eyebrow: { color: colors.accent, fontSize: 12, fontWeight: '800', letterSpacing: 1 },
  title: { color: colors.text, fontSize: 26, fontWeight: '800', marginTop: spacing.xs },
  content: { padding: spacing.lg, paddingTop: 0, gap: spacing.md },
  error: { color: colors.danger, fontWeight: '700', marginBottom: spacing.sm },
  bucket: { gap: spacing.sm, marginBottom: spacing.md },
  bucketHeader: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm },
  bucketTitle: { color: colors.text, fontSize: 17, fontWeight: '800' },
  cardTitle: { color: colors.text, fontSize: 16, fontWeight: '800' },
  cardMeta: { color: colors.textSubtle, marginBottom: spacing.xs },
  cardProgress: { color: colors.textMuted, fontSize: 13, fontWeight: '700' },
  action: { alignItems: 'center', backgroundColor: colors.primary, borderRadius: 10, marginTop: spacing.sm, padding: spacing.md },
  actionText: { color: '#fff', fontWeight: '800' },
});
