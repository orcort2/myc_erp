import { useEffect, useState } from 'react';
import { Alert, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';

import type { LabClient } from '@/src/types/lab-work-order';
import {
  applyCreatedClient,
  buildLabClientSearchQuery,
  cancelInlineCreate,
  initialSelectorState,
  limitVisibleResults,
  openInlineCreate,
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
  const [newCompany, setNewCompany] = useState('');
  const [newAddress, setNewAddress] = useState('');
  const [newAttention, setNewAttention] = useState('');
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    let active = true;
    const timer = setTimeout(() => {
      setLoading(true);
      const query = buildLabClientSearchQuery(state.searchTerm);
      request<LabClient[]>(`/mobile/v1/technician/lab-clients${query ? `?${query}` : ''}`)
        .then((results) => { if (active) setState((current) => ({ ...current, results })); })
        .catch(() => { /* búsqueda silenciosa: no debe tirar el formulario contenedor */ })
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
        }),
      });
      if (shouldResetFormAfterSubmit('success')) {
        setNewCompany('');
        setNewAddress('');
        setNewAttention('');
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
      <View style={styles.panel}>
        <Text style={styles.title}>Crear cliente</Text>
        <SelectorField label="Empresa" required value={newCompany} onChange={setNewCompany} />
        <SelectorField label="Dirección" value={newAddress} onChange={setNewAddress} />
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
      </View>
    );
  }

  const visibleResults = limitVisibleResults(state.results);
  return (
    <View style={styles.panel}>
      <TextInput
        placeholder="Buscar cliente"
        style={styles.search}
        value={state.searchTerm}
        onChangeText={(value) => setState((current) => ({ ...current, searchTerm: value }))}
      />
      <ScrollView style={styles.results} nestedScrollEnabled>
        {visibleResults.map((item) => (
          <Pressable
            key={item.id}
            style={[styles.resultRow, state.selectedClientId === item.id && styles.resultRowSelected]}
            onPress={() => { setState((current) => ({ ...current, selectedClientId: item.id })); onSelect(item as LabClient); }}
          >
            <Text style={styles.resultCompany}>{item.company}</Text>
            {!!item.attention && <Text style={styles.resultMeta}>{item.attention}</Text>}
          </Pressable>
        ))}
        {!loading && !visibleResults.length && <Text style={styles.empty}>Sin resultados.</Text>}
      </ScrollView>
      <Pressable style={styles.secondary} onPress={() => setState(openInlineCreate(state))}>
        <Text style={styles.secondaryText}>+ Crear cliente</Text>
      </Pressable>
    </View>
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
  panel: { gap: 8 },
  title: { color: '#142b3a', fontSize: 16, fontWeight: '800' },
  search: { backgroundColor: '#fff', borderColor: '#b9c8d2', borderRadius: 9, borderWidth: 1, minHeight: 44, paddingHorizontal: 11 },
  results: { maxHeight: 220 },
  resultRow: { borderBottomColor: '#e4ebf0', borderBottomWidth: 1, paddingVertical: 9 },
  resultRowSelected: { backgroundColor: '#eef6f5' },
  resultCompany: { color: '#142b3a', fontWeight: '700' },
  resultMeta: { color: '#637280', fontSize: 12 },
  empty: { color: '#8a97a1', paddingVertical: 8 },
  secondary: { alignItems: 'center', borderColor: '#0067a8', borderRadius: 10, borderWidth: 1, marginTop: 4, padding: 11 },
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
