import { useEffect, useState } from 'react';
import { Alert, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';

import { AlertBanner, Card, EmptyState, LoadingState } from '@/src/design/primitives';
import { colors, radius, spacing } from '@/src/design/tokens';
import type { LabClient } from '@/src/types/lab-work-order';
import {
  applyCreatedClient,
  buildLabClientSearchQuery,
  cancelInlineCreate,
  initialSelectorState,
  limitVisibleResults,
  openInlineCreate,
  shouldSearchLabClients,
  shouldResetFormAfterSubmit,
} from '@/src/services/lab-client-selector';

type Request = <T>(path: string, init?: RequestInit) => Promise<T>;

type Props = {
  onSelect(client: LabClient): void;
  request: Request;
};

/**
 * Selector de LabClient reutilizado tanto para el cliente receptor de la OT
 * (Fase 2A) como para el cliente documental "Otro cliente" de un equipo
 * (Fase 2C) -- mismo componente, un solo buscador, sin duplicar UI.
 */
export function LabClientSelector({ onSelect, request }: Props) {
  const [state, setState] = useState(initialSelectorState());
  const [loading, setLoading] = useState(false);
  const [searchError, setSearchError] = useState('');
  const [newCompany, setNewCompany] = useState('');
  const [newAddress, setNewAddress] = useState('');
  const [newAttention, setNewAttention] = useState('');
  const [newPostalCode, setNewPostalCode] = useState('');
  const [newCity, setNewCity] = useState('');
  const [newState, setNewState] = useState('');
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    let active = true;
    if (!shouldSearchLabClients(state.searchTerm)) {
      setLoading(false);
      setSearchError('');
      setState((current) => current.results.length ? { ...current, results: [] } : current);
      return () => { active = false; };
    }
    const timer = setTimeout(() => {
      setLoading(true);
      setSearchError('');
      const query = buildLabClientSearchQuery(state.searchTerm);
      request<LabClient[]>(`/mobile/v1/technician/lab-clients?${query}`)
        .then((results) => { if (active) setState((current) => ({ ...current, results })); })
        .catch((error) => {
          // La búsqueda ya no falla en silencio -- se muestra un estado de
          // error explícito sin tirar el formulario contenedor (OT/equipo).
          if (active) setSearchError(error instanceof Error ? error.message : 'No fue posible buscar clientes.');
        })
        .finally(() => { if (active) setLoading(false); });
    }, 300);
    return () => { active = false; clearTimeout(timer); };
  }, [state.searchTerm, request]);

  async function submitInlineCreate() {
    if (!newCompany.trim()) return;
    setCreating(true);
    try {
      const created = await request<LabClient>('/mobile/v1/technician/lab-clients', {
        method: 'POST',
        body: JSON.stringify({
          company: newCompany.trim(),
          address: newAddress.trim(),
          attention: newAttention.trim(),
          postal_code: newPostalCode.trim() || null,
          city: newCity.trim() || null,
          state: newState.trim() || null,
        }),
      });
      if (shouldResetFormAfterSubmit('success')) {
        setNewCompany('');
        setNewAddress('');
        setNewAttention('');
        setNewPostalCode('');
        setNewCity('');
        setNewState('');
      }
      setState((current) => applyCreatedClient(current, created));
      onSelect(created);
    } catch (error) {
      // shouldResetFormAfterSubmit('error') === false: los campos de creación
      // conservan lo capturado, el usuario sólo corrige y reintenta.
      Alert.alert('No fue posible crear el cliente', error instanceof Error ? error.message : 'Revisa los datos');
    } finally {
      setCreating(false);
    }
  }

  if (state.mode === 'create') {
    return (
      <Card>
        <Text style={styles.title}>Crear cliente</Text>
        <SelectorField label="Empresa" required value={newCompany} onChange={setNewCompany} />
        <SelectorField label="Dirección" value={newAddress} onChange={setNewAddress} />
        <SelectorField label="Código postal" value={newPostalCode} onChange={setNewPostalCode} />
        <SelectorField label="Ciudad" value={newCity} onChange={setNewCity} />
        <SelectorField label="Estado" value={newState} onChange={setNewState} />
        <SelectorField label="Atención a" value={newAttention} onChange={setNewAttention} />
        <View style={styles.actionRow}>
          <Pressable style={styles.cancel} onPress={() => setState(cancelInlineCreate(state))}>
            <Text>Cancelar</Text>
          </Pressable>
          <Pressable
            disabled={!newCompany.trim() || creating}
            style={[styles.save, (!newCompany.trim() || creating) && styles.disabled]}
            onPress={submitInlineCreate}
          >
            <Text style={styles.saveText}>Guardar</Text>
          </Pressable>
        </View>
      </Card>
    );
  }

  const visibleResults = limitVisibleResults(state.results);
  return (
    <Card>
      <TextInput
        placeholder="Buscar cliente"
        style={styles.search}
        value={state.searchTerm}
        onChangeText={(value) => setState((current) => ({ ...current, searchTerm: value }))}
      />
      <View style={styles.results}>
        {loading ? (
          <LoadingState label="Buscando clientes…" />
        ) : searchError ? (
          <AlertBanner tone="danger">{searchError}</AlertBanner>
        ) : visibleResults.length ? (
          <ScrollView nestedScrollEnabled>
            {visibleResults.map((item) => (
              <Pressable
                key={item.id}
                style={({ pressed }) => [
                  styles.resultRow,
                  state.selectedClientId === item.id && styles.resultRowSelected,
                  pressed && styles.resultRowPressed,
                ]}
                onPress={() => { setState((current) => ({ ...current, selectedClientId: item.id })); onSelect(item as LabClient); }}
              >
                <Text style={styles.resultCompany}>{item.company}</Text>
                {!!item.attention && <Text style={styles.resultMeta}>{item.attention}</Text>}
              </Pressable>
            ))}
          </ScrollView>
        ) : (
          <EmptyState title="Sin resultados" description={state.searchTerm.trim() ? 'Prueba con otro nombre o crea el cliente.' : 'Escribe para buscar un cliente existente.'} />
        )}
      </View>
      <Pressable style={styles.secondary} onPress={() => setState(openInlineCreate(state))}>
        <Text style={styles.secondaryText}>+ Crear cliente</Text>
      </Pressable>
    </Card>
  );
}

