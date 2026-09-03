import { useEffect, useMemo, useRef, useState } from 'react';
import {
  Alert,
  KeyboardAvoidingView,
  Modal,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
  useWindowDimensions,
} from 'react-native';
import { SafeAreaProvider, SafeAreaView } from 'react-native-safe-area-context';

import { colors, radius, spacing, typography } from '@/src/design/tokens';
import { PrimaryButton } from '@/src/design/primitives';
import { computeSectionProgress } from '@/src/services/field-sheet-progress';
import {
  addRow,
  canCloseWithoutConfirmation,
  exitAfterSuccessfulSave,
  initWorkspaceState,
  markSaveError,
  markSaved,
  markSaving,
  removeRow,
  setCellValue,
  type SaveState,
} from '@/src/services/field-sheet-results-workspace-state';
import { keyboardTypeForFieldType } from '@/src/services/field-sheet-contract';
import { computeTableLayout } from '@/src/services/field-sheet-table-layout';
import {
  buildGroupedHeaderLayout,
  declaredWidth,
  rowLabel,
} from '@/src/services/field-sheet-result-layout';
import type {
  FieldSheetResultRow,
  FieldSheetResultSection,
} from '@/src/types/lab-work-order';
import { ApiError } from '@/src/api/client';

type Props = {
  visible: boolean;
  title: string;
  sections: FieldSheetResultSection[];
  rows: FieldSheetResultRow[];
  readOnly?: boolean;
  onClose(): void;
  onSave(rows: FieldSheetResultRow[]): Promise<void>;
};

const SAVE_STATE_LABEL: Record<SaveState, string> = {
  idle: 'Sin cambios',
  dirty: 'Cambios pendientes',
  saving: 'Guardando…',
  saved: 'Guardado',
  error: 'Error al guardar',
};

function saveStateColor(state: SaveState): string {
  if (state === 'error') return colors.danger;
  if (state === 'saved') return colors.success;
  if (state === 'dirty') return colors.warningStrong;

  return colors.textSubtle;
}

/**
 * Fase 6:
 *
 * Workspace fullscreen de resultados.
 *
 * Este componente no contiene comportamiento específico por instrumento.
 * Renderiza exclusivamente a partir del contrato canónico:
 *
 * - result_sections
 * - columns
 * - rows
 * - table_family
 * - metadata
 *
 * El guardado es explícito:
 * nunca se realiza un PATCH por cada tecla.
 *
 * Si existen cambios sin guardar, el cierre exige confirmación.
 *
 * IMPORTANTE:
 * El manejo del teclado se delega a KeyboardAvoidingView y a los insets
 * nativos del ScrollView. No utilizar measureLayout/findNodeHandle para
 * desplazar manualmente TextInput, porque esa combinación no es estable
 * con refs de React Native/Fabric.
 */
