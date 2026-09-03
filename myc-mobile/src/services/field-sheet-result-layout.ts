import type {
  FieldSheetResultHeaderCell,
  FieldSheetResultSection,
} from '@/src/types/lab-work-order';

export type HeaderCellLayout = {
  cell: FieldSheetResultHeaderCell;
  row: number;
  column: number;
  colspan: number;
  rowspan: number;
  left: number;
  top: number;
  width: number;
  height: number;
};

export type GroupedHeaderLayout = {
  columnCount: number;
  rowCount: number;
  rowHeight: number;
  totalWidth: number;
  totalHeight: number;
  cells: HeaderCellLayout[];
};

function safeSpan(value: number | undefined): number {
  return Math.max(1, Math.trunc(value ?? 1));
}

export function buildGroupedHeaderLayout(
  section: FieldSheetResultSection,
  columnWidths: number[],
  rowHeight = 32,
): GroupedHeaderLayout | null {
  const rows = section.header_rows ?? [];
  if (rows.length === 0) return null;

  const columnCount = section.columns.length + 1;
  const occupied = Array.from({ length: rows.length }, () =>
    Array<boolean>(columnCount).fill(false),
  );
  const cells: HeaderCellLayout[] = [];

  rows.forEach((row, rowIndex) => {
    let columnIndex = 0;

    for (const cell of row.cells) {
      while (
        columnIndex < columnCount &&
        occupied[rowIndex][columnIndex]
      ) {
        columnIndex += 1;
      }

      const colspan = safeSpan(cell.colspan);
      const rowspan = safeSpan(cell.rowspan);
      cells.push({
        cell,
        row: rowIndex,
        column: columnIndex,
        colspan,
        rowspan,
        left: columnWidths
          .slice(0, columnIndex)
          .reduce((total, width) => total + width, 0),
        top: rowIndex * rowHeight,
        width: columnWidths
          .slice(columnIndex, columnIndex + colspan)
          .reduce((total, width) => total + width, 0),
        height: rowspan * rowHeight,
      });
      for (let targetRow = rowIndex; targetRow < rowIndex + rowspan; targetRow += 1) {
        for (let targetColumn = columnIndex; targetColumn < columnIndex + colspan; targetColumn += 1) {
          if (occupied[targetRow]) occupied[targetRow][targetColumn] = true;
        }
      }
      columnIndex += colspan;
    }
  });

  return {
    columnCount,
    rowCount: rows.length,
    rowHeight,
    totalWidth: columnWidths.reduce((total, width) => total + width, 0),
    totalHeight: rows.length * rowHeight,
    cells,
  };
}

export function rowLabel(
  section: FieldSheetResultSection,
  rowNumber: number,
): string {
  return section.row_labels?.[rowNumber - 1] ?? String(rowNumber);
}

export function declaredWidth(
  value: string | null | undefined,
  availableWidth: number,
  fallback: number,
): number {
  if (!value || value === 'auto') return fallback;
  const match = /^(\d+(?:\.\d+)?)(mm|cm|in|pt|px|%)$/.exec(value.toLowerCase());
  if (!match) return fallback;
  const amount = Number(match[1]);
  const unit = match[2] as 'mm' | 'cm' | 'in' | 'pt' | 'px' | '%';
  if (unit === '%') return Math.max(48, (availableWidth * amount) / 100);
  const factors: Record<'mm' | 'cm' | 'in' | 'pt' | 'px', number> = {
    mm: 3.78,
    cm: 37.8,
    in: 96,
    pt: 96 / 72,
    px: 1,
  };
  const factor = factors[unit];
  return Math.max(48, amount * factor);
}
