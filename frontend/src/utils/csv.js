export function toCsvValue(value) {
  const text = String(value ?? '');
  return `"${text.replace(/"/g, '""')}"`;
}

export function downloadCsv(filename, columns, rows = []) {
  const content = [
    columns.map(toCsvValue).join(','),
    ...rows.map((row) => columns.map((column) => toCsvValue(row[column])).join(','))
  ].join('\n');
  const blob = new Blob([`\ufeff${content}`], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

export function parseDelimitedText(text) {
  const lines = text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);

  if (!lines.length) {
    return { columns: [], rows: [] };
  }

  const separator = lines[0].includes('\t') ? '\t' : ',';
  const columns = lines[0].split(separator).map((column) => column.replace(/^"|"$/g, '').trim());
  const rows = lines.slice(1).map((line) => {
    const values = line.split(separator).map((value) => value.replace(/^"|"$/g, '').trim());
    return Object.fromEntries(columns.map((column, index) => [column, values[index] ?? '']));
  });

  return { columns, rows };
}