function SelectorField({
  label, value, onChange, required,
}: { label: string; value: string; onChange(value: string): void; required?: boolean }) {
  return (
    <View style={styles.fieldGroup}>
      <Text style={styles.fieldLabel}>{label}{required ? ' *' : ''}</Text>
      <TextInput onChangeText={onChange} style={styles.fieldInput} value={value} />
    </View>
  );
}

const styles = StyleSheet.create({
  title: { color: '#142b3a', fontSize: 16, fontWeight: '800', marginBottom: spacing.sm },
  search: { backgroundColor: '#fff', borderColor: '#b9c8d2', borderRadius: 9, borderWidth: 1, minHeight: 44, paddingHorizontal: 11 },
  results: { marginTop: spacing.sm, maxHeight: 220 },
  resultRow: { borderBottomColor: '#e4ebf0', borderBottomWidth: 1, borderRadius: radius.sm, paddingHorizontal: spacing.xs, paddingVertical: 9 },
  resultRowSelected: { backgroundColor: '#eef6f5' },
  resultRowPressed: { backgroundColor: colors.background },
  resultCompany: { color: '#142b3a', fontWeight: '700' },
  resultMeta: { color: '#637280', fontSize: 12 },
  secondary: { alignItems: 'center', borderColor: '#0067a8', borderRadius: 10, borderWidth: 1, marginTop: spacing.sm, padding: 11 },
  secondaryText: { color: '#0067a8', fontWeight: '800' },
  fieldGroup: { gap: 4 },
  fieldLabel: { color: '#344553', fontSize: 12, fontWeight: '700' },
  fieldInput: { backgroundColor: '#fff', borderColor: '#b9c8d2', borderRadius: 9, borderWidth: 1, minHeight: 44, paddingHorizontal: 11 },
  actionRow: { flexDirection: 'row', gap: 8, marginTop: 4 },
  cancel: { alignItems: 'center', flex: 1, padding: 12 },
  save: { alignItems: 'center', backgroundColor: '#0067a8', borderRadius: 10, flex: 1, padding: 12 },
  saveText: { color: '#fff', fontWeight: '800' },
  disabled: { opacity: 0.42 },
});
