import { useMemo, useRef, useState } from 'react';
import { Pressable, StyleSheet, Text, TextInput, View } from 'react-native';

import { AlertBanner, PrimaryButton, SecondaryButton } from '@/src/design/primitives';
import { MobileSignaturePad } from '@/src/components/signatures/MobileSignaturePad';
import { SuccessTransition } from '@/src/components/signatures/StepTransition';
import { SignatureSubmissionLock } from '@/src/components/signatures/signature-flow-state';
import {
  buildDeliveryPayload,
  createDeliveryWizardState,
  goToStep,
  validateContinueFromDeliveredBySignature,
  validateContinueFromRecipient,
  validateSubmitDelivery,
} from '@/src/components/lab/lab-delivery-flow-state';
import type { LabDeliveryCreatePayload, LabDeliveryMethod, LabDeliveryPendingEquipmentItem } from '@/src/types/lab-work-order';

const METHOD_OPTIONS: { value: LabDeliveryMethod; label: string }[] = [
  { value: 'direct', label: 'Entrega directa' },
  { value: 'client_pickup', label: 'Recolección por cliente' },
];

const SUCCESS_CONFIRMATION_MS = 900;

type Props = {
  clientName: string;
  deliveredByName: string;
  defaultRecipientName: string;
  equipment: LabDeliveryPendingEquipmentItem[];
  isPartial: boolean;
  nextExhibitionNumber: number;
  onCancel(): void;
  onComplete(): void;
  onDrawingChange(active: boolean): void;
  onSubmit(payload: LabDeliveryCreatePayload): Promise<void>;
};

