import { useEffect, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';

import type { LabClient, LinkedCompany } from '@/src/types/lab-work-order';
import { LabClientSelector } from '@/src/components/lab/LabClientSelector';
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
  instrument: '', brand: '', identification: '', serial_number: '',
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
      <Text style={styles.sectionTitle}>Datos del equipo</Text>
      <Field label="Instrumento" required value={equipment.instrument} onChange={(value) => setEquipment({ ...equipment, instrument: value })} />
      <Field label="Marca" required value={equipment.brand} onChange={(value) => setEquipment({ ...equipment, brand: value })} />
      <Field label="Identificación" required value={equipment.identification} onChange={(value) => setEquipment({ ...equipment, identification: value })} />
      <Field label="Serie" required value={equipment.serial_number} onChange={(value) => setEquipment({ ...equipment, serial_number: value })} />
      {service === 'linked' ? (
        <Field label="Informe (opcional)" value={equipment.report_number ?? ''} onChange={(value) => setEquipment({ ...equipment, report_number: value || null })} />
      ) : (
        <View style={styles.fieldGroup}>
          <Text style={styles.fieldLabel}>Folio de informe</Text>
          <Text style={styles.readOnlyValue}>{folioIsSecured ? folioDisplay : 'Generado por el sistema'}</Text>
        </View>
      )}
      <Text style={styles.fieldLabel}>Estado físico</Text>
      <View style={styles.row}>
        <Pressable onPress={() => setEquipment({ ...equipment, is_good_condition: true })} style={[styles.choice, equipment.is_good_condition && styles.choiceActive]}><Text>✓ Bueno</Text></Pressable>
        <Pressable onPress={() => setEquipment({ ...equipment, is_good_condition: false })} style={[styles.choice, !equipment.is_good_condition && styles.choiceBad]}><Text>X Malo</Text></Pressable>
      </View>

      <Text style={styles.sectionTitle}>Cliente documental</Text>
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

      <Text style={styles.sectionTitle}>Servicio</Text>
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
        <ScrollView style={styles.linkedList} nestedScrollEnabled>
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
        <>
          <Text style={styles.sectionTitle}>Folio</Text>
          <Text style={styles.notice}>{folioDisplay ?? 'Pendiente'}</Text>
        </>
      )}

      <View style={styles.actionRow}>
        <Pressable style={styles.cancel} onPress={onCancel}><Text>Cancelar</Text></Pressable>
        <Pressable
          disabled={!canSubmit || busy}
          style={[styles.save, (!canSubmit || busy) && styles.disabled]}
          onPress={submit}
        >
          <Text style={styles.saveText}>{mode === 'edit' ? 'Guardar cambios' : 'Guardar equipo'}</Text>
        </Pressable>
      </View>
    </View>
  );
}

function Field({
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
  sectionTitle: { color: '#142b3a', fontSize: 15, fontWeight: '800', marginTop: 10 },
  fieldGroup: { gap: 4 },
  fieldLabel: { color: '#344553', fontSize: 12, fontWeight: '700' },
  fieldInput: { backgroundColor: '#fff', borderColor: '#b9c8d2', borderRadius: 9, borderWidth: 1, minHeight: 44, paddingHorizontal: 11 },
  readOnlyValue: { backgroundColor: '#f5f8fa', borderColor: '#dbe4ea', borderRadius: 9, borderWidth: 1, color: '#344553', minHeight: 44, paddingHorizontal: 11, paddingVertical: 12 },
  row: { flexDirection: 'row', flexWrap: 'wrap', gap: 7 },
  choice: { backgroundColor: '#f5f8fa', borderColor: '#cbd7df', borderRadius: 9, borderWidth: 1, padding: 10 },
  choiceActive: { backgroundColor: '#dff3f1', borderColor: '#008f87' },
  choiceBad: { backgroundColor: '#fdeceb', borderColor: '#c73636' },
  notice: { color: '#637280', fontStyle: 'italic' },
  warning: { color: '#a86a00', fontSize: 12 },
  selectedClient: { alignItems: 'center', flexDirection: 'row', justifyContent: 'space-between', padding: 4 },
  selectedClientText: { color: '#142b3a', fontWeight: '700' },
  change: { color: '#0067a8', fontWeight: '700' },
  linkedList: { maxHeight: 160 },
  error: { color: '#c73636', fontWeight: '700' },
  actionRow: { flexDirection: 'row', gap: 8, marginTop: 8 },
  cancel: { alignItems: 'center', flex: 1, padding: 12 },
  save: { alignItems: 'center', backgroundColor: '#0067a8', borderRadius: 10, flex: 1, padding: 12 },
  saveText: { color: '#fff', fontWeight: '800' },
  disabled: { opacity: 0.42 },
});