export function FieldSheetResultsWorkspace({
  visible,
  title,
  sections,
  rows,
  readOnly,
  onClose,
  onSave,
}: Props) {
  /**
   * Reactivo a rotación.
   *
   * useWindowDimensions vuelve a renderizar cuando cambia la orientación.
   * computeTableLayout recalcula los anchos sin modificar los valores
   * capturados, ya que esos datos viven en workspace-state.
   */
  const { width } = useWindowDimensions();

  const [state, setState] = useState(() => initWorkspaceState(rows));
  const [cellErrors, setCellErrors] = useState<Record<string, string>>({});

  /**
   * Sólo se utiliza para navegación mediante "Next".
   *
   * NO utilizar estos refs para measureLayout/findNodeHandle.
   */
  const inputRefs = useRef(new Map<string, TextInput | null>());

  /**
   * El caller puede reabrir el workspace con una versión más reciente
   * de rows. Resincronizamos únicamente cuando el modal vuelve a abrirse,
   * nunca durante una edición activa por un render del padre.
   */
  
  const wasVisible = useRef(false);

  useEffect(() => {
    const justOpened = visible && !wasVisible.current;

    if (justOpened) {
      setState(initWorkspaceState(rows));
      setCellErrors({});
    }

    wasVisible.current = visible;
  }, [visible, rows]);

  const progressBySection = useMemo(
    () =>
      sections.map((section) =>
        computeSectionProgress(section, state.rows),
      ),
    [sections, state.rows],
  );

  async function handleSave(): Promise<boolean> {
    setState((current) => markSaving(current));

    try {
      await onSave(state.rows);

      setState((current) =>
        markSaved(current, current.rows),
      );

      return true;
    } catch (error) {
      if (error instanceof ApiError) {
        setCellErrors(Object.fromEntries(error.fieldErrors.map((item) => {
          const leaf = item.field.split('.').at(-1) ?? item.field;
          return [leaf, item.message];
        })));
      }
      setState((current) =>
        markSaveError(
          current,
          error instanceof Error
            ? error.message
            : 'No fue posible guardar',
        ),
      );

      return false;
    }
  }

  function requestClose() {
    if (canCloseWithoutConfirmation(state)) {
      onClose();
      return;
    }

    Alert.alert(
      'Cambios sin guardar',
      'Tienes cambios en Resultados que no se han guardado. ¿Qué deseas hacer?',
      [
        {
          text: 'Seguir editando',
          style: 'cancel',
        },
        {
          text: 'Descartar',
          style: 'destructive',
          onPress: onClose,
        },
        {
          text: 'Guardar y salir',
          onPress: () =>
            exitAfterSuccessfulSave(handleSave, onClose),
        },
      ],
    );
  }

  /**
   * Navegación entre campos utilizando el botón "Next" del teclado.
   *
   * Esto sólo llama focus() sobre el siguiente TextInput.
   * El scroll vertical queda bajo responsabilidad de React Native/iOS.
   */
  function focusNext(key: string) {
    inputRefs.current.get(key)?.focus();
  }

  return (
    <Modal
      animationType="slide"
      onRequestClose={requestClose}
      presentationStyle="fullScreen"
      visible={visible}
    >
      <SafeAreaProvider>
        <SafeAreaView
          edges={['top', 'right', 'bottom', 'left']}
          style={styles.screen}
        >
          <View style={styles.header}>
            <View style={styles.headerText}>
              <Text style={styles.eyebrow}>
                RESULTADOS
              </Text>

              <Text style={styles.title}>
                {title}
              </Text>

              <Text
                style={[
                  styles.saveStateText,
                  {
                    color: saveStateColor(state.saveState),
                  },
                ]}
              >
                {SAVE_STATE_LABEL[state.saveState]}
              </Text>

              {state.saveState === 'error' &&
                state.errorMessage && (
                  <Text style={styles.errorText}>
                    {state.errorMessage}
                  </Text>
                )}
            </View>

            <Pressable onPress={requestClose}>
              <Text style={styles.close}>
                Cerrar
              </Text>
            </Pressable>
          </View>

          <KeyboardAvoidingView
            behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
            keyboardVerticalOffset={0}
            style={styles.flex}
          >
            <ScrollView
              automaticallyAdjustKeyboardInsets={Platform.OS === 'ios'}
              contentContainerStyle={styles.content}
              keyboardDismissMode={
                Platform.OS === 'ios'
                  ? 'interactive'
                  : 'on-drag'
              }
              keyboardShouldPersistTaps="handled"
              nestedScrollEnabled
              style={styles.flex}
            >
              {sections.map((section, sectionIndex) => {
                const progress =
                  progressBySection[sectionIndex];

                const sectionRows =
                  state.rows.filter(
                    (row) =>
                      row.section_key === section.key,
                  );

                const columnCount =
                  section.columns.length;

                const availableTableWidth = width - spacing.lg * 2;
                const layout =
                  computeTableLayout(
                    availableTableWidth,
                    columnCount,
                  );

                const rowNumberWidth = declaredWidth(
                  section.layout?.row_number_width,
                  availableTableWidth,
                  32,
                );
                const columnWidths = section.columns.map((column) =>
                  declaredWidth(
                    column.width,
                    availableTableWidth - rowNumberWidth,
                    layout.columnWidth,
                  ),
                );
                const logicalColumnWidths = [rowNumberWidth, ...columnWidths];
                const groupedHeaderLayout = buildGroupedHeaderLayout(
                  section,
                  logicalColumnWidths,
                );
                const tableWidth = logicalColumnWidths.reduce(
                  (total, value) => total + value,
                  0,
                );

                return (
                  <View
                    key={section.key}
                    style={styles.sectionBlock}
                  >
                    <View style={styles.sectionHeader}>
                      <Text style={styles.sectionTitle}>
                        {section.title}
                      </Text>

                      <Text style={styles.sectionProgress}>
                        {progress.completed} /{' '}
                        {progress.totalRequired}{' '}
                        completos
                      </Text>
                    </View>

                    {progress.missing > 0 && (
                      <Text style={styles.sectionMissing}>
                        {progress.missing}{' '}
                        pendiente
                        {progress.missing === 1
                          ? ''
                          : 's'}
                      </Text>
                    )}

                    <ScrollView
                      horizontal={
                        tableWidth > availableTableWidth
                      }
                      keyboardShouldPersistTaps="handled"
                      nestedScrollEnabled
                      showsHorizontalScrollIndicator={
                        tableWidth > availableTableWidth
                      }
                    >
                      <View
                        style={{
                          width: tableWidth,
                        }}
                      >
                        {groupedHeaderLayout ? (
                          <View
                            style={[
                              styles.groupedHeader,
                              {
                                height: groupedHeaderLayout.totalHeight,
                                width: groupedHeaderLayout.totalWidth,
                              },
                            ]}
                          >
                            {groupedHeaderLayout.cells.map((positionedCell) => (
                              <Text
                                key={`${positionedCell.row}-${positionedCell.column}-${positionedCell.cell.column_key ?? positionedCell.cell.label}`}
                                numberOfLines={3}
                                style={[
                                  styles.tableHeaderCell,
                                  styles.groupedHeaderCell,
                                  {
                                    height: positionedCell.height,
                                    left: positionedCell.left,
                                    position: 'absolute',
                                    textAlign: positionedCell.cell.alignment ?? 'center',
                                    top: positionedCell.top,
                                    width: positionedCell.width,
                                  },
                                ]}
                              >
                                {positionedCell.cell.label}
                              </Text>
                            ))}
                          </View>
                        ) : (
                        <View style={styles.tableHeaderRow}>
                          <Text
                            style={[
                              styles.tableHeaderCell,
                              { width: rowNumberWidth },
                            ]}
                          >
                            #
                          </Text>

                          {section.columns.map(
                            (column, columnIndex) => (
                              <Text
                                key={column.key}
                                numberOfLines={2}
                                style={[
                                  styles.tableHeaderCell,
                                  {
                                    width:
                                      columnWidths[columnIndex],
                                  },
                                ]}
                              >
                                {column.label}
                              </Text>
                            ),
                          )}

                          {section.allow_remove_rows && (
                            <View style={{ width: 40 }} />
                          )}
                        </View>
                        )}

                        {sectionRows.map((row) => (
                          <View
                            key={`${section.key}-${row.row_number}`}
                            style={styles.tableRow}
                          >
                            <Text
                              style={[
                                styles.rowNumber,
                                { width: rowNumberWidth },
                              ]}
                            >
                              {rowLabel(section, row.row_number)}
                            </Text>

                            {section.columns.map(
                              (
                                column,
                                columnIndex,
                              ) => {
                                const cellKey =
                                  `${section.key}-${row.row_number}-${column.key}`;

                                const nextColumn =
                                  section.columns[
                                    columnIndex + 1
                                  ];

                                const nextKey =
                                  nextColumn
                                    ? `${section.key}-${row.row_number}-${nextColumn.key}`
                                    : null;

                                const editable =
                                  column.editable !==
                                    false &&
                                  !readOnly;

                                const sourceKey =
                                  column.source ??
                                  column.key;

                                return (
                                  <View key={column.key} style={{ width: columnWidths[columnIndex] }}>
                                  <TextInput
                                    editable={editable}
                                    keyboardType={keyboardTypeForFieldType(
                                      column.data_type,
                                    )}
                                    onChangeText={(
                                      value,
                                    ) => {
                                      setCellErrors((current) => {
                                        if (!(sourceKey in current)) return current;
                                        const next = { ...current };
                                        delete next[sourceKey];
                                        return next;
                                      });
                                      setState(
                                        (current) =>
                                          setCellValue(
                                            current,
                                            section.key,
                                            row.row_number,
                                            sourceKey,
                                            value,
                                          ),
                                      );
                                    }
                                    }
                                    onSubmitEditing={() => {
                                      if (nextKey) {
                                        focusNext(nextKey);
                                      }
                                    }}
                                    placeholder={
                                      column.label
                                    }
                                    ref={(instance) => {
                                      inputRefs.current.set(
                                        cellKey,
                                        instance,
                                      );
                                    }}
                                    returnKeyType={
                                      nextKey
                                        ? 'next'
                                        : 'done'
                                    }
                                    style={[
                                      styles.tableInput,
                                      { width: '100%' },
                                      !editable &&
                                        styles.tableInputReadOnly,
                                      !!cellErrors[sourceKey] && styles.tableInputError,
                                    ]}
                                    value={String(
                                      row.row_data[
                                        sourceKey
                                      ] ?? '',
                                    )}
                                  />
                                  {!!cellErrors[sourceKey] && (
                                    <Text style={styles.cellError}>
                                      {cellErrors[sourceKey]}
                                    </Text>
                                  )}
                                  </View>
                                );
                              },
                            )}

                            {section.allow_remove_rows && (
                              <Pressable
                                onPress={() =>
                                  setState(
                                    (current) =>
                                      removeRow(
                                        current,
                                        section,
                                        row.row_number,
                                      ),
                                  )
                                }
                                style={styles.removeRow}
                              >
                                <Text
                                  style={
                                    styles.removeRowText
                                  }
                                >
                                  ✕
                                </Text>
                              </Pressable>
                            )}
                          </View>
                        ))}
                      </View>
                    </ScrollView>

                    {section.allow_add_rows &&
                      !readOnly && (
                        <Pressable
                          onPress={() =>
                            setState((current) =>
                              addRow(
                                current,
                                section,
                              ),
                            )
                          }
                          style={styles.addRow}
                        >
                          <Text style={styles.addRowText}>
                            ＋ Agregar fila
                          </Text>
                        </Pressable>
                      )}
                  </View>
                );
              })}
            </ScrollView>

            {!readOnly && (
              <View style={styles.footer}>
                <PrimaryButton
                  disabled={state.saveState === 'saving'}
                  label="Guardar resultados"
                  loading={state.saveState === 'saving'}
                  onPress={() => {
                    void handleSave();
                  }}
                />
              </View>
            )}
          </KeyboardAvoidingView>
        </SafeAreaView>
      </SafeAreaProvider>
    </Modal>
  );
}

