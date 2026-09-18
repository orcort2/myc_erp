import { useEffect, useState } from 'react';
import { Alert, Pressable, StyleSheet, Text, View } from 'react-native';

import {
  ActionRow,
  AlertBanner,
  Card,
  DangerButton,
  Field,
  LoadingState,
  OperationalActionStack,
  Section,
  SecondaryButton,
} from '@/src/design/primitives';
import { colors, spacing } from '@/src/design/tokens';
import {
  ORIENTATION_LABELS,
  buildLabExternalStructurePayload,
  buildLabExternalValuesPatch,
  cellValue,
  emptyColumn,
  emptyGroup,
  emptyTable,
  findRow,
  labExternalTableProgress,
  readLabExternalDefinition,
  validateLabExternalStructure,
  type LabExternalGroup,
  type LabExternalOrientation,
  type LabExternalRow,
} from '@/src/services/lab-field-sheet-external';
import type { LabEquipment, LabFieldSheet, LabWorkOrder } from '@/src/types/lab-work-order';

type Request = <T>(path: string, init?: RequestInit) => Promise<T>;

type Props = {
  busy: boolean;
  readOnly: boolean;
  onSaved(sheet: LabFieldSheet): void;
  onDirtyChange(dirty: boolean): void;
  equipment: LabEquipment;
  request: Request;
  sheet: LabFieldSheet | null;
  setBusy(value: boolean): void;
  workOrder: LabWorkOrder;
};

const EDITABLE_STRUCTURE_STATUSES = new Set(['draft', 'in_progress']);

