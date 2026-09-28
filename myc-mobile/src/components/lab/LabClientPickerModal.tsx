import { useRef } from 'react';
import { KeyboardAvoidingView, Modal, Platform, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaProvider, SafeAreaView } from 'react-native-safe-area-context';

import { LabClientSelector, type LabClientSelectorBackHandler } from '@/src/components/lab/LabClientSelector';
import { CloseButton } from '@/src/design/primitives';
import { colors, spacing } from '@/src/design/tokens';
import type { LabClient } from '@/src/types/lab-work-order';

type Request = <T>(path: string, init?: RequestInit) => Promise<T>;

type Props = {
  visible: boolean;
  request: Request;
  onClose(): void;
  /** Autoridad del consumidor (en OT: selectLabClient). Se invoca una vez por selección. */
  onSelect(client: LabClient): void;
};

/**
 * Presentación modal del cliente receptor de la OT LAB. Sólo envuelve a
 * LabClientSelector (búsqueda + alta, la única implementación): no mapea
 * campos de cliente ni toca el formulario de la OT. Cerrar sin elegir no
 * modifica nada; elegir (o crear) delega en `onSelect` y después cierra.
 *
 * El contenido vive dentro del Modal: al ocultarse, RN lo desmonta y la
 * siguiente apertura empieza con búsqueda limpia.
 */
export function LabClientPickerModal({ visible, request, onClose, onSelect }: Props) {
  const selectorBack = useRef<LabClientSelectorBackHandler | null>(null);

  // Back de Android / cierre por sistema: si el selector está en alta, la
  // cancela (misma transición que "Cancelar") y el modal permanece abierto;
  // en búsqueda/resultados cierra el modal sin tocar la OT.
  function requestClose() {
    if (selectorBack.current?.()) return;
    onClose();
  }

  function select(client: LabClient) {
    onSelect(client);
    onClose();
  }

  return (
    <Modal animationType="slide" onRequestClose={requestClose} visible={visible}>
      <SafeAreaProvider>
        <SafeAreaView edges={['top', 'right', 'bottom', 'left']} style={styles.screen}>
          <View style={styles.header}>
            <Text accessibilityRole="header" style={styles.title}>Seleccionar cliente</Text>
            <CloseButton label="Cerrar" onPress={onClose} />
          </View>
          {/* Una autoridad por plataforma (misma política que el modal de OT):
              iOS ajusta insets en el ScrollView nativo; Android ajusta altura. */}
          <KeyboardAvoidingView
            enabled={Platform.OS === 'android'}
            behavior={Platform.OS === 'android' ? 'height' : undefined}
            style={styles.flex}
          >
            <ScrollView
              automaticallyAdjustKeyboardInsets={Platform.OS === 'ios'}
              contentContainerStyle={styles.content}
              keyboardShouldPersistTaps="handled"
              style={styles.flex}
            >
              <LabClientSelector backHandlerRef={selectorBack} request={request} onSelect={select} />
            </ScrollView>
          </KeyboardAvoidingView>
        </SafeAreaView>
      </SafeAreaProvider>
    </Modal>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  screen: { backgroundColor: colors.background, flex: 1 },
  header: {
    alignItems: 'center',
    borderBottomColor: colors.border,
    borderBottomWidth: 1,
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
  },
  title: { color: colors.text, flex: 1, fontSize: 18, fontWeight: '800' },
  content: { padding: spacing.lg },
});
