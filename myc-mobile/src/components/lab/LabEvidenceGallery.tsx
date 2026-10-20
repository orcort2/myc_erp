import { Image } from 'expo-image';
import { useEffect, useRef, useState } from 'react';
import { Alert, Modal, Pressable, ScrollView, StyleSheet, Text, useWindowDimensions, View } from 'react-native';

import { colors, spacing } from '@/src/design/tokens';
import { EVIDENCE_TYPE_LABELS } from '@/src/services/technical-report-installation';
import {
  gridColumns,
  indexAfterDelete,
  neighborIndex,
  pageIndexFromOffset,
  planEvidenceGrid,
} from '@/src/services/technical-report-gallery';
import type { TechnicalReportEvidence } from '@/src/types/technical-report';

type Props = {
  /** Sólo la evidencia de ESTA categoría, ordenada por posición. */
  items: TechnicalReportEvidence[];
  canAdd: boolean;
  /** Sólo con el reporte editable: la eliminación vive en el visor. */
  canDelete: boolean;
  busy: boolean;
  addLabel: string;
  imageSource(evidenceId: number): { uri: string; headers: Record<string, string> };
  onAdd(): void;
  /** Resuelve cuando la baja terminó (o lanza). */
  onDelete(item: TechnicalReportEvidence): Promise<void>;
};

/**
 * Grid compacto de miniaturas de UNA categoría de evidencia + visor a pantalla
 * completa con swipe. El visor nunca mezcla categorías: before/during/
 * incident/after determinan después la composición del PDF.
 */
export function LabEvidenceGallery({ addLabel, busy, canAdd, canDelete, imageSource, items, onAdd, onDelete }: Props) {
  const { width: windowWidth } = useWindowDimensions();
  const columns = gridColumns(windowWidth);
  const plan = planEvidenceGrid({ columns, count: items.length, canAdd });
  const [viewerIndex, setViewerIndex] = useState<number | null>(null);
  const cellStyle = columns === 3 ? styles.cellThree : styles.cellTwo;
  const typeLabel = items[0] ? EVIDENCE_TYPE_LABELS[items[0].evidence_type] : '';

  return (
    <View style={styles.gallery}>
      <View style={styles.grid}>
        {items.slice(0, plan.visiblePhotos).map((item, index) => (
          <Pressable
            accessibilityLabel={`Abrir foto ${EVIDENCE_TYPE_LABELS[item.evidence_type]} ${item.position}`}
            accessibilityRole="imagebutton"
            key={item.id}
            onPress={() => setViewerIndex(index)}
            style={[styles.cell, cellStyle]}
          >
            <Image
              accessibilityLabel={`Foto ${EVIDENCE_TYPE_LABELS[item.evidence_type]} ${item.position}`}
              cachePolicy="memory-disk"
              contentFit="cover"
              source={imageSource(item.id)}
              style={styles.thumb}
            />
          </Pressable>
        ))}
        {plan.overflow > 0 && (
          <Pressable
            accessibilityLabel={`Ver ${items.length} fotos`}
            accessibilityRole="button"
            onPress={() => setViewerIndex(plan.visiblePhotos)}
            style={[styles.cell, styles.moreCell, cellStyle]}
          >
            <Text style={styles.moreText}>+{plan.overflow}</Text>
          </Pressable>
        )}
        {plan.addCell && (
          <Pressable
            accessibilityLabel={addLabel}
            accessibilityRole="button"
            disabled={busy}
            onPress={onAdd}
            style={[styles.cell, styles.addCell, cellStyle]}
          >
            <Text style={styles.addPlus}>+</Text>
            <Text style={styles.addText}>Agregar</Text>
          </Pressable>
        )}
      </View>
      {plan.addButton && (
        <Pressable accessibilityLabel={addLabel} accessibilityRole="button" disabled={busy} onPress={onAdd} style={styles.addInline}>
          <Text style={styles.addInlineText}>+ Agregar foto</Text>
        </Pressable>
      )}
      {items.length > 0 && <Text style={styles.count}>{items.length} {items.length === 1 ? 'evidencia' : 'evidencias'}</Text>}

      {viewerIndex !== null && items.length > 0 && (
        <EvidenceViewer
          busy={busy}
          canDelete={canDelete}
          imageSource={imageSource}
          initialIndex={Math.min(viewerIndex, items.length - 1)}
          items={items}
          onClose={() => setViewerIndex(null)}
          onDelete={onDelete}
          typeLabel={typeLabel}
        />
      )}
    </View>
  );
}

