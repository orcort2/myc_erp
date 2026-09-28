import { useEffect, useState, type RefObject } from 'react';
import { Alert, Pressable, StyleSheet, Text, TextInput, View } from 'react-native';

import { AlertBanner, Card, EmptyState, LoadingState } from '@/src/design/primitives';
import { colors, radius, spacing } from '@/src/design/tokens';
import type { LabClient } from '@/src/types/lab-work-order';
import {
  applyCreatedClient,
  applySearchResults,
  buildLabClientSearchQuery,
  cancelInlineCreate,
  contextualCreateCompany,
  initialSelectorState,
  limitVisibleResults,
  openInlineCreate,
  resolveSearchView,
  shouldSearchLabClients,
  shouldResetFormAfterSubmit,
} from '@/src/services/lab-client-selector';

type Request = <T>(path: string, init?: RequestInit) => Promise<T>;

/** Devuelve true si el selector consumió el "atrás" (p. ej. cancelar el alta). */
export type LabClientSelectorBackHandler = () => boolean;

type Props = {
  onSelect(client: LabClient): void;
  request: Request;
  /**
   * Opcional: el contenedor (LabClientPickerModal) consulta aquí el Back de
   * Android antes de cerrarse. El modo búsqueda/alta sigue siendo estado
   * exclusivo del selector; el padre nunca lo lee ni lo escribe.
   */
  backHandlerRef?: RefObject<LabClientSelectorBackHandler | null>;
};

/**
 * Selector de LabClient reutilizado tanto para el cliente receptor de la OT
 * (Fase 2A) como para el cliente documental "Otro cliente" de un equipo
 * (Fase 2C) -- mismo componente, un solo buscador, sin duplicar UI.
 *
 * Es la autoridad de contenido (búsqueda + alta). No decide su presentación:
 * la OT lo envuelve en LabClientPickerModal; el formulario de equipo lo
 * sigue mostrando inline.
 */
export function LabClientSelector({ onSelect, request, backHandlerRef }: Props) {
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
    // Un error pertenece al término que lo produjo: al teclear otro, la vista
    // vuelve a 'loading' hasta que responda el nuevo término.
    setSearchError('');
    if (!shouldSearchLabClients(state.searchTerm)) {
      setLoading(false);
      setSearchError('');
      setState((current) => current.results.length ? { ...current, results: [], resultsTerm: '' } : current);
      return () => { active = false; };
    }
    const timer = setTimeout(() => {
      setLoading(true);
      const term = state.searchTerm;
      const query = buildLabClientSearchQuery(term);
      request<LabClient[]>(`/mobile/v1/technician/lab-clients?${query}`)
        .then((results) => { if (active) setState((current) => applySearchResults(current, term, results)); })
        .catch((error) => {
          // La búsqueda ya no falla en silencio -- se muestra un estado de
          // error explícito sin tirar el formulario contenedor (OT/equipo).
          if (active) setSearchError(error instanceof Error ? error.message : 'No fue posible buscar clientes.');
        })
        .finally(() => { if (active) setLoading(false); });
    }, 300);
    return () => { active = false; clearTimeout(timer); };
  }, [state.searchTerm, request]);

  // Única transición de salida del alta: la usan "Cancelar" y el Back del
  // contenedor. Vuelve a búsqueda conservando término y resultados.
  function cancelCreate() {
    setState((current) => cancelInlineCreate(current));
  }

  useEffect(() => {
    if (!backHandlerRef) return;
    backHandlerRef.current = () => {
      if (state.mode !== 'create') return false;
      cancelCreate();
      return true;
    };
    return () => { backHandlerRef.current = null; };
  }, [backHandlerRef, state.mode]);

  // Alta contextual desde una búsqueda sin coincidencias: misma alta que
  // "+ Crear cliente", sólo precarga Empresa con el término buscado. No crea
  // nada hasta que el usuario pulsa Guardar.
  function openContextualCreate() {
    setNewCompany(contextualCreateCompany(state));
    setState(openInlineCreate(state));
  }

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
          <Pressable accessibilityRole="button" style={styles.cancel} onPress={cancelCreate}>
            <Text>Cancelar</Text>
          </Pressable>
          <Pressable
            accessibilityRole="button"
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
  const view = resolveSearchView(state, { loading, error: searchError });
  const searchedTerm = contextualCreateCompany(state);
  return (
    <Card>
      <TextInput
        accessibilityLabel="Buscar cliente"
        placeholder="Buscar cliente"
        style={styles.search}
        value={state.searchTerm}
        onChangeText={(value) => setState((current) => ({ ...current, searchTerm: value }))}
      />
      <View style={styles.results}>
        {view === 'loading' ? (
          <LoadingState label="Buscando clientes…" />
        ) : view === 'error' ? (
          <AlertBanner tone="danger">{searchError}</AlertBanner>
        ) : view === 'results' ? (
          <View>
            {visibleResults.map((item) => (
              <Pressable
                key={item.id}
                accessibilityRole="button"
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
          </View>
        ) : view === 'empty' ? (
          <View>
            <EmptyState title="Sin resultados" description="Ningún cliente coincide. Puedes crearlo con este nombre." />
            <Pressable accessibilityRole="button" style={styles.contextualCreate} onPress={openContextualCreate}>
              <Text style={styles.secondaryText}>{`+ Crear cliente "${searchedTerm}"`}</Text>
            </Pressable>
          </View>
        ) : (
          <EmptyState title="Buscar cliente" description="Escribe al menos 2 caracteres para buscar un cliente existente." />
        )}
      </View>
      <Pressable accessibilityRole="button" style={styles.secondary} onPress={() => setState(openInlineCreate(state))}>
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
  results: { marginTop: spacing.sm },
  resultRow: { borderBottomColor: '#e4ebf0', borderBottomWidth: 1, borderRadius: radius.sm, justifyContent: 'center', minHeight: 44, paddingHorizontal: spacing.xs, paddingVertical: 9 },
  resultRowSelected: { backgroundColor: '#eef6f5' },
  resultRowPressed: { backgroundColor: colors.background },
  resultCompany: { color: '#142b3a', fontWeight: '700' },
  resultMeta: { color: '#637280', fontSize: 12 },
  secondary: { alignItems: 'center', borderColor: '#0067a8', borderRadius: 10, borderWidth: 1, marginTop: spacing.sm, padding: 11 },
  contextualCreate: { alignItems: 'center', backgroundColor: '#eaf3fa', borderRadius: 10, justifyContent: 'center', minHeight: 44, padding: 11 },
  secondaryText: { color: '#0067a8', fontWeight: '800' },
  fieldGroup: { gap: 4 },
  fieldLabel: { color: '#344553', fontSize: 12, fontWeight: '700' },
  fieldInput: { backgroundColor: '#fff', borderColor: '#b9c8d2', borderRadius: 9, borderWidth: 1, minHeight: 44, paddingHorizontal: 11 },
  actionRow: { flexDirection: 'row', gap: 8, marginTop: 4 },
  cancel: { alignItems: 'center', flex: 1, justifyContent: 'center', minHeight: 44, padding: 12 },
  save: { alignItems: 'center', backgroundColor: '#0067a8', borderRadius: 10, flex: 1, justifyContent: 'center', minHeight: 44, padding: 12 },
  saveText: { color: '#fff', fontWeight: '800' },
  disabled: { opacity: 0.42 },
});
