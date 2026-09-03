import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

const source = readFileSync(
  resolve(dirname(fileURLToPath(import.meta.url)), './MycDatePickerField.tsx'),
  'utf8',
);

test('MycDatePickerField abre un modal y presenta calendario de siete columnas', () => {
  assert.match(source, /<Modal[\s\S]*?visible=\{open\}/);
  assert.match(source, /const WEEKDAYS = \['D', 'L', 'M', 'M', 'J', 'V', 'S'\]/);
  assert.match(source, /width: '14\.2857%'/);
  assert.match(source, /const selected = date === value/);
  assert.match(source, /const isToday = date === today/);
});

test('el field visible conserva AAAA-MM-DD y no abre teclado', () => {
  assert.match(source, /placeholder = 'AAAA-MM-DD'/);
  assert.match(source, /<Pressable[\s\S]*onPress=\{\(\) => setOpen\(true\)\}/);
  assert.doesNotMatch(source, /<TextInput/);
});

test('los shortcuts +6 meses y +1 año usan exclusivamente shortcutBaseValue', () => {
  assert.match(source, /applyShortcut\(6\)/);
  assert.match(source, /applyShortcut\(12\)/);
  assert.match(source, /addCivilMonths\(shortcutBaseValue, months\)/);
  assert.doesNotMatch(source, /addCivilMonths\(today/);
  assert.match(source, /Selecciona primero la fecha de calibración/);
});
