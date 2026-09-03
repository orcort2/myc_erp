import type {
  FieldSheetResultHeaderCell,
  FieldSheetResultSection,
} from '@/src/types/lab-work-order';

export type HeaderSegment =
  | { kind: 'cell'; cell: FieldSheetResultHeaderCell; span: number }
  | { kind: 'spacer'; span: number };

function safeSpan(value: number | undefined): number {
  return Math.max(1, Math.trunc(value ?? 1));
}

export function buildGroupedHeaderRows(
  section: FieldSheetResultSection,
): HeaderSegment[][] {
  const rows = section.header_rows ?? [];
  if (rows.length === 0) return [];

  const columnCount = section.columns.length + 1;
  const occupiedUntil = Array<number>(columnCount).fill(0);

  return rows.map((row, rowIndex) => {
    const segments: HeaderSegment[] = [];
    let columnIndex = 0;

    for (const cell of row.cells) {
      let skipped = 0;
      while (
        columnIndex < columnCount &&
        occupiedUntil[columnIndex] > rowIndex
      ) {
        skipped += 1;
        columnIndex += 1;
      }
      if (skipped > 0) {
        segments.push({ kind: 'spacer', span: skipped });
      }

      const colspan = safeSpan(cell.colspan);
      const rowspan = safeSpan(cell.rowspan);
      segments.push({ kind: 'cell', cell, span: colspan });
      for (
        let index = columnIndex;
        index < Math.min(columnIndex + colspan, columnCount);
        index += 1
      ) {
        occupiedUntil[index] = rowIndex + rowspan;
      }
      columnIndex += colspan;
    }

    let trailing = 0;
    while (columnIndex < columnCount) {
      trailing += 1;
      columnIndex += 1;
    }
    if (trailing > 0) {
      segments.push({ kind: 'spacer', span: trailing });
    }
    return segments;
  });
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
