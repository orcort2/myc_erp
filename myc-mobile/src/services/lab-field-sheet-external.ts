/**
 * PENDIENTE 7 (encargo de corrección LAB): "LAB EXTERNO" -- lógica pura del
 * lado mobile para el equipo service_type=linked. Espejo exacto de
 * app/schemas/lab_field_sheet_external.py (mismos límites, misma forma) --
 * backend sigue siendo la única autoridad de validación real; esto sólo
 * evita mandar una estructura obviamente inválida y da feedback inmediato.
 */

export type LabExternalOrientation = 'pattern_to_ibc' | 'ibc_to_pattern';

export type LabExternalColumn = {
  key: string;
  label: string;
};

export type LabExternalTable = {
  id: string;
  title: string;
  columns: LabExternalColumn[];
  row_count: number;
};

export type LabExternalGroup = {
  id: string;
  title: string;
  orientation: LabExternalOrientation;
  tables: LabExternalTable[];
};

export type LabExternalDefinition = {
  kind: 'lab_externo';
  groups: LabExternalGroup[];
};

export type LabExternalStructurePayload = {
  groups: LabExternalGroup[];
};

export const LAB_EXTERNAL_TEMPLATE_KEY = 'lab_externo';

export const MAX_LAB_EXTERNAL_GROUPS = 20;
export const MAX_LAB_EXTERNAL_TABLES_PER_GROUP = 20;
export const MAX_LAB_EXTERNAL_COLUMNS_PER_TABLE = 30;
export const MAX_LAB_EXTERNAL_ROWS_PER_TABLE = 200;

export const ORIENTATION_LABELS: Record<LabExternalOrientation, string> = {
  pattern_to_ibc: 'Patrón → IBC',
  ibc_to_pattern: 'IBC → Patrón',
};

/** Un equipo service_type=linked siempre usa LAB EXTERNO -- nunca se ofrece
 * ni se pide elegir una plantilla LAB interna (sección "INTEGRACIÓN
 * LINKED" del encargo). */
export function isLabExternalEquipment(equipment: { service_type: string | null }): boolean {
  return equipment.service_type === 'linked';
}

function slugify(value: string): string {
  return value
    .toLowerCase()
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '')
    || 'x';
}

/** Genera un id corto, único dentro de `existingIds`, a partir de un texto
 * legible (título del grupo/tabla) -- nunca requiere que el técnico invente
 * un identificador técnico él mismo. */
export function generateUniqueId(base: string, existingIds: string[]): string {
  const slug = slugify(base);
  if (!existingIds.includes(slug)) return slug;
  let suffix = 2;
  while (existingIds.includes(`${slug}_${suffix}`)) suffix += 1;
  return `${slug}_${suffix}`;
}

export function emptyColumn(existing: LabExternalColumn[]): LabExternalColumn {
  const index = existing.length + 1;
  return { key: generateUniqueId(`col_${index}`, existing.map((item) => item.key)), label: `Columna ${index}` };
}

export function emptyTable(existingIds: string[], index: number): LabExternalTable {
  return {
    id: generateUniqueId(`tabla_${index}`, existingIds),
    title: `Tabla ${index}`,
    columns: [{ key: 'c1', label: 'Columna 1' }],
    row_count: 1,
  };
}

export function emptyGroup(existingIds: string[], index: number): LabExternalGroup {
  const groupId = generateUniqueId(`grupo_${index}`, existingIds);
  return {
    id: groupId,
    title: `Grupo ${index}`,
    orientation: 'pattern_to_ibc',
    tables: [emptyTable([], 1)],
  };
}

export type LabExternalStructureIssue = string;

/** Mismas reglas que LabExternalStructureWrite en backend (ids únicos,
 * al menos una columna/tabla) -- feedback inmediato en mobile; backend
 * sigue siendo quien realmente lo exige. */
export function validateLabExternalStructure(groups: LabExternalGroup[]): LabExternalStructureIssue[] {
  const issues: LabExternalStructureIssue[] = [];
  const groupIds = groups.map((group) => group.id);
  if (new Set(groupIds).size !== groupIds.length) {
    issues.push('Hay grupos con el mismo id -- deben ser únicos.');
  }
  const tableIds = groups.flatMap((group) => group.tables.map((table) => table.id));
  if (new Set(tableIds).size !== tableIds.length) {
    issues.push('Hay tablas con el mismo id en toda la hoja -- deben ser únicos.');
  }
  for (const group of groups) {
    if (!group.tables.length) {
      issues.push(`El grupo "${group.title}" necesita al menos una tabla.`);
    }
    for (const table of group.tables) {
      if (!table.columns.length) {
        issues.push(`La tabla "${table.title}" necesita al menos una columna.`);
      }
      const columnKeys = table.columns.map((column) => column.key);
      if (new Set(columnKeys).size !== columnKeys.length) {
        issues.push(`La tabla "${table.title}" tiene columnas repetidas.`);
      }
      if (table.row_count < 1) {
        issues.push(`La tabla "${table.title}" necesita al menos una fila.`);
      }
    }
  }
  return issues;
}

export function buildLabExternalStructurePayload(groups: LabExternalGroup[]): LabExternalStructurePayload {
  return { groups };
}

/** Extrae la definición LAB EXTERNO de un FieldSheetRead -- backend nunca
 * manda blocks/result_sections aquí (bootstrap_lab_external_definition en
 * lab_field_sheets_external.py), así que esto SIEMPRE trae groups, nunca el
 * shape de una plantilla institucional canónica. */
export function readLabExternalDefinition(templateDefinition: unknown): LabExternalDefinition {
  const raw = (templateDefinition ?? {}) as Partial<LabExternalDefinition>;
  return { kind: 'lab_externo', groups: raw.groups ?? [] };
}

export type LabExternalRow = {
  id?: number;
  section_key: string;
  row_number: number;
  row_data: Record<string, string>;
};

/** Localiza la fila (section_key=table.id, row_number) capturada para una
 * celda -- las filas ya existen (creadas por apply_lab_external_structure
 * al guardar la estructura); esto nunca crea una fila nueva del lado
 * mobile. */
export function findRow(rows: LabExternalRow[], tableId: string, rowNumber: number): LabExternalRow | undefined {
  return rows.find((row) => row.section_key === tableId && row.row_number === rowNumber);
}

export function cellValue(rows: LabExternalRow[], tableId: string, rowNumber: number, columnKey: string): string {
  const row = findRow(rows, tableId, rowNumber);
  const value = row?.row_data?.[columnKey];
  return value == null ? '' : String(value);
}

/** Construye el body exacto del PATCH .../field-sheet ya existente --
 * ningún endpoint nuevo para capturar valores, sólo results_rows con
 * row_data por columna dinámica (mismo contrato que cualquier otra
 * plantilla, ver FieldSheetResultUpdate en backend). */
export function buildLabExternalValuesPatch(rows: LabExternalRow[]): { results_rows: LabExternalRow[] } {
  return { results_rows: rows };
}

/** Misma semántica de progreso que backend: filas declaradas con al menos
 * una columna declarada no vacía; celdas ajenas a la tabla no cuentan. */
export function labExternalTableProgress(table: LabExternalTable, rows: LabExternalRow[]): { completed: number; total: number } {
  let completed = 0;
  for (let row = 1; row <= table.row_count; row += 1) {
    if (table.columns.some((column) => cellValue(rows, table.id, row, column.key).trim() !== '')) completed += 1;
  }
  return { completed, total: table.row_count };
}
