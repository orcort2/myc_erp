import { useMemo, useState } from 'react';
import { Pressable, StyleSheet, Text, TextInput, View } from 'react-native';

import { AdministrativeButton, AlertBanner, OperationalActionStack, SecondaryButton } from '@/src/design/primitives';
import type { LabDeliveryPendingEquipmentItem } from '@/src/types/lab-work-order';

type Props = {
  busy: boolean;
  onCancel(): void;
  onSubmit(payload: { requested_equipment_ids: number[]; reason: string; description: string }): Promise<void>;
  pendingEquipment: LabDeliveryPendingEquipmentItem[];
};

export function LabPartialDeliveryRequest({ busy, onCancel, onSubmit, pendingEquipment }: Props) {
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [reason, setReason] = useState('');
  const [error, setError] = useState('');

  const groups = useMemo(() => {
    const byWorkOrder = new Map<number, { folio: number; items: LabDeliveryPendingEquipmentItem[] }>();
    for (const item of pendingEquipment) {
      const bucket = byWorkOrder.get(item.work_order_id) ?? { folio: item.work_order_folio, items: [] };
      bucket.items.push(item);
      byWorkOrder.set(item.work_order_id, bucket);
    }
    return Array.from(byWorkOrder.entries())
      .sort(([, a], [, b]) => a.folio - b.folio)
      .map(([workOrderId, bucket]) => ({ workOrderId, ...bucket }));
  }, [pendingEquipment]);

  function toggle(equipmentId: number) {
    setSelected((current) => {
      const next = new Set(current);
      if (next.has(equipmentId)) next.delete(equipmentId); else next.add(equipmentId);
      return next;
    });
  }

  function toggleAllForWorkOrder(items: LabDeliveryPendingEquipmentItem[]) {
    const ids = items.map((item) => item.equipment_id);
    const allSelected = ids.every((id) => selected.has(id));
    setSelected((current) => {
      const next = new Set(current);
      ids.forEach((id) => (allSelected ? next.delete(id) : next.add(id)));
      return next;
    });
  }

  async function submit() {
    if (selected.size === 0 || !reason.trim()) {
      setError(selected.size === 0 ? 'Selecciona al menos un equipo.' : 'Escribe el motivo de la entrega parcial.');
      return;
    }
    setError('');
    await onSubmit({
      requested_equipment_ids: Array.from(selected),
      reason: reason.trim(),
      description: reason.trim(),
    });
  }

  return (
    <View>
      <Text style={styles.eyebrow}>EXCEPCIÓN OPERATIVA</Text>
      <Text style={styles.title}>Solicitar entrega parcial</Text>
      <Text style={styles.summary}>{selected.size} de {pendingEquipment.length} equipos seleccionados</Text>
      {groups.map((group) => {
        const ids = group.items.map((item) => item.equipment_id);
        const allSelected = ids.length > 0 && ids.every((id) => selected.has(id));
        return (
          <View key={group.workOrderId} style={styles.group}>
            <View style={styles.groupHeader}>
              <Text style={styles.groupTitle}>OT {group.folio}</Text>
              <Pressable disabled={busy} onPress={() => toggleAllForWorkOrder(group.items)}>
                <Text style={styles.selectAll}>{allSelected ? 'Deseleccionar todos' : 'Seleccionar todos'}</Text>
              </Pressable>
            </View>
            {group.items.map((item) => {
              const checked = selected.has(item.equipment_id);
              return (
                <Pressable key={item.equipment_id} disabled={busy} onPress={() => toggle(item.equipment_id)} style={styles.row}>
                  <View style={[styles.checkbox, checked && styles.checkboxChecked]}>{checked && <Text style={styles.checkboxMark}>✓</Text>}</View>
                  <Text style={styles.rowText}>{item.instrument} · {item.brand} · {item.serial_number}</Text>
                </Pressable>
              );
            })}
          </View>
        );
      })}
      <Text style={styles.label}>Motivo *</Text>
      <TextInput editable={!busy} multiline onChangeText={(value) => { setReason(value); setError(''); }} style={[styles.input, styles.reason]} value={reason} />
      {!!error && <AlertBanner tone="danger">{error}</AlertBanner>}
      <OperationalActionStack>
        <AdministrativeButton disabled={busy} icon="send" label="Solicitar entrega parcial" loading={busy} onPress={() => void submit()} />
        <SecondaryButton disabled={busy} icon="close" label="Cancelar" onPress={onCancel} />
      </OperationalActionStack>
    </View>
  );
}

const styles = StyleSheet.create({
  checkbox: { alignItems: 'center', borderColor: '#aebfc8', borderRadius: 6, borderWidth: 1.5, height: 22, justifyContent: 'center', marginRight: 12, width: 22 },
  checkboxChecked: { backgroundColor: '#08756f', borderColor: '#08756f' },
  checkboxMark: { color: '#fff', fontSize: 14, fontWeight: '900' },
  eyebrow: { color: '#a5691a', fontSize: 12, fontWeight: '900', letterSpacing: 1 },
  group: { backgroundColor: '#fff', borderRadius: 12, marginTop: 14, padding: 14 },
  groupHeader: { alignItems: 'center', flexDirection: 'row', justifyContent: 'space-between', marginBottom: 8 },
  groupTitle: { color: '#142b3a', fontSize: 16, fontWeight: '800' },
  input: { backgroundColor: '#fff', borderColor: '#aebfc8', borderRadius: 11, borderWidth: 1, fontSize: 16, paddingHorizontal: 14 },
  label: { color: '#344553', fontSize: 14, fontWeight: '800', marginBottom: 8, marginTop: 16 },
  reason: { minHeight: 90, paddingTop: 12, textAlignVertical: 'top' },
  row: { alignItems: 'center', flexDirection: 'row', paddingVertical: 8 },
  rowText: { color: '#344553', flexShrink: 1, fontSize: 14 },
  selectAll: { color: '#08756f', fontSize: 13, fontWeight: '800' },
  summary: { color: '#637280', fontSize: 15, marginBottom: 4, marginTop: 8 },
  title: { color: '#142b3a', fontSize: 26, fontWeight: '900', marginBottom: 8 },
});
