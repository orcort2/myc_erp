import * as DocumentPicker from 'expo-document-picker';
import { Redirect, router } from 'expo-router';
import { useCallback, useEffect, useState } from 'react';
import { Alert, SafeAreaView, ScrollView, Text, View } from 'react-native';

import { apiUrl, readApiError } from '@/src/api/client';
import { useAuth } from '@/src/auth/AuthProvider';
import { deriveMobileCapabilities } from '@/src/permissions/mobile-capabilities';
import { buildLabClientSearchQuery } from '@/src/services/lab-client-selector';
import type { LabClient } from '@/src/types/lab-work-order';
import { layout, spacing } from '@/src/design/tokens';
import {
  ActionRow,
  Card,
  EmptyState,
  Field,
  LoadingState,
  PrimaryButton,
  ReadOnlyField,
  Screen,
  SecondaryButton,
  Section,
} from '@/src/design/primitives';

type ClientDraft = {
  company: string;
  address: string;
  attention: string;
  postal_code: string;
  city: string;
  state: string;
};

const BLANK_DRAFT: ClientDraft = {
  company: '', address: '', attention: '', postal_code: '', city: '', state: '',
};

function draftFromClient(client: LabClient): ClientDraft {
  return {
    company: client.company,
    address: client.address,
    attention: client.attention,
    postal_code: client.postal_code ?? '',
    city: client.city ?? '',
    state: client.state ?? '',
  };
}

/**
 * Cierre UX 2026-09: módulo Clientes real (no placeholder) -- buscar,
 * consultar, crear, editar e importar XLSX sobre LabClient, la única
 * autoridad de cliente legítima para Mobile (aislamiento arquitectónico,
 * ver myc-mobile/AGENTS.md: Mobile no reutiliza el Cliente canónico del
 * ERP productivo). Reutiliza exactamente los mismos endpoints
 * /mobile/v1/technician/lab-clients que ya usaba el selector embebido en
 * OT -- ningún modelo ni importador paralelo.
 */
