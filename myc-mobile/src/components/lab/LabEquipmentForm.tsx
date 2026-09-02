import { useEffect, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import type { LabClient, LinkedCompany } from '@/src/types/lab-work-order';
import { LabClientSelector } from '@/src/components/lab/LabClientSelector';
import {
  ActionRow, Field, PrimaryButton, ReadOnlyField, Section, SecondaryButton,
} from '@/src/design/primitives';
import { colors, radius, spacing } from '@/src/design/tokens';
import {
  defaultDocumentaryClient,
  selectFinalClient,
  validateServiceSelection,
  type DocumentaryClientSelection,
  type EquipmentBasicData,
  type EquipmentFormValues,
  type LabServiceType,
} from '@/src/services/lab-equipment-configured-payload';

type Request = <T>(path: string, init?: RequestInit) => Promise<T>;

type Props = {
  busy: boolean;
  /** Sólo aplica en mode='edit': el folio ya asignado se muestra de solo
   * lectura -- nunca se edita desde este formulario (Fase 2 hardening). */
  folioDisplay?: string | null;
  initialValues?: EquipmentFormValues;
  mode: 'create' | 'edit';
  onCancel(): void;
  onSubmit(values: EquipmentFormValues): void;
  request: Request;
  workOrderClientName: string;
};

const SERVICE_OPTIONS: { value: LabServiceType; label: string }[] = [
  { value: 'accredited', label: 'Acreditado' },
  { value: 'traceable', label: 'Trazable' },
  { value: 'linked', label: 'Vinculado' },
];

const BLANK_EQUIPMENT: EquipmentBasicData = {
  instrument: '', brand: '', model: null,
  identification: '', serial_number: '',
  report_number: null, is_good_condition: true,
};

/**
 * Alta y edición de equipo (Fase 2B-2D, Fase 2 hardening 2G): datos del
 * equipo + cliente documental + servicio en un solo formulario. El mismo
 * componente sirve para mode='create' (Fase 2E, un solo POST atómico) y
 * mode='edit' (Fase 2G, el padre decide qué endpoints llamar según lo que
 * realmente cambió -- ver diffEquipmentEdit). No hay un segundo formulario.
 */
export function LabEquipmentForm({
  busy, folioDisplay, initialValues, mode, onCancel, onSubmit, request, workOrderClientName,
}: Props) {
  const [equipment, setEquipment] = useState<EquipmentBasicData>(
    initialValues?.equipment ?? BLANK_EQUIPMENT,
  );
  const [documentaryClient, setDocumentaryClient] = useState<DocumentaryClientSelection>(
    initialValues?.documentaryClient ?? defaultDocumentaryClient(),
  );
  const [service, setService] = useState<LabServiceType>(
    initialValues?.service.serviceType ?? 'accredited',
  );
  const [linkedCompanyId, setLinkedCompanyId] = useState<number | null>(
    initialValues?.service.linkedCompanyId ?? null,
  );
  const [linkedCompanies, setLinkedCompanies] = useState<LinkedCompany[]>([]);
  const [validationError, setValidationError] = useState('');

  useEffect(() => {
    request<LinkedCompany[]>('/mobile/v1/technician/lab-work-orders/linked-companies')
      .then(setLinkedCompanies)
      .catch(() => setLinkedCompanies([]));
  }, [request]);

  const canSubmit = Boolean(
    equipment.instrument.trim() && equipment.brand.trim()
    && equipment.identification.trim() && equipment.serial_number.trim(),
  );
  const folioIsSecured = mode === 'edit' && !!folioDisplay && folioDisplay !== 'Pendiente' && folioDisplay !== 'Sin asignar';

  function submit() {
    const error = validateServiceSelection({ serviceType: service, linkedCompanyId });
    if (error) {
      setValidationError(error);
      return;
    }
    setValidationError('');
    onSubmit({ equipment, documentaryClient, service: { serviceType: service, linkedCompanyId } });
  }

  return (
    <View style={styles.panel}>
      <Section title="Datos del equipo">
        <Field label="Instrumento *" onChange={(value) => setEquipment({ ...equipment, instrument: value })} value={equipment.instrument} />
        <Field label="Marca *" onChange={(value) => setEquipment({ ...equipment, brand: value })} value={equipment.brand} />
        <Field label="Modelo" onChange={(value) => setEquipment({ ...equipment, model: value || null })} value={equipment.model ?? ''} />
        <Field label="Identificación *" onChange={(value) => setEquipment({ ...equipment, identification: value })} value={equipment.identification} />
        <Field label="Serie *" onChange={(value) => setEquipment({ ...equipment, serial_number: value })} value={equipment.serial_number} />
        {service === 'linked' ? (
          <Field label="Informe (opcional)" onChange={(value) => setEquipment({ ...equipment, report_number: value || null })} value={equipment.report_number ?? ''} />
        ) : (
          <ReadOnlyField label="Folio de informe" value={folioIsSecured ? (folioDisplay as string) : 'Generado por el sistema'} />
        )}
        <Text style={styles.groupLabel}>Estado físico</Text>
        <View style={styles.row}>
          <Pressable onPress={() => setEquipment({ ...equipment, is_good_condition: true })} style={[styles.choice, equipment.is_good_condition && styles.choiceActive]}><Text>✓ Bueno</Text></Pressable>
          <Pressable onPress={() => setEquipment({ ...equipment, is_good_condition: false })} style={[styles.choice, !equipment.is_good_condition && styles.choiceBad]}><Text>X Malo</Text></Pressable>
        </View>
      </Section>

      <Section title="Cliente documental">
        <View style={styles.row}>
          <Pressable
            onPress={() => setDocumentaryClient(defaultDocumentaryClient())}
            style={[styles.choice, documentaryClient.mode === 'order' && styles.choiceActive]}
          >
            <Text>Mismo cliente de la OT</Text>
          </Pressable>
          <Pressable
            onPress={() => setDocumentaryClient((current) => (
              current.mode === 'different' ? current : { ...defaultDocumentaryClient(), mode: 'different', finalClientCompany: '' }
            ))}
            style={[styles.choice, documentaryClient.mode === 'different' && styles.choiceActive]}
          >
            <Text>Otro cliente</Text>
          </Pressable>
        </View>
        {documentaryClient.mode === 'order' && (
          <Text style={styles.notice}>{workOrderClientName}</Text>
        )}
        {documentaryClient.mode === 'different' && (
          <>
            {documentaryClient.finalClientCompany ? (
              <View style={styles.selectedClient}>
                <Text style={styles.selectedClientText}>{documentaryClient.finalClientCompany}</Text>
                <Pressable onPress={() => setDocumentaryClient({ ...defaultDocumentaryClient(), mode: 'different', finalClientCompany: '' })}>
                  <Text style={styles.change}>Cambiar</Text>
                </Pressable>
              </View>
            ) : (
              <LabClientSelector
                request={request}
                onSelect={(client: LabClient) => setDocumentaryClient(selectFinalClient(client))}
              />
            )}
          </>
        )}
      </Section>

      <Section title="Servicio">
        <View style={styles.row}>
          {SERVICE_OPTIONS.map((option) => (
            <Pressable
              key={option.value}
              onPress={() => { setService(option.value); setValidationError(''); }}
              style={[styles.choice, service === option.value && styles.choiceActive]}
            >
              <Text>{option.label}</Text>
            </Pressable>
          ))}
        </View>
        {service === 'linked' && (
          <ScrollView nestedScrollEnabled style={styles.linkedList}>
            {linkedCompanies.map((company) => (
              <Pressable
                key={company.id}
                onPress={() => setLinkedCompanyId(company.id)}
                style={[styles.choice, linkedCompanyId === company.id && styles.choiceActive]}
              >
                <Text>{company.name}</Text>
              </Pressable>
            ))}
          </ScrollView>
        )}
        {mode === 'edit' && folioIsSecured && (
          <Text style={styles.warning}>
            Este equipo ya tiene folio reservado; cambiar el servicio a otro distinto será rechazado
            para no liberarlo ni reasignarlo. Reconfirmar el mismo servicio es seguro.
          </Text>
        )}
        {!!validationError && <Text style={styles.error}>{validationError}</Text>}
        {mode === 'edit' && service === 'linked' && (
          <ReadOnlyField label="Folio" value={folioDisplay ?? 'Pendiente'} />
        )}
      </Section>

      <ActionRow>
        <SecondaryButton label="Cancelar" onPress={onCancel} />
        <PrimaryButton disabled={!canSubmit || busy} label={mode === 'edit' ? 'Guardar cambios' : 'Guardar equipo'} loading={busy} onPress={submit} />
      </ActionRow>
    </View>
  );
}

const styles = StyleSheet.create({
  panel: { gap: spacing.md },
  groupLabel: { color: colors.textMuted, fontSize: 12, fontWeight: '700' },
  row: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm },
  choice: { backgroundColor: colors.background, borderColor: colors.borderStrong, borderRadius: radius.md, borderWidth: 1, padding: spacing.sm },
  choiceActive: { backgroundColor: colors.primarySoft, borderColor: colors.accent },
  choiceBad: { backgroundColor: '#fdeceb', borderColor: colors.danger },
  notice: { color: colors.textSubtle, fontStyle: 'italic' },
  warning: { color: colors.warningStrong, fontSize: 12 },
  selectedClient: { alignItems: 'center', flexDirection: 'row', justifyContent: 'space-between', padding: spacing.xs },
  selectedClientText: { color: colors.text, fontWeight: '700' },
  change: { color: colors.primary, fontWeight: '700' },
  linkedList: { maxHeight: 160 },
  error: { color: colors.danger, fontWeight: '700' },
});