function EvidenceViewer({
  busy,
  canDelete,
  imageSource,
  initialIndex,
  items,
  onClose,
  onDelete,
  typeLabel,
}: {
  busy: boolean;
  canDelete: boolean;
  imageSource: Props['imageSource'];
  initialIndex: number;
  items: TechnicalReportEvidence[];
  onClose(): void;
  onDelete(item: TechnicalReportEvidence): Promise<void>;
  typeLabel: string;
}) {
  const { width } = useWindowDimensions();
  const [index, setIndex] = useState(initialIndex);
  const pager = useRef<{ scrollTo(options: { x: number; y: number; animated: boolean }): void } | null>(null);
  const current = items[Math.min(index, items.length - 1)];

  function goTo(next: number) {
    setIndex(next);
    pager.current?.scrollTo({ x: next * width, y: 0, animated: true });
  }

  // Posición inicial (y tras borrar): el pager se alinea con el índice vigente.
  useEffect(() => {
    pager.current?.scrollTo({ x: Math.min(index, items.length - 1) * width, y: 0, animated: false });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [items.length, width]);

  function confirmDelete() {
    const removedIndex = index;
    Alert.alert('¿Eliminar esta evidencia?', 'La fotografía se quitará del reporte.', [
      { text: 'Cancelar', style: 'cancel' },
      {
        text: 'Eliminar',
        style: 'destructive',
        onPress: () => {
          onDelete(current)
            .then(() => {
              const next = indexAfterDelete(removedIndex, items.length - 1);
              if (next === null) onClose();
              else setIndex(next);
            })
            .catch(() => undefined);
        },
      },
    ]);
  }

  return (
    <Modal animationType="fade" onRequestClose={onClose} transparent visible>
      <View style={styles.viewer}>
        <ScrollView
          horizontal
          onMomentumScrollEnd={(event) => setIndex(pageIndexFromOffset(event.nativeEvent.contentOffset.x, width, items.length))}
          pagingEnabled
          ref={pager as never}
          showsHorizontalScrollIndicator={false}
          style={styles.pager}
        >
          {items.map((item) => (
            <View key={item.id} style={[styles.page, { width }]}>
              <Image
                accessibilityLabel={`Foto ampliada ${EVIDENCE_TYPE_LABELS[item.evidence_type]} ${item.position}`}
                cachePolicy="memory-disk"
                contentFit="contain"
                source={imageSource(item.id)}
                style={styles.photo}
              />
            </View>
          ))}
        </ScrollView>

        <View style={styles.glass}>
          <View style={styles.glassRow}>
            <Pressable
              accessibilityLabel="Foto anterior"
              accessibilityRole="button"
              disabled={index === 0}
              hitSlop={8}
              onPress={() => goTo(neighborIndex(index, -1, items.length))}
              style={[styles.nav, index === 0 && styles.navDisabled]}
            >
              <Text style={styles.navText}>‹</Text>
            </Pressable>
            <Text accessibilityLabel={`Foto ${index + 1} de ${items.length}`} style={styles.position}>
              {index + 1} de {items.length} · {typeLabel}
            </Text>
            <Pressable
              accessibilityLabel="Foto siguiente"
              accessibilityRole="button"
              disabled={index >= items.length - 1}
              hitSlop={8}
              onPress={() => goTo(neighborIndex(index, 1, items.length))}
              style={[styles.nav, index >= items.length - 1 && styles.navDisabled]}
            >
              <Text style={styles.navText}>›</Text>
            </Pressable>
          </View>
          <View style={styles.glassRow}>
            <Pressable accessibilityLabel="Cerrar visor" accessibilityRole="button" hitSlop={8} onPress={onClose}>
              <Text style={styles.action}>Cerrar</Text>
            </Pressable>
            {canDelete && (
              <Pressable accessibilityLabel="Eliminar evidencia" accessibilityRole="button" disabled={busy} hitSlop={8} onPress={confirmDelete}>
                <Text style={styles.danger}>Eliminar</Text>
              </Pressable>
            )}
          </View>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  action: { color: '#ffffff', fontWeight: '700' },
  addCell: { alignItems: 'center', backgroundColor: colors.primarySoft, borderColor: colors.primary, borderStyle: 'dashed', justifyContent: 'center' },
  addInline: { alignSelf: 'flex-start', paddingVertical: spacing.xs },
  addInlineText: { color: colors.primary, fontWeight: '700' },
  addPlus: { color: colors.primary, fontSize: 26, fontWeight: '600' },
  addText: { color: colors.primary, fontSize: 12, fontWeight: '700' },
  cell: { aspectRatio: 1, borderColor: colors.border, borderRadius: 9, borderWidth: 1, overflow: 'hidden' },
  // Tres o dos columnas repartiendo el ancho disponible: sin tamaños fijos.
  cellThree: { width: '31.5%' },
  cellTwo: { width: '48.5%' },
  count: { color: colors.textSubtle, fontSize: 12 },
  danger: { color: '#ff8a80', fontWeight: '800' },
  gallery: { gap: spacing.xs },
  glass: {
    backgroundColor: 'rgba(20, 43, 58, 0.62)',
    borderRadius: 14,
    bottom: spacing.xl,
    gap: spacing.sm,
    left: spacing.lg,
    padding: spacing.md,
    position: 'absolute',
    right: spacing.lg,
  },
  glassRow: { alignItems: 'center', flexDirection: 'row', justifyContent: 'space-between' },
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm },
  moreCell: { alignItems: 'center', backgroundColor: colors.text, justifyContent: 'center' },
  moreText: { color: '#ffffff', fontSize: 22, fontWeight: '800' },
  nav: { alignItems: 'center', height: 36, justifyContent: 'center', width: 36 },
  navDisabled: { opacity: 0.35 },
  navText: { color: '#ffffff', fontSize: 28, fontWeight: '600' },
  page: { alignItems: 'center', justifyContent: 'center' },
  pager: { flex: 1 },
  photo: { height: '100%', width: '100%' },
  position: { color: '#ffffff', fontWeight: '700' },
  thumb: { height: '100%', width: '100%' },
  viewer: { backgroundColor: 'rgba(0, 0, 0, 0.92)', flex: 1 },
});
