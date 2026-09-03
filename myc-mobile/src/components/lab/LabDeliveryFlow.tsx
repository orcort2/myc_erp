import { useState } from 'react';
import { StyleSheet, Text, TextInput, View } from 'react-native';

import { AlertBanner, PrimaryButton, SecondaryButton } from '@/src/design/primitives';
import { MobileSignaturePad } from '@/src/components/signatures/MobileSignaturePad';
import { emptySignatureCapture, hasSignificantSignatureCapture, type SignatureCapture } from '@/src/components/signatures/signature-flow-state';
import type { LabWorkOrder } from '@/src/types/lab-work-order';

type Props = {
  busy: boolean;
  onCancel(): void;
  onDrawingChange(active: boolean): void;
  onSubmit(payload: { recipient_name: string; recipient_signature_data_url: string; notes: string | null }): Promise<void>;
  workOrder: LabWorkOrder;
};

export function LabDeliveryFlow({ busy, onCancel, onDrawingChange, onSubmit, workOrder }: Props) {
  const [recipientName, setRecipientName] = useState(workOrder.contact_name ?? '');
  const [notes, setNotes] = useState('');
  const [capture, setCapture] = useState<SignatureCapture>(emptySignatureCapture());
  const [error, setError] = useState('');
  const valid = recipientName.trim().length > 0 && hasSignificantSignatureCapture(capture);

  async function submit() {
    if (!valid || busy) {
      setError(!recipientName.trim() ? 'Escribe el nombre de quien recibe.' : 'Captura la firma de quien recibe.');
      return;
    }
    setError('');
    await onSubmit({
      recipient_name: recipientName.trim(),
      recipient_signature_data_url: capture.dataUrl,
      notes: notes.trim() || null,
    });
  }

  return (
    <View>
      <Text style={styles.eyebrow}>ENTREGA DE EQUIPOS</Text>
      <Text style={styles.title}>Entrega de equipos</Text>
      <Text style={styles.summary}>OT {workOrder.folio} · {workOrder.client_name} · {workOrder.equipment.length} equipo(s)</Text>
      {workOrder.equipment.map((item) => <Text key={item.id} style={styles.equipment}>{item.position}. {item.instrument} · {item.brand} · {item.serial_number}</Text>)}
      <Text style={styles.label}>Nombre de quien recibe *</Text>
      <TextInput editable={!busy} onChangeText={(value) => { setRecipientName(value); setError(''); }} style={styles.input} value={recipientName} />
      <Text style={styles.label}>Observaciones de entrega</Text>
      <TextInput editable={!busy} multiline onChangeText={setNotes} style={[styles.input, styles.notes]} value={notes} />
      <MobileSignaturePad capture={capture} disabled={busy} label="Firma de quien recibe" onChange={(value) => { setCapture(value); setError(''); }} onDrawingChange={onDrawingChange} />
      {!!error && <AlertBanner tone="danger">{error}</AlertBanner>}
      <Text style={styles.warning}>Al confirmar se registrará la salida y se generará el acuse de entrega.</Text>
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
  notes: { minHeight: 90, paddingTop: 12, textAlignVertical: 'top' },
  summary: { color: '#637280', fontSize: 15, marginBottom: 14 },
  title: { color: '#142b3a', fontSize: 26, fontWeight: '900', marginBottom: 8 },
  warning: { color: '#7a5414', fontSize: 13, marginTop: 14 },
});