/** Editor especializado de resultados; captura, estados y acciones viven en LabTechnicalCapture. */
export function LabExternalFieldSheet({ busy, readOnly, onSaved, onDirtyChange, equipment, request, sheet, setBusy, workOrder }: Props) {
  const [groups, setGroups] = useState<LabExternalGroup[]>([]);
  const [rows, setRows] = useState<LabExternalRow[]>([]);
  const [structureDirty, setStructureDirty] = useState(false);
  const [valuesDirty, setValuesDirty] = useState(false);
  useEffect(() => { onDirtyChange(structureDirty || valuesDirty); }, [structureDirty, valuesDirty, onDirtyChange]);

  useEffect(() => {
    if (!sheet) return;
    setGroups(readLabExternalDefinition(sheet.template_definition).groups);
    setRows(sheet.results_rows as unknown as LabExternalRow[]);
    setStructureDirty(false);
    setValuesDirty(false);
  }, [sheet]);

  if (!sheet) {
    return <LoadingState label="Preparando hoja LAB EXTERNO..." />;
  }

  const editableValues = !busy && !readOnly && EDITABLE_STRUCTURE_STATUSES.has(sheet.status);
  const editableStructure = editableValues && !valuesDirty;
  const issues = validateLabExternalStructure(groups);

  function updateGroup(groupId: string, patch: Partial<LabExternalGroup>) {
    setGroups((current) => current.map((group) => (group.id === groupId ? { ...group, ...patch } : group)));
    setStructureDirty(true);
  }

  function addGroup() {
    setGroups((current) => {
      const group = emptyGroup(current.map((item) => item.id), current.length + 1);
      group.tables = [emptyTable(current.flatMap((item) => item.tables.map((table) => table.id)), 1)];
      return [...current, group];
    });
    setStructureDirty(true);
  }

  function removeGroup(groupId: string) {
    setGroups((current) => current.filter((group) => group.id !== groupId));
    setStructureDirty(true);
  }

  function addTable(groupId: string) {
    setGroups((current) => current.map((group) => {
      if (group.id !== groupId) return group;
      const existingIds = groups.flatMap((item) => item.tables.map((table) => table.id));
      return { ...group, tables: [...group.tables, emptyTable(existingIds, group.tables.length + 1)] };
    }));
    setStructureDirty(true);
  }

  function removeTable(groupId: string, tableId: string) {
    setGroups((current) => current.map((group) => (
      group.id === groupId ? { ...group, tables: group.tables.filter((table) => table.id !== tableId) } : group
    )));
    setStructureDirty(true);
  }

  function updateTable(groupId: string, tableId: string, patch: Partial<LabExternalGroup['tables'][number]>) {
    setGroups((current) => current.map((group) => (
      group.id !== groupId ? group : {
        ...group,
        tables: group.tables.map((table) => (table.id === tableId ? { ...table, ...patch } : table)),
      }
    )));
    setStructureDirty(true);
  }

  function addColumn(groupId: string, tableId: string) {
    setGroups((current) => current.map((group) => (
      group.id !== groupId ? group : {
        ...group,
        tables: group.tables.map((table) => (
          table.id === tableId ? { ...table, columns: [...table.columns, emptyColumn(table.columns)] } : table
        )),
      }
    )));
    setStructureDirty(true);
  }

  function removeColumn(groupId: string, tableId: string, columnKey: string) {
    setGroups((current) => current.map((group) => (
      group.id !== groupId ? group : {
        ...group,
        tables: group.tables.map((table) => (
          table.id === tableId ? { ...table, columns: table.columns.filter((column) => column.key !== columnKey) } : table
        )),
      }
    )));
    setStructureDirty(true);
  }

  function updateCell(tableId: string, rowNumber: number, columnKey: string, value: string) {
    setRows((current) => {
      const existing = findRow(current, tableId, rowNumber);
      if (!existing) return current;
      return current.map((row) => (
        row === existing ? { ...row, row_data: { ...row.row_data, [columnKey]: value } } : row
      ));
    });
    setValuesDirty(true);
  }

  async function saveStructure() {
    if (!editableStructure || valuesDirty) return;
    if (issues.length) {
      Alert.alert('Revisa la estructura', issues[0]);
      return;
    }
    setBusy(true);
    try {
      await request<LabFieldSheet>(
        `/mobile/v1/technician/lab-work-orders/${workOrder.id}/equipment/${equipment.id}/field-sheet/lab-externo/structure`,
        { method: 'PUT', body: JSON.stringify(buildLabExternalStructurePayload(groups)) },
      );
      const reloaded = await request<LabFieldSheet>(
        `/mobile/v1/technician/lab-work-orders/${workOrder.id}/equipment/${equipment.id}/field-sheet`,
      );
      onSaved(reloaded);
      setRows(reloaded.results_rows as unknown as LabExternalRow[]);
      setStructureDirty(false);
    } catch (error) {
      Alert.alert('No fue posible guardar la estructura', error instanceof Error ? error.message : 'Intenta nuevamente');
    } finally {
      setBusy(false);
    }
  }

  async function saveValues() {
    if (!editableValues || structureDirty) return;
    setBusy(true);
    try {
      const saved = await request<LabFieldSheet>(
        `/mobile/v1/technician/lab-work-orders/${workOrder.id}/equipment/${equipment.id}/field-sheet`,
        { method: 'PATCH', body: JSON.stringify(buildLabExternalValuesPatch(rows)) },
      );
      onSaved(saved);
      setValuesDirty(false);
    } catch (error) {
      Alert.alert('No fue posible guardar los valores', error instanceof Error ? error.message : 'Intenta nuevamente');
    } finally {
      setBusy(false);
    }
  }

  return (
    <View>
      {!readOnly && (structureDirty || valuesDirty) && (
        <AlertBanner tone="info">{structureDirty ? 'Guarda la estructura antes de capturar valores.' : 'Guarda los valores antes de cambiar la estructura.'}</AlertBanner>
      )}

      {readOnly && (
        <AlertBanner tone="info">La estructura y los valores ya no pueden editarse desde este estado.</AlertBanner>
      )}

      <Section title="Grupos de tablas" description="Cada grupo comparte una sola orientación (Patrón → IBC o IBC → Patrón); cada tabla dentro del grupo define sus propias columnas y filas.">
        {groups.length === 0 && <Text style={styles.empty}>Todavía no hay grupos definidos.</Text>}
        {groups.map((group) => (
          <Card key={group.id}>
            {editableStructure ? (
              <>
                <Field label="Título del grupo" value={group.title} onChange={(value) => updateGroup(group.id, { title: value })} />
                <Text style={styles.label}>Orientación</Text>
                <View style={styles.choiceRow}>
                  {(Object.keys(ORIENTATION_LABELS) as LabExternalOrientation[]).map((orientation) => (
                    <Pressable
                      key={orientation}
                      onPress={() => updateGroup(group.id, { orientation })}
                      style={[styles.choice, group.orientation === orientation && styles.choiceActive]}
                    >
                      <Text style={group.orientation === orientation ? styles.choiceTextActive : styles.choiceText}>
                        {ORIENTATION_LABELS[orientation]}
                      </Text>
                    </Pressable>
                  ))}
                </View>
              </>
            ) : (
              <>
                <Text style={styles.groupTitleReadOnly}>{group.title}</Text>
                <Text style={styles.groupOrientationReadOnly}>Orientación: {ORIENTATION_LABELS[group.orientation]}</Text>
              </>
            )}

            {group.tables.map((table) => (
              <View key={table.id} style={styles.tableBlock}>
                {editableStructure ? (
                  <>
                    <Field label="Título de la tabla" value={table.title} onChange={(value) => updateTable(group.id, table.id, { title: value })} />
                    <Text style={styles.label}>Columnas</Text>
                    {table.columns.map((column) => (
                      <View key={column.key} style={styles.columnRow}>
                        <View style={styles.columnField}>
                          <Field label="" value={column.label} onChange={(value) => updateTable(group.id, table.id, {
                            columns: table.columns.map((item) => (item.key === column.key ? { ...item, label: value } : item)),
                          })} />
                        </View>
                        {table.columns.length > 1 && (
                          <Pressable onPress={() => removeColumn(group.id, table.id, column.key)}>
                            <Text style={styles.removeLink}>Quitar</Text>
                          </Pressable>
                        )}
                      </View>
                    ))}
                    <SecondaryButton icon="plus" label="+ Columna" onPress={() => addColumn(group.id, table.id)} />
                    <Field
                      keyboardType="phone-pad"
                      label="Número de filas"
                      value={String(table.row_count)}
                      onChange={(value) => updateTable(group.id, table.id, { row_count: Math.max(1, Number(value.replace(/\D/g, '')) || 1) })}
                    />
                  </>
                ) : (
                  <Text style={styles.tableTitleReadOnly}>{table.title}</Text>
                )}

                <Text style={styles.meta}>
                  {labExternalTableProgress(table, rows).completed} / {table.row_count} filas capturadas
                </Text>
                <View style={styles.valuesTable}>
                  <View style={styles.valuesRow}>
                    <Text style={styles.valuesHeaderCell}>#</Text>
                    {table.columns.map((column) => <Text key={column.key} style={styles.valuesHeaderCell}>{column.label}</Text>)}
                  </View>
                  {Array.from({ length: table.row_count }, (_, index) => index + 1).map((rowNumber) => (
                    <View key={rowNumber} style={styles.valuesRow}>
                      <Text style={styles.valuesRowNumber}>{rowNumber}</Text>
                      {table.columns.map((column) => (
                        editableValues && !structureDirty ? (
                          <View key={column.key} style={styles.valuesCell}>
                            <Field
                              label=""
                              value={cellValue(rows, table.id, rowNumber, column.key)}
                              onChange={(value) => updateCell(table.id, rowNumber, column.key, value)}
                            />
                          </View>
                        ) : (
                          <Text key={column.key} style={styles.valuesCellReadOnly}>{cellValue(rows, table.id, rowNumber, column.key) || '—'}</Text>
                        )
                      ))}
                    </View>
                  ))}
                </View>

                {editableStructure && (
                  <DangerButton icon="trash-can-outline" label="Eliminar tabla" onPress={() => removeTable(group.id, table.id)} />
                )}
              </View>
            ))}

            {editableStructure && (
              <ActionRow>
                <SecondaryButton icon="plus" label="+ Agregar tabla" onPress={() => addTable(group.id)} />
                <DangerButton icon="trash-can-outline" label="Eliminar grupo" onPress={() => removeGroup(group.id)} />
              </ActionRow>
            )}
          </Card>
        ))}

        {editableStructure && (
          <SecondaryButton icon="plus" label="+ Agregar grupo" onPress={addGroup} />
        )}
      </Section>

      {issues.length > 0 && editableStructure && (
        <AlertBanner tone="danger">{issues[0]}</AlertBanner>
      )}

      {editableValues && (
        <OperationalActionStack>
          <SecondaryButton disabled={busy || !structureDirty || valuesDirty} icon="content-save-outline" label="Guardar estructura" loading={busy} onPress={saveStructure} />
          <SecondaryButton disabled={busy || !valuesDirty || structureDirty} icon="content-save-outline" label="Guardar valores" loading={busy} onPress={saveValues} />
        </OperationalActionStack>
      )}

    </View>
  );
}