const styles = StyleSheet.create({
  flex: {
    flex: 1,
  },

  screen: {
    flex: 1,
    backgroundColor: colors.background,
  },

  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    padding: spacing.lg,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
    backgroundColor: colors.surface,
  },

  headerText: {
    flex: 1,
    gap: 2,
  },

  eyebrow: {
    ...typography.eyebrow,
    color: colors.accent,
  },

  title: {
    ...typography.title,
    color: colors.text,
  },

  saveStateText: {
    fontSize: 13,
    fontWeight: '700',
  },

  errorText: {
    color: colors.danger,
    fontSize: 12,
  },

  close: {
    color: colors.primary,
    fontWeight: '800',
    fontSize: 16,
    paddingTop: spacing.xs,
  },

  content: {
    padding: spacing.lg,
    gap: spacing.lg,
    paddingBottom: spacing.xl,
  },

  sectionBlock: {
    gap: spacing.sm,
    marginBottom: spacing.md,
  },

  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: spacing.sm,
  },

  sectionTitle: {
    ...typography.sectionTitle,
    color: colors.text,
    flex: 1,
  },

  sectionProgress: {
    ...typography.meta,
    color: colors.textMuted,
    fontWeight: '700',
  },

  sectionMissing: {
    color: colors.warningStrong,
    fontSize: 12,
    fontWeight: '700',
  },

  tableHeaderRow: {
    flexDirection: 'row',
    gap: spacing.xs,
    paddingBottom: spacing.xs,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },

  tableHeaderCell: {
    ...typography.label,
    color: colors.textMuted,
  },

  groupedHeaderCell: {
    borderColor: colors.border,
    borderWidth: 1,
    padding: spacing.xs,
    textAlignVertical: 'center',
  },

  groupedHeader: {
    position: 'relative',
  },

  tableRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.xs,
    paddingVertical: spacing.xs,
  },

  rowNumber: {
    color: colors.textSubtle,
    fontWeight: '700',
    textAlign: 'center',
  },

  tableInput: {
    borderColor: colors.borderStrong,
    borderRadius: radius.sm,
    borderWidth: 1,
    minHeight: 44,
    paddingHorizontal: spacing.sm,
    color: colors.text,
    backgroundColor: colors.surface,
  },

  tableInputReadOnly: {
    backgroundColor: colors.background,
    color: colors.textMuted,
  },

  tableInputError: {
    borderColor: colors.danger,
  },

  cellError: {
    color: colors.danger,
    fontSize: 10,
    marginTop: 2,
  },

  removeRow: {
    width: 40,
    alignItems: 'center',
    justifyContent: 'center',
  },

  removeRowText: {
    color: colors.danger,
    fontWeight: '800',
    fontSize: 16,
  },

  addRow: {
    alignItems: 'center',
    borderColor: colors.accent,
    borderRadius: radius.md,
    borderStyle: 'dashed',
    borderWidth: 1,
    padding: spacing.sm,
    marginTop: spacing.xs,
  },

  addRowText: {
    color: colors.accent,
    fontWeight: '800',
  },

  footer: {
    padding: spacing.lg,
    borderTopWidth: 1,
    borderTopColor: colors.border,
    backgroundColor: colors.surface,
  },

});
