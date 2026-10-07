/**
 * Layout de la evidencia fotográfica (SG-4C.2-4): matemática pura del grid de
 * miniaturas y de la navegación del visor, sin React, para poder probarla.
 */

/** Ancho de ventana a partir del cual caben 3 columnas legibles. iPhone SE /
 * mini (< 360 pt de ancho útil) usan 2. No son dimensiones de celda: las
 * celdas se reparten el ancho disponible. */
export const THREE_COLUMN_MIN_WIDTH = 360;

/** Filas visibles del grid antes de compactar (4C.4). */
export const GRID_VISIBLE_ROWS = 2;

export function gridColumns(windowWidth: number): 2 | 3 {
  return windowWidth >= THREE_COLUMN_MIN_WIDTH ? 3 : 2;
}

export type EvidenceGridPlan = {
  /** Cuántas miniaturas se muestran (las primeras por posición). */
  visiblePhotos: number;
  /** > 0: la última celda es "+N" y abre el visor con la colección completa. */
  overflow: number;
  /** Celda "+ Agregar" dentro del grid. */
  addCell: boolean;
  /** Con overflow no cabe la celda "+": se ofrece un botón debajo del grid. */
  addButton: boolean;
};

/** La autoridad es la colección completa del backend; esto sólo decide
 * cuántas previews caben sin convertir el grid en otro formulario gigante. */
export function planEvidenceGrid(input: { count: number; canAdd: boolean; columns: 2 | 3 }): EvidenceGridPlan {
  const capacity = input.columns * GRID_VISIBLE_ROWS;
  if (input.count + (input.canAdd ? 1 : 0) <= capacity) {
    return { visiblePhotos: input.count, overflow: 0, addCell: input.canAdd, addButton: false };
  }
  const visiblePhotos = capacity - 1;
  return { visiblePhotos, overflow: input.count - visiblePhotos, addCell: false, addButton: input.canAdd };
}

/** Índice vecino dentro de una categoría, sin dar la vuelta. */
export function neighborIndex(index: number, delta: -1 | 1, count: number): number {
  return Math.min(Math.max(index + delta, 0), Math.max(count - 1, 0));
}

/** Índice a mostrar tras borrar `removedIndex` de una colección de `remainingCount`
 * elementos restantes; null = ya no queda nada y el visor se cierra. */
export function indexAfterDelete(removedIndex: number, remainingCount: number): number | null {
  if (remainingCount <= 0) return null;
  return Math.min(removedIndex, remainingCount - 1);
}

export function pageIndexFromOffset(offsetX: number, pageWidth: number, count: number): number {
  if (pageWidth <= 0) return 0;
  return Math.min(Math.max(Math.round(offsetX / pageWidth), 0), Math.max(count - 1, 0));
}