const styles = StyleSheet.create({
  header: { alignItems: 'center', flexDirection: 'row', justifyContent: 'space-between' },
  title: { color: colors.text, fontSize: 18, fontWeight: '800' },
  meta: { color: colors.textMuted, marginBottom: spacing.md, marginTop: 2 },
  label: { color: colors.textMuted, fontSize: 12, fontWeight: '700', marginBottom: 6, marginTop: 8, textTransform: 'uppercase' },
  empty: { color: colors.textMuted, fontStyle: 'italic' },
  choiceRow: { flexDirection: 'row', gap: 8, marginBottom: 8 },
  choice: { borderColor: colors.border, borderRadius: 10, borderWidth: 1, flex: 1, padding: 10 },
  choiceActive: { backgroundColor: colors.primary, borderColor: colors.primary },
  choiceText: { color: colors.text, textAlign: 'center' },
  choiceTextActive: { color: '#fff', fontWeight: '700', textAlign: 'center' },
  tableBlock: { borderColor: colors.border, borderRadius: 10, borderWidth: 1, marginTop: 10, padding: 10 },
  columnRow: { alignItems: 'center', flexDirection: 'row', gap: 8 },
  columnField: { flex: 1 },
  removeLink: { color: '#a51c30', fontWeight: '700' },
  groupTitleReadOnly: { color: colors.text, fontSize: 14, fontWeight: '800' },
  groupOrientationReadOnly: { color: colors.textMuted, fontSize: 11, marginTop: 2, textTransform: 'uppercase' },
  tableTitleReadOnly: { color: colors.text, fontSize: 12, fontWeight: '700', marginBottom: 4 },
  valuesTable: { marginTop: 8 },
  valuesRow: { alignItems: 'center', flexDirection: 'row', gap: 6, marginBottom: 4 },
  valuesRowNumber: { color: colors.textMuted, width: 20 },
  valuesHeaderCell: { color: colors.textMuted, flex: 1, fontSize: 10, fontWeight: '700', textTransform: 'uppercase' },
  valuesCell: { flex: 1 },
  valuesCellReadOnly: { color: colors.text, flex: 1 },
});