export function LabDeliveryFlow({
  clientName, deliveredByName, defaultRecipientName, equipment, isPartial, nextExhibitionNumber,
  onCancel, onComplete, onDrawingChange, onSubmit,
}: Props) {
  const [state, setState] = useState(() => createDeliveryWizardState(defaultRecipientName));
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const submissionLock = useRef(new SignatureSubmissionLock());

  const groups = useMemo(() => {
    const byWorkOrder = new Map<number, { folio: number; items: LabDeliveryPendingEquipmentItem[] }>();
    for (const item of equipment) {
      const bucket = byWorkOrder.get(item.work_order_id) ?? { folio: item.work_order_folio, items: [] };
      bucket.items.push(item);
      byWorkOrder.set(item.work_order_id, bucket);
    }
    return Array.from(byWorkOrder.values()).sort((a, b) => a.folio - b.folio);
  }, [equipment]);

  function goTo(step: Parameters<typeof goToStep>[1]) {
    setError('');
    setState((current) => goToStep(current, step));
  }

  function continueFromRecipient() {
    const validationError = validateContinueFromRecipient(state);
    if (validationError) { setError(validationError); return; }
    goTo('delivered_by_signature');
  }

  function continueFromDeliveredBySignature() {
    const validationError = validateContinueFromDeliveredBySignature(state);
    if (validationError) { setError(validationError); return; }
    goTo('recipient_signature');
  }

  async function submit() {
    const validationError = validateSubmitDelivery(state);
    if (validationError) { setError(validationError); return; }
    if (!submissionLock.current.begin()) return;
    setError('');
    setSubmitting(true);
    try {
      await onSubmit(buildDeliveryPayload(state));
      submissionLock.current.finish();
      setSubmitting(false);
      goTo('success');
      setTimeout(onComplete, SUCCESS_CONFIRMATION_MS);
      return;
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : 'No fue posible registrar la entrega. Intenta nuevamente.');
    }
    submissionLock.current.finish();
    setSubmitting(false);
  }

  if (state.step === 'success') {
    return (
      <SuccessTransition
        subtitle={isPartial ? 'La exhibición parcial quedó registrada.' : 'La exhibición se registró correctamente.'}
        title="Entrega registrada"
      />
    );
  }

  const stepIndex = { review: 1, recipient: 2, delivered_by_signature: 3, recipient_signature: 4 }[state.step];

  return (
    <View>
      <Text style={styles.eyebrow}>
        {isPartial ? 'ENTREGA PARCIAL AUTORIZADA' : 'ENTREGA DE EQUIPOS'} · PASO {stepIndex} DE 4
      </Text>

      {state.step === 'review' && (
        <>
          <Text style={styles.title}>Revisión de entrega</Text>
          <View style={styles.summaryCard}>
            <Text style={styles.summaryLine}><Text style={styles.summaryLabel}>Cliente: </Text>{clientName}</Text>
            <Text style={styles.summaryLine}><Text style={styles.summaryLabel}>Tipo: </Text>{isPartial ? 'Entrega parcial' : 'Entrega completa'}</Text>
            <Text style={styles.summaryLine}><Text style={styles.summaryLabel}>Exhibición: </Text>{nextExhibitionNumber}</Text>
            <Text style={styles.summaryLine}><Text style={styles.summaryLabel}>Equipos: </Text>{equipment.length}</Text>
          </View>
          <Text style={styles.label}>Método de entrega</Text>
          <View style={styles.methodRow}>
            {METHOD_OPTIONS.map((option) => (
              <Pressable
                key={option.value}
                onPress={() => setState((current) => ({ ...current, deliveryMethod: option.value }))}
                style={[styles.methodChip, state.deliveryMethod === option.value && styles.methodChipActive]}
              >
                <Text style={[styles.methodChipText, state.deliveryMethod === option.value && styles.methodChipTextActive]}>{option.label}</Text>
              </Pressable>
            ))}
          </View>
          {groups.map((group) => (
            <View key={group.folio} style={styles.group}>
              <Text style={styles.groupTitle}>OT {group.folio}</Text>
              {group.items.map((item) => (
                <Text key={item.equipment_id} style={styles.equipment}>{item.instrument} · {item.brand} · {item.serial_number}</Text>
              ))}
            </View>
          ))}
          <PrimaryButton icon="arrow-right-circle" label="Continuar" onPress={() => goTo('recipient')} />
          <SecondaryButton icon="close" label="Cancelar" onPress={onCancel} />
        </>
      )}

      {state.step === 'recipient' && (
        <>
          <Text style={styles.title}>Persona que recibe</Text>
          <Text style={styles.label}>Nombre de quien recibe *</Text>
          <TextInput onChangeText={(value) => { setError(''); setState((current) => ({ ...current, recipientName: value })); }} style={styles.input} value={state.recipientName} />
          <Text style={styles.label}>Observaciones de entrega</Text>
          <TextInput multiline onChangeText={(value) => setState((current) => ({ ...current, notes: value }))} style={[styles.input, styles.notes]} value={state.notes} />
          {!!error && <AlertBanner tone="danger">{error}</AlertBanner>}
          <PrimaryButton icon="arrow-right-circle" label="Continuar a firmas" onPress={continueFromRecipient} />
          <SecondaryButton icon="arrow-left" label="Volver" onPress={() => goTo('review')} />
        </>
      )}

      {state.step === 'delivered_by_signature' && (
        <>
          <Text style={styles.title}>Firma de quien entrega</Text>
          <Text style={styles.readOnlyLabel}>Entrega</Text>
          <Text style={styles.readOnlyValue}>{deliveredByName}</Text>
          <MobileSignaturePad
            capture={state.deliveredByCapture}
            disabled={submitting}
            key="delivered-by-signature"
            label="Firma de quien entrega"
            onChange={(capture) => { setError(''); setState((current) => ({ ...current, deliveredByCapture: capture })); }}
            onDrawingChange={onDrawingChange}
          />
          {!!error && <AlertBanner tone="danger">{error}</AlertBanner>}
          <PrimaryButton icon="arrow-right-circle" label="Continuar con receptor" onPress={continueFromDeliveredBySignature} />
          <SecondaryButton icon="arrow-left" label="Volver" onPress={() => goTo('recipient')} />
        </>
      )}

      {state.step === 'recipient_signature' && (
        <>
          <Text style={styles.title}>Firma de quien recibe</Text>
          <Text style={styles.readOnlyLabel}>Recibe</Text>
          <Text style={styles.readOnlyValue}>{state.recipientName}</Text>
          <MobileSignaturePad
            capture={state.recipientCapture}
            disabled={submitting}
            key="recipient-signature"
            label="Firma de quien recibe"
            onChange={(capture) => { setError(''); setState((current) => ({ ...current, recipientCapture: capture })); }}
            onDrawingChange={onDrawingChange}
          />
          <Text style={styles.conformity}>
            {isPartial
              ? 'Recibí de conformidad los equipos relacionados en esta entrega parcial.'
              : 'Recibí de conformidad los equipos relacionados en este acuse.'}
          </Text>
          {!!error && <AlertBanner tone="danger">{error}</AlertBanner>}
          <PrimaryButton icon="package-check" label="Confirmar entrega" loading={submitting} onPress={() => void submit()} />
          <SecondaryButton disabled={submitting} icon="arrow-left" label="Volver" onPress={() => goTo('delivered_by_signature')} />
        </>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  conformity: { color: '#7a5414', fontSize: 13, marginTop: 14, textAlign: 'center' },
  equipment: { color: '#52636f', fontSize: 13, marginTop: 3 },
  eyebrow: { color: '#08756f', fontSize: 12, fontWeight: '900', letterSpacing: 1, marginBottom: 7 },
  group: { marginTop: 10 },
  groupTitle: { color: '#142b3a', fontSize: 14, fontWeight: '800' },
  input: { backgroundColor: '#fff', borderColor: '#aebfc8', borderRadius: 11, borderWidth: 1, fontSize: 16, minHeight: 50, paddingHorizontal: 14 },
  label: { color: '#344553', fontSize: 14, fontWeight: '800', marginBottom: 8, marginTop: 16 },
  methodChip: { backgroundColor: '#eef2f5', borderRadius: 18, marginRight: 8, paddingHorizontal: 14, paddingVertical: 10 },
  methodChipActive: { backgroundColor: '#08756f' },
  methodChipText: { color: '#425563', fontWeight: '700' },
  methodChipTextActive: { color: '#fff' },
  methodRow: { flexDirection: 'row' },
  notes: { minHeight: 90, paddingTop: 12, textAlignVertical: 'top' },
  readOnlyLabel: { color: '#637280', fontSize: 12, fontWeight: '800', marginTop: 14, textTransform: 'uppercase' },
  readOnlyValue: { color: '#142b3a', fontSize: 18, fontWeight: '800', marginBottom: 6, marginTop: 2 },
  summaryCard: { backgroundColor: '#fff', borderColor: '#d6e1e6', borderRadius: 14, borderWidth: 1, gap: 4, marginTop: 8, padding: 14 },
  summaryLabel: { color: '#637280', fontWeight: '700' },
  summaryLine: { color: '#142b3a', fontSize: 14 },
  title: { color: '#142b3a', fontSize: 26, fontWeight: '900', marginBottom: 8 },
});
