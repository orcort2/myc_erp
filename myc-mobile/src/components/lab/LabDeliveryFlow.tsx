import { useState } from 'react';
import { Pressable, StyleSheet, Text, TextInput, View } from 'react-native';

import { AlertBanner, PrimaryButton, SecondaryButton } from '@/src/design/primitives';
import { MobileSignaturePad } from '@/src/components/signatures/MobileSignaturePad';
import { emptySignatureCapture, hasSignificantSignatureCapture, type SignatureCapture } from '@/src/components/signatures/signature-flow-state';
import type { LabDeliveryCreatePayload, LabDeliveryMethod, LabDeliveryPendingEquipmentItem } from '@/src/types/lab-work-order';

const METHOD_OPTIONS: { value: LabDeliveryMethod; label: string }[] = [
  { value: 'direct', label: 'Entrega directa' },
  { value: 'client_pickup', label: 'Recolección por cliente' },
];

type Props = {
  busy: boolean;
  clientName: string;
  defaultRecipientName: string;
  equipment: LabDeliveryPendingEquipmentItem[];
  isPartial: boolean;
  onCancel(): void;
  onDrawingChange(active: boolean): void;
  onSubmit(payload: LabDeliveryCreatePayload): Promise<void>;
};

export function LabDeliveryFlow({
  busy, clientName, defaultRecipientName, equipment, isPartial, onCancel, onDrawingChange, onSubmit,
}: Props) {
  const [deliveryMethod, setDeliveryMethod] = useState<LabDeliveryMethod>('direct');
  const [recipientName, setRecipientName] = useState(defaultRecipientName);
  const [notes, setNotes] = useState('');
  const [deliveredByCapture, setDeliveredByCapture] = useState<SignatureCapture>(emptySignatureCapture());
  const [recipientCapture, setRecipientCapture] = useState<SignatureCapture>(emptySignatureCapture());
  const [error, setError] = useState('');
  const valid = recipientName.trim().length > 0
    && hasSignificantSignatureCapture(deliveredByCapture)
    && hasSignificantSignatureCapture(recipientCapture);

  async function submit() {
    if (!valid || busy) {
      setError(
        !recipientName.trim() ? 'Escribe el nombre de quien recibe.'
          : !hasSignificantSignatureCapture(deliveredByCapture) ? 'Captura la firma de quien entrega.'
          : 'Captura la firma de quien recibe.',
      );
      return;
    }
    setError('');
    await onSubmit({
      delivery_method: deliveryMethod,
      delivered_by_signature_data_url: deliveredByCapture.dataUrl,
      recipient_name: recipientName.trim(),
      recipient_signature_data_url: recipientCapture.dataUrl,
      notes: notes.trim() || null,
    });
  }

  return (
    <View>
      <Text style={styles.eyebrow}>{isPartial ? 'ENTREGA PARCIAL AUTORIZADA' : 'ENTREGA DE EQUIPOS'}</Text>
      <Text style={styles.title}>{isPartial ? 'Ejecutar entrega parcial' : 'Entrega de equipos'}</Text>
      <Text style={styles.summary}>{clientName} · {equipment.length} equipo(s) {isPartial ? 'autorizado(s)' : 'pendiente(s)'}</Text>
      {equipment.map((item) => (
        <Text key={item.equipment_id} style={styles.equipment}>
          OT {item.work_order_folio} · {item.instrument} · {item.brand} · {item.serial_number}
        </Text>
      ))}
      <Text style={styles.label}>Método de entrega</Text>
      <View style={styles.methodRow}>
        {METHOD_OPTIONS.map((option) => (
          <Pressable
            key={option.value}
            disabled={busy}
            onPress={() => setDeliveryMethod(option.value)}
            style={[styles.methodChip, deliveryMethod === option.value && styles.methodChipActive]}
          >
            <Text style={[styles.methodChipText, deliveryMethod === option.value && styles.methodChipTextActive]}>{option.label}</Text>
          </Pressable>
        ))}
      </View>
      <Text style={styles.label}>Nombre de quien recibe *</Text>
      <TextInput editable={!busy} onChangeText={(value) => { setRecipientName(value); setError(''); }} style={styles.input} value={recipientName} />
      <Text style={styles.label}>Observaciones de entrega</Text>
      <TextInput editable={!busy} multiline onChangeText={setNotes} style={[styles.input, styles.notes]} value={notes} />
      <MobileSignaturePad capture={deliveredByCapture} disabled={busy} label="Firma de quien entrega" onChange={(value) => { setDeliveredByCapture(value); setError(''); }} onDrawingChange={onDrawingChange} />
      <MobileSignaturePad capture={recipientCapture} disabled={busy} label="Firma de quien recibe" onChange={(value) => { setRecipientCapture(value); setError(''); }} onDrawingChange={onDrawingChange} />
      {!!error && <AlertBanner tone="danger">{error}</AlertBanner>}
      <Text style={styles.warning}>
        {isPartial
          ? 'Recibí de conformidad los equipos relacionados en esta entrega parcial.'
          : 'Recibí de conformidad los equipos relacionados en este acuse.'}
      </Text>
      <PrimaryButton disabled={!valid} label="Confirmar entrega" loading={busy} onPress={() => void submit()} />
      <SecondaryButton disabled={busy} label="Cancelar" onPress={onCancel} />
    </View>
  );
}

const styles = StyleSheet.create({
  equipment: { color: '#52636f', fontSize: 13, marginBottom: 4 },
  eyebrow: { color: '#08756f', fontSize: 12, fontWeight: '900', letterSpacing: 1 },
  input: { backgroundColor: '#fff', borderColor: '#aebfc8', borderRadius: 11, borderWidth: 1, fontSize: 16, minHeight: 50, paddingHorizontal: 14 },
  label: { color: '#344553', fontSize: 14, fontWeight: '800', marginBottom: 8, marginTop: 16 },
  methodChip: { backgroundColor: '#eef2f5', borderRadius: 18, marginRight: 8, paddingHorizontal: 14, paddingVertical: 10 },
  methodChipActive: { backgroundColor: '#08756f' },
  methodChipText: { color: '#425563', fontWeight: '700' },
  methodChipTextActive: { color: '#fff' },
  methodRow: { flexDirection: 'row' },
  notes: { minHeight: 90, paddingTop: 12, textAlignVertical: 'top' },
  summary: { color: '#637280', fontSize: 15, marginBottom: 14 },
  title: { color: '#142b3a', fontSize: 26, fontWeight: '900', marginBottom: 8 },
  warning: { color: '#7a5414', fontSize: 13, marginTop: 14 },
});
