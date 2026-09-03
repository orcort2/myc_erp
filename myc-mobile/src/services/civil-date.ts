export type CivilDate = { year: number; month: number; day: number };

export function daysInMonth(year: number, month: number): number {
  if (month === 2) {
    const leap = year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
    return leap ? 29 : 28;
  }
  return [4, 6, 9, 11].includes(month) ? 30 : 31;
}

export function parseCivilDate(value: string): CivilDate | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (!match) return null;
  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  if (month < 1 || month > 12 || day < 1 || day > daysInMonth(year, month)) return null;
  return { year, month, day };
}

export function formatCivilDate(date: CivilDate): string {
  return `${String(date.year).padStart(4, '0')}-${String(date.month).padStart(2, '0')}-${String(date.day).padStart(2, '0')}`;
}

export function addCivilMonths(value: string, months: number): string | null {
  const date = parseCivilDate(value);
  if (!date) return null;
  const zeroBased = date.year * 12 + date.month - 1 + months;
  const year = Math.floor(zeroBased / 12);
  const month = ((zeroBased % 12) + 12) % 12 + 1;
  return formatCivilDate({ year, month, day: Math.min(date.day, daysInMonth(year, month)) });
}

export function todayCivilDate(now = new Date()): string {
  return formatCivilDate({
    year: now.getFullYear(),
    month: now.getMonth() + 1,
    day: now.getDate(),
  });
}

export function calendarDays(year: number, month: number): (string | null)[] {
  const firstWeekday = new Date(Date.UTC(year, month - 1, 1)).getUTCDay();
  const cells: (string | null)[] = Array.from({ length: firstWeekday }, () => null);
  for (let day = 1; day <= daysInMonth(year, month); day += 1) {
    cells.push(formatCivilDate({ year, month, day }));
  }
  while (cells.length % 7 !== 0) cells.push(null);
  return cells;
}
