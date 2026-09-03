import assert from 'node:assert/strict';
import test from 'node:test';

import { addCivilMonths, calendarDays, parseCivilDate, todayCivilDate } from './civil-date';

test('parseCivilDate acepta sólo fechas civiles YYYY-MM-DD válidas', () => {
  assert.deepEqual(parseCivilDate('2024-02-29'), { year: 2024, month: 2, day: 29 });
  assert.equal(parseCivilDate('2023-02-29'), null);
  assert.equal(parseCivilDate('2026-2-03'), null);
});

test('+6 meses clampa el fin de mes sin desbordar a marzo', () => {
  assert.equal(addCivilMonths('2025-08-31', 6), '2026-02-28');
  assert.equal(addCivilMonths('2023-08-31', 6), '2024-02-29');
});

test('+1 año clampa el 29 de febrero al último día válido', () => {
  assert.equal(addCivilMonths('2024-02-29', 12), '2025-02-28');
  assert.equal(addCivilMonths('2024-02-29', 48), '2028-02-29');
});

test('todayCivilDate usa componentes locales y calendarDays conserva semanas completas', () => {
  const local = new Date(2026, 8, 3, 23, 30);
  assert.equal(todayCivilDate(local), '2026-09-03');
  assert.equal(calendarDays(2026, 9).length % 7, 0);
  assert.ok(calendarDays(2026, 9).includes('2026-09-30'));
});
