import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { LabClientPickerModal } from '@/src/components/lab/LabClientPickerModal';
import { colors } from '@/src/design/tokens';
import type { LabClient } from '@/src/types/lab-work-order';

type Request = <T>(path: string, init?: RequestInit) => Promise<T>;

type Props = {
  clientId: number | null;
  clientName: string;
  address: string;
  request: Request;
  /** Única autoridad que mapea el cliente al formulario de OT (selectLabClient). */
  onSelect(client: LabClient): void;
};

/**
 * Campo "Cliente" de Datos generales de la OT LAB. Sólo decide la
 * presentación: sin cliente muestra "Elegir cliente"; con cliente muestra la
 * tarjeta existente y "Cambiar cliente". Ambos abren LabClientPickerModal.
 *
 * "Cambiar cliente" es transaccional: nunca borra el cliente actual; sólo
 * `onSelect` (al elegir o crear otro) lo reemplaza. Cerrar el modal no
 * modifica la OT.
 */
export function LabWorkOrderClientField({ clientId, clientName, address, request, onSelect }: Props) {
  const [pickerOpen, setPickerOpen] = useState(false);

  return (
    <>
      {clientId ? (
        <View style={styles.selectedClient}>
          <Text style={styles.clientChoiceTitle}>{clientName}</Text>
          <Text style={styles.clientChoiceMeta}>{address}</Text>
          <Pressable
            accessibilityLabel="Cambiar cliente"
            accessibilityRole="button"
            hitSlop={8}
            onPress={() => setPickerOpen(true)}
            style={styles.changeClientAction}
          >
            <Text style={styles.change}>Cambiar cliente</Text>
          </Pressable>
        </View>
      ) : (
        <Pressable
          accessibilityLabel="Elegir cliente"
          accessibilityRole="button"
          onPress={() => setPickerOpen(true)}
          style={({ pressed }) => [styles.chooseClient, pressed && styles.chooseClientPressed]}
        >
          <MaterialCommunityIcons name="account-search-outline" size={20} color={colors.primary} />
          <Text style={styles.chooseClientText}>Elegir cliente</Text>
        </Pressable>
      )}
      <LabClientPickerModal
        onClose={() => setPickerOpen(false)}
        onSelect={onSelect}
        request={request}
        visible={pickerOpen}
      />
    </>
  );
}

const styles = StyleSheet.create({
  // Tarjeta de cliente seleccionado: mismos valores que tenía en work-orders.tsx.
  selectedClient: {
    marginBottom: 16,
    backgroundColor: '#e4f4ef',
    borderColor: '#75b9a7',
    borderRadius: 10,
    borderWidth: 1,
    gap: 4,
    padding: 11,
  },
  clientChoiceTitle: {
    color: '#142b3a',
    fontWeight: '800',
  },
  clientChoiceMeta: {
    color: '#667582',
    fontSize: 12,
    marginTop: 3,
  },
  change: {
    color: '#0067a8',
    fontWeight: '700',
  },
  changeClientAction: {
    alignSelf: 'flex-start',
    justifyContent: 'center',
    minHeight: 44,
  },
  chooseClient: {
    alignItems: 'center',
    backgroundColor: '#fff',
    borderColor: '#0067a8',
    borderRadius: 10,
    borderWidth: 1,
    flexDirection: 'row',
    gap: 8,
    justifyContent: 'center',
    marginBottom: 16,
    minHeight: 48,
    paddingHorizontal: 14,
  },
  chooseClientPressed: {
    backgroundColor: '#eaf3fa',
  },
  chooseClientText: {
    color: '#0067a8',
    fontSize: 16,
    fontWeight: '800',
  },
});
