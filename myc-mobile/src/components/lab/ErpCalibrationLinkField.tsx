import { useEffect, useState } from 'react';
import { Pressable, StyleSheet, Text, TextInput, View } from 'react-native';

import { AlertBanner, Card, EmptyState, LoadingState } from '@/src/design/primitives';
import { colors, radius, spacing } from '@/src/design/tokens';
import {
  buildErpCandidateQuery,
  describeErpCandidate,
  erpClientMismatchWarning,
  ERP_CANDIDATE_DEBOUNCE_MS,
  ERP_CANDIDATES_PATH,
  shouldSearchErpCandidates,
  type ErpCalibrationCandidate,
} from '@/src/services/lab-erp-calibration';

type Request = <T>(path: string, init?: RequestInit) => Promise<T>;

type Props = {
  request: Request;
  selection: ErpCalibrationCandidate | null;
  onChange(selection: ErpCalibrationCandidate | null): void;
  /** client_name actual del formulario LAB; sólo se compara para advertir. */
  labClientName: string;
};

/**
 * "Vincular con cotización ERP (opcional)": busca en el servidor ETS de
 * calibración con cotización aceptada y permite elegir exactamente uno antes
 * de crear la OT. No sustituye ni toca "Orden de compra / cotización"
 * (texto documental); la selección sólo viaja como `service_order_id`.
 */
export function ErpCalibrationLinkField({ request, selection, onChange, labClientName }: Props) {
  const [term, setTerm] = useState('');
  const [results, setResults] = useState<ErpCalibrationCandidate[]>([]);
  const [resultsTerm, setResultsTerm] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    setError('');
    if (!shouldSearchErpCandidates(term)) {
      setLoading(false);
      setResults([]);
      setResultsTerm('');
      return () => { active = false; };
    }
    const timer = setTimeout(() => {
      setLoading(true);
      const searched = term.trim();
      request<ErpCalibrationCandidate[]>(`${ERP_CANDIDATES_PATH}?${buildErpCandidateQuery(searched)}`)
        .then((rows) => {
          if (!active) return;
          setResults(rows);
          setResultsTerm(searched);
        })
        .catch((caught) => {
          if (active) setError(caught instanceof Error ? caught.message : 'No fue posible buscar cotizaciones.');
        })
        .finally(() => { if (active) setLoading(false); });
    }, ERP_CANDIDATE_DEBOUNCE_MS);
    return () => { active = false; clearTimeout(timer); };
  }, [term, request]);

  if (selection) {
    const summary = describeErpCandidate(selection);
    const warning = erpClientMismatchWarning(labClientName, selection);
    return (
      <View style={styles.selected}>
        <Text style={styles.selectedTitle}>{summary.quotation}</Text>
        <Text style={styles.meta}>{summary.serviceOrder}</Text>
        <Text style={styles.clientLine}>Cliente ERP: {summary.client}</Text>
        {warning ? <AlertBanner tone="warning">{warning}</AlertBanner> : null}
        <Pressable
          accessibilityLabel="Quitar vínculo ERP"
          accessibilityRole="button"
          hitSlop={8}
          onPress={() => onChange(null)}
          style={styles.clearAction}
        >
          <Text style={styles.clearText}>Quitar vínculo</Text>
        </Pressable>
      </View>
    );
  }

  const pending = shouldSearchErpCandidates(term) && (loading || resultsTerm !== term.trim());
  return (
    <Card>
      <TextInput
        accessibilityLabel="Buscar cotización ERP"
        autoCapitalize="none"
        onChangeText={setTerm}
        placeholder="Cotización, ETS o cliente"
        style={styles.search}
        value={term}
      />
      <View style={styles.results}>
        {!shouldSearchErpCandidates(term) ? (
          <EmptyState title="Sin vínculo ERP" description="Opcional. Escribe al menos 2 caracteres para buscar." />
        ) : error ? (
          <AlertBanner tone="danger">{error}</AlertBanner>
        ) : pending ? (
          <LoadingState label="Buscando cotizaciones…" />
        ) : results.length ? (
          <View>
            {results.map((candidate) => {
              const summary = describeErpCandidate(candidate);
              return (
                <Pressable
                  key={candidate.service_order_id}
                  accessibilityRole="button"
                  accessibilityState={{ disabled: !candidate.available }}
                  disabled={!candidate.available}
                  onPress={() => onChange(candidate)}
                  style={({ pressed }) => [
                    styles.row,
                    !candidate.available && styles.rowDisabled,
                    pressed && styles.rowPressed,
                  ]}
                >
                  <Text style={styles.rowTitle}>{summary.quotation}</Text>
                  <Text style={styles.meta}>{summary.serviceOrder} · {summary.client}</Text>
                  <Text style={styles.meta}>{summary.detail}</Text>
                </Pressable>
              );
            })}
          </View>
        ) : (
          <EmptyState title="Sin resultados" description="No hay ETS de calibración aceptados que coincidan." />
        )}
      </View>
    </Card>
  );
}

const styles = StyleSheet.create({
  search: { backgroundColor: '#fff', borderColor: '#b9c8d2', borderRadius: 9, borderWidth: 1, minHeight: 44, paddingHorizontal: 11 },
  results: { marginTop: spacing.sm },
  row: { borderBottomColor: '#e4ebf0', borderBottomWidth: 1, borderRadius: radius.sm, gap: 2, justifyContent: 'center', minHeight: 44, paddingHorizontal: spacing.xs, paddingVertical: 9 },
  rowDisabled: { opacity: 0.5 },
  rowPressed: { backgroundColor: colors.background },
  rowTitle: { color: '#142b3a', fontWeight: '700' },
  meta: { color: '#637280', fontSize: 12 },
  selected: { backgroundColor: '#eaf3fa', borderColor: '#7aa9cf', borderRadius: 10, borderWidth: 1, gap: 4, marginBottom: 16, padding: 11 },
  selectedTitle: { color: '#142b3a', fontWeight: '800' },
  clientLine: { color: '#142b3a', fontSize: 13, fontWeight: '700' },
  clearAction: { alignSelf: 'flex-start', justifyContent: 'center', minHeight: 44 },
  clearText: { color: '#0067a8', fontWeight: '700' },
});