export default function ClientsScreen() {
  const { authorizedFetch, isLoading, user } = useAuth();
  const capabilities = deriveMobileCapabilities(user);
  const { canReadLabClients, canManageLabClients, canEditLabClients, canImportLabClients } = capabilities;

  const [searchTerm, setSearchTerm] = useState('');
  const [results, setResults] = useState<LabClient[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [mode, setMode] = useState<'list' | 'create' | 'edit'>('list');
  const [editingId, setEditingId] = useState<number | null>(null);
  const [draft, setDraft] = useState<ClientDraft>(BLANK_DRAFT);
  const [saving, setSaving] = useState(false);
  const [importing, setImporting] = useState(false);

  const load = useCallback(async (term: string) => {
    setLoading(true);
    setError('');
    try {
      const query = buildLabClientSearchQuery(term);
      const response = await authorizedFetch(
        apiUrl(`/mobile/v1/technician/lab-clients${query ? `?${query}` : ''}`),
      );
      if (!response.ok) throw new Error(await readApiError(response));
      setResults(await response.json() as LabClient[]);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'No fue posible cargar los clientes');
    } finally {
      setLoading(false);
    }
  }, [authorizedFetch]);

  useEffect(() => {
    if (!user) return;
    const timer = setTimeout(() => { void load(searchTerm); }, 300);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchTerm, user]);

  function startCreate() {
    setDraft(BLANK_DRAFT);
    setEditingId(null);
    setMode('create');
  }

  function startEdit(client: LabClient) {
    setDraft(draftFromClient(client));
    setEditingId(client.id);
    setMode('edit');
  }

  function cancelForm() {
    setMode('list');
    setEditingId(null);
    setDraft(BLANK_DRAFT);
  }

  async function saveDraft() {
    if (!draft.company.trim()) return;
    setSaving(true);
    try {
      const body = JSON.stringify({
        company: draft.company.trim(),
        address: draft.address.trim(),
        attention: draft.attention.trim(),
        postal_code: draft.postal_code.trim() || null,
        city: draft.city.trim() || null,
        state: draft.state.trim() || null,
      });
      const path = editingId
        ? `/mobile/v1/technician/lab-clients/${editingId}`
        : '/mobile/v1/technician/lab-clients';
      const response = await authorizedFetch(apiUrl(path), {
        method: editingId ? 'PATCH' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body,
      });
      if (!response.ok) throw new Error(await readApiError(response));
      cancelForm();
      await load(searchTerm);
    } catch (requestError) {
      Alert.alert(
        editingId ? 'No fue posible guardar los cambios' : 'No fue posible crear el cliente',
        requestError instanceof Error ? requestError.message : 'Revisa los datos',
      );
    } finally {
      setSaving(false);
    }
  }

  async function importXlsx() {
    const picked = await DocumentPicker.getDocumentAsync({
      copyToCacheDirectory: true,
      multiple: false,
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    });
    if (picked.canceled) return;
    setImporting(true);
    try {
      const asset = picked.assets[0];
      const form = new FormData();
      form.append('upload', {
        uri: asset.uri,
        name: asset.name,
        type: asset.mimeType ?? 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      } as unknown as Blob);
      const response = await authorizedFetch(apiUrl('/mobile/v1/technician/lab-clients/import'), {
        method: 'POST',
        body: form,
      });
      if (!response.ok) throw new Error(await readApiError(response));
      const summary = await response.json() as { new: number; skipped: number; invalid: number };
      await load(searchTerm);
      Alert.alert('Importación terminada', `${summary.new} nuevos · ${summary.skipped} omitidos · ${summary.invalid} inválidos`);
    } catch (requestError) {
      Alert.alert('No fue posible importar', requestError instanceof Error ? requestError.message : 'Revisa el XLSX');
    } finally {
      setImporting(false);
    }
  }

  if (isLoading) return <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center' }}><LoadingState /></View>;
  if (!user) return <Redirect href="/(auth)/login" />;
  if (!canReadLabClients) {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: '#f4f7fa' }}>
        <Screen>
          <View style={{ padding: layout.screenPadding }}>
            <SecondaryButton label="‹ Inicio" onPress={() => router.back()} />
            <EmptyState title="Sin acceso" description="Tu cuenta no tiene permiso para consultar Clientes." />
          </View>
        </Screen>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: '#f4f7fa' }}>
      <ScrollView contentContainerStyle={{ padding: layout.screenPadding }}>
        <Screen>
          <View style={{ marginBottom: layout.sectionGap, gap: layout.fieldGap }}>
            <SecondaryButton label="‹ Inicio" onPress={() => router.back()} />
            <Text style={{ fontSize: 22, fontWeight: '800', color: '#142b3a' }}>Clientes</Text>
            <Text style={{ color: '#51606f' }}>Catálogo LAB: buscar, crear y editar clientes.</Text>
          </View>

          {mode === 'list' && (
            <Section>
              <Field label="Buscar cliente" value={searchTerm} onChange={setSearchTerm} placeholder="Nombre, dirección o atención" />
              <ActionRow>
                {canManageLabClients && <PrimaryButton label="+ Crear cliente" onPress={startCreate} />}
                {canImportLabClients && (
                  <SecondaryButton label="Importar XLSX" onPress={importXlsx} loading={importing} />
                )}
              </ActionRow>
            </Section>
          )}

          {mode !== 'list' && (
            <Section title={mode === 'edit' ? 'Editar cliente' : 'Crear cliente'}>
              <Field label="Empresa" value={draft.company} onChange={(value) => setDraft({ ...draft, company: value })} />
              <Field label="Dirección" value={draft.address} onChange={(value) => setDraft({ ...draft, address: value })} multiline />
              <Field label="Código postal" value={draft.postal_code} onChange={(value) => setDraft({ ...draft, postal_code: value })} keyboardType="numeric" />
              <Field label="Ciudad" value={draft.city} onChange={(value) => setDraft({ ...draft, city: value })} />
              <Field label="Estado" value={draft.state} onChange={(value) => setDraft({ ...draft, state: value })} />
              <Field label="Atención a" value={draft.attention} onChange={(value) => setDraft({ ...draft, attention: value })} />
              <ActionRow>
                <SecondaryButton label="Cancelar" onPress={cancelForm} />
                <PrimaryButton label="Guardar" onPress={saveDraft} disabled={!draft.company.trim()} loading={saving} />
              </ActionRow>
            </Section>
          )}

          {!!error && <Text style={{ color: '#c73636', marginBottom: spacing.md }}>{error}</Text>}

          {mode === 'list' && (
            loading ? <LoadingState label="Buscando clientes…" /> : (
              results.length ? results.map((client) => (
                <Card key={client.id}>
                  <Text style={{ fontWeight: '800', color: '#142b3a', fontSize: 16 }}>{client.company}</Text>
                  {!!client.address && <ReadOnlyField label="Dirección" value={client.address} />}
                  {(client.city || client.state || client.postal_code) && (
                    <ReadOnlyField
                      label="Ubicación"
                      value={[client.city, client.state, client.postal_code].filter(Boolean).join(' · ')}
                    />
                  )}
                  {!!client.attention && <ReadOnlyField label="Atención" value={client.attention} />}
                  {canEditLabClients && (
                    <ActionRow>
                      <SecondaryButton label="Editar" onPress={() => startEdit(client)} />
                    </ActionRow>
                  )}
                </Card>
              )) : (
                <EmptyState
                  title="Sin resultados"
                  description={searchTerm.trim() ? 'Ningún cliente coincide con la búsqueda.' : 'Todavía no hay clientes registrados.'}
                />
              )
            )
          )}
        </Screen>
      </ScrollView>
    </SafeAreaView>
  );
}
