import * as DocumentPicker from 'expo-document-picker';
import { Redirect } from 'expo-router';
import { useCallback, useEffect, useRef, useState } from 'react';
import { Alert, SafeAreaView, ScrollView, Text, View } from 'react-native';

import { apiUrl, readApiError } from '@/src/api/client';
import { useAuth } from '@/src/auth/AuthProvider';
import { deriveMobileCapabilities } from '@/src/permissions/mobile-capabilities';
import {
  buildLabClientListQuery,
  LAB_CLIENTS_PAGE_SIZE,
  mergeLabClientPage,
} from '@/src/services/lab-client-selector';
import type { LabClient } from '@/src/types/lab-work-order';
import { colors, layout, spacing, typography } from '@/src/design/tokens';
import {
  ActionRow,
  AdministrativeButton,
  BackButton,
  Card,
  DangerButton,
  EmptyState,
  Field,
  FadeIn,
  LoadingState,
  PrimaryButton,
  ReadOnlyField,
  Screen,
  SecondaryButton,
  Section,
  StatusBadge,
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
 * consultar, crear, editar, eliminar/restaurar (soft delete, Admin) e
 * importar XLSX sobre LabClient, la única autoridad de cliente legítima
 * para Mobile (aislamiento arquitectónico, ver myc-mobile/AGENTS.md: Mobile
 * no reutiliza el Cliente canónico del ERP productivo). Reutiliza
 * exactamente los mismos endpoints /mobile/v1/technician/lab-clients que ya
 * usaba el selector embebido en OT -- ningún modelo ni importador paralelo.
 */
export default function ClientsScreen() {
  const { authorizedFetch, isLoading, user } = useAuth();
  const capabilities = deriveMobileCapabilities(user);
  const {
    canReadLabClients, canManageLabClients, canEditLabClients,
    canImportLabClients, canDeactivateLabClients,
  } = capabilities;

  const [searchTerm, setSearchTerm] = useState('');
  const [results, setResults] = useState<LabClient[]>([]);
  const [showInactive, setShowInactive] = useState(false);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(false);
  const [error, setError] = useState('');
  const [mode, setMode] = useState<'list' | 'create' | 'edit'>('list');
  const [editingId, setEditingId] = useState<number | null>(null);
  const [draft, setDraft] = useState<ClientDraft>(BLANK_DRAFT);
  const [saving, setSaving] = useState(false);
  const [importing, setImporting] = useState(false);
  const [busyClientId, setBusyClientId] = useState<number | null>(null);
  const requestSequence = useRef(0);

  const load = useCallback(async (
    term: string,
    includeInactive: boolean,
    offset = 0,
    append = false,
  ) => {
    const requestId = ++requestSequence.current;
    if (append) {
      setLoadingMore(true);
    } else {
      setLoading(true);
      setLoadingMore(false);
    }
    setError('');
    try {
      const queryString = buildLabClientListQuery(term, offset, includeInactive);
      const response = await authorizedFetch(
        apiUrl(`/mobile/v1/technician/lab-clients?${queryString}`),
      );
      if (!response.ok) throw new Error(await readApiError(response));
      const page = await response.json() as LabClient[];
      if (requestId !== requestSequence.current) return;
      setResults((current) => mergeLabClientPage(current, page, append) as LabClient[]);
      setHasMore(page.length === LAB_CLIENTS_PAGE_SIZE);
    } catch (requestError) {
      if (requestId !== requestSequence.current) return;
      setError(requestError instanceof Error ? requestError.message : 'No fue posible cargar los clientes');
    } finally {
      if (requestId === requestSequence.current) {
        if (append) setLoadingMore(false); else setLoading(false);
      }
    }
  }, [authorizedFetch]);

  useEffect(() => {
    if (!user) return;
    const timer = setTimeout(() => { void load(searchTerm, showInactive); }, 300);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchTerm, showInactive, user]);

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
      await load(searchTerm, showInactive, 0, false);
    } catch (requestError) {
      Alert.alert(
        editingId ? 'No fue posible guardar los cambios' : 'No fue posible crear el cliente',
        requestError instanceof Error ? requestError.message : 'Revisa los datos',
      );
    } finally {
      setSaving(false);
    }
  }

  async function setClientActive(client: LabClient, active: boolean) {
    setBusyClientId(client.id);
    try {
      const response = await authorizedFetch(
        apiUrl(`/mobile/v1/technician/lab-clients/${client.id}/${active ? 'activate' : 'deactivate'}`),
        { method: 'POST' },
      );
      if (!response.ok) throw new Error(await readApiError(response));
      await load(searchTerm, showInactive, 0, false);
    } catch (requestError) {
      Alert.alert(
        active ? 'No fue posible restaurar el cliente' : 'No fue posible eliminar el cliente',
        requestError instanceof Error ? requestError.message : 'Intenta nuevamente',
      );
    } finally {
      setBusyClientId(null);
    }
  }

  function confirmDeactivate(client: LabClient) {
    Alert.alert(
      'Eliminar cliente',
      `"${client.company}" dejará de aparecer para nuevas OT. El histórico que ya lo usa sigue mostrando su nombre y dirección sin cambios. ¿Continuar?`,
      [
        { text: 'Cancelar', style: 'cancel' },
        { text: 'Eliminar', style: 'destructive', onPress: () => void setClientActive(client, false) },
      ],
    );
  }

  function confirmRestore(client: LabClient) {
    Alert.alert(
      'Restaurar cliente',
      `"${client.company}" volverá a estar disponible para nuevas OT. ¿Continuar?`,
      [
        { text: 'Cancelar', style: 'cancel' },
        { text: 'Restaurar', onPress: () => void setClientActive(client, true) },
      ],
    );
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
      await load(searchTerm, showInactive, 0, false);
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
      <SafeAreaView style={{ flex: 1, backgroundColor: colors.background }}>
        <Screen>
          <View style={{ padding: layout.screenPadding }}>
            <BackButton />
            <EmptyState title="Sin acceso" description="Tu cuenta no tiene permiso para consultar Clientes." />
          </View>
        </Screen>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.background }}>
      <ScrollView contentContainerStyle={{ padding: layout.screenPadding }}>
        <Screen>
          <View style={{ marginBottom: layout.sectionGap, gap: layout.fieldGap }}>
            <BackButton />
            <Text style={{ ...typography.title, color: colors.text }}>Clientes</Text>
            <Text style={{ color: colors.textMuted }}>Catálogo LAB: buscar, crear y editar clientes.</Text>
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
              {canDeactivateLabClients && (
                <SecondaryButton
                  label={showInactive ? 'Ocultar inactivos' : 'Ver clientes inactivos'}
                  onPress={() => setShowInactive((value) => !value)}
                />
              )}
            </Section>
          )}

          {mode !== 'list' && (
            <FadeIn transitionKey={mode}>
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
            </FadeIn>
          )}

          {!!error && <Text style={{ color: colors.danger, marginBottom: spacing.md }}>{error}</Text>}

          {mode === 'list' && (
            loading ? <LoadingState label="Buscando clientes…" /> : (
              results.length ? (
                <FadeIn transitionKey={`${searchTerm}:${showInactive}`}>
                  <View style={{ gap: layout.cardGap }}>
                    {results.map((client) => (
                      <Card key={client.id}>
                        <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                          <Text style={{ fontWeight: '800', color: colors.text, fontSize: 16, flex: 1 }}>{client.company}</Text>
                          {!client.is_active && <StatusBadge label="INACTIVO" tone="neutral" />}
                        </View>
                        {!!client.address && <ReadOnlyField label="Dirección" value={client.address} />}
                        {(client.city || client.state || client.postal_code) && (
                          <ReadOnlyField
                            label="Ubicación"
                            value={[client.city, client.state, client.postal_code].filter(Boolean).join(' · ')}
                          />
                        )}
                        {!!client.attention && <ReadOnlyField label="Atención" value={client.attention} />}
                        <ActionRow>
                          {canEditLabClients && client.is_active && (
                            <SecondaryButton label="Editar" onPress={() => startEdit(client)} />
                          )}
                          {canDeactivateLabClients && client.is_active && (
                            <DangerButton
                              label="Eliminar"
                              loading={busyClientId === client.id}
                              onPress={() => confirmDeactivate(client)}
                            />
                          )}
                          {canDeactivateLabClients && !client.is_active && (
                            <AdministrativeButton
                              label="Restaurar"
                              loading={busyClientId === client.id}
                              onPress={() => confirmRestore(client)}
                            />
                          )}
                        </ActionRow>
                      </Card>
                    ))}
                    {hasMore && (
                      <SecondaryButton
                        label="Cargar más"
                        loading={loadingMore}
                        onPress={() => void load(searchTerm, showInactive, results.length, true)}
                      />
                    )}
                  </View>
                </FadeIn>
              ) : (
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
