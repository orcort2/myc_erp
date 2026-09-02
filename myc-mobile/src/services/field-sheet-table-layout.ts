/**
 * Fase 6: cálculo de layout de tabla reactivo a dimensiones (consumido con
 * useWindowDimensions() en el workspace) -- portrait usa scroll horizontal
 * cuando no caben las columnas, landscape aprovecha el ancho completo,
 * rotación recalcula sin perder datos (esto es puro cálculo, el estado de
 * filas vive aparte en field-sheet-results-workspace-state). No se fuerza
 * landscape ni se bloquea portrait (app.json ya usa orientation: default).
 */
export type Orientation = 'portrait' | 'landscape';

export function orientationForDimensions(width: number, height: number): Orientation {
  return width >= height ? 'landscape' : 'portrait';
}

export type TableLayout = {
  columnWidth: number;
  totalWidth: number;
  needsHorizontalScroll: boolean;
};

const DEFAULT_MIN_COLUMN_WIDTH = 96;
const DEFAULT_ROW_NUMBER_WIDTH = 32;

export function computeTableLayout(
  availableWidth: number,
  columnCount: number,
  options?: { minColumnWidth?: number; rowNumberWidth?: number },
): TableLayout {
  const minColumnWidth = options?.minColumnWidth ?? DEFAULT_MIN_COLUMN_WIDTH;
  const rowNumberWidth = options?.rowNumberWidth ?? DEFAULT_ROW_NUMBER_WIDTH;
  if (columnCount <= 0) {
    return { columnWidth: 0, totalWidth: rowNumberWidth, needsHorizontalScroll: false };
  }
  const usableWidth = Math.max(availableWidth - rowNumberWidth, 0);
  const evenWidth = usableWidth / columnCount;
  // Nunca se comprime bajo el mínimo legible -- si no caben todas las
  // columnas al mínimo, el total excede el ancho disponible y el caller
  // activa scroll horizontal (needsHorizontalScroll), no letra diminuta.
  const columnWidth = Math.max(evenWidth, minColumnWidth);
  const totalWidth = rowNumberWidth + columnWidth * columnCount;
  return {
    columnWidth,
    totalWidth,
    needsHorizontalScroll: totalWidth > availableWidth,
  };
}
