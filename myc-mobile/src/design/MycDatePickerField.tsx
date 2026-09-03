import { useMemo, useState } from 'react';
import { Modal, Pressable, StyleSheet, Text, View } from 'react-native';

import { colors, radius, spacing } from '@/src/design/tokens';
import {
  addCivilMonths,
  calendarDays,
  formatCivilDate,
  parseCivilDate,
  todayCivilDate,
} from '@/src/services/civil-date';

const MONTHS = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'];
const WEEKDAYS = ['D', 'L', 'M', 'M', 'J', 'V', 'S'];

type Props = {
  label: string;
  value: string;
  onChange(value: string): void;
  placeholder?: string;
  disabled?: boolean;
  error?: string;
  hint?: string;
  shortcutBaseValue?: string;
};

export function MycDatePickerField({
  label,
  value,
  onChange,
  placeholder = 'AAAA-MM-DD',
  disabled,
  error,
  hint,
  shortcutBaseValue,
}: Props) {
  const initial = parseCivilDate(value) ?? parseCivilDate(todayCivilDate())!;
  const [open, setOpen] = useState(false);
  const [visibleMonth, setVisibleMonth] = useState({ year: initial.year, month: initial.month });
  const cells = useMemo(
    () => calendarDays(visibleMonth.year, visibleMonth.month),
    [visibleMonth],
  );
  const today = todayCivilDate();
  const shortcutEnabled = shortcutBaseValue == null || parseCivilDate(shortcutBaseValue) !== null;

  function moveMonth(delta: number) {
    const next = addCivilMonths(formatCivilDate({ ...visibleMonth, day: 1 }), delta);
    const parsed = next ? parseCivilDate(next) : null;
    if (parsed) setVisibleMonth({ year: parsed.year, month: parsed.month });
  }

  function applyShortcut(months: number) {
    if (!shortcutBaseValue) return;
    const next = addCivilMonths(shortcutBaseValue, months);
    if (next) onChange(next);
  }

  return (
    <View style={styles.field}>
      <Text style={styles.label}>{label}</Text>
      <Pressable
        accessibilityRole="button"
        disabled={disabled}
        onPress={() => setOpen(true)}
        style={[styles.input, !!error && styles.inputError, disabled && styles.disabled]}
      >
        <Text style={value ? styles.value : styles.placeholder}>{value || placeholder}</Text>
        <Text style={styles.icon}>▣</Text>
      </Pressable>
      {shortcutBaseValue !== undefined && (
        <View style={styles.shortcuts}>
          <Pressable disabled={!shortcutEnabled} onPress={() => applyShortcut(6)} style={styles.shortcut}><Text style={styles.shortcutText}>+6 meses</Text></Pressable>
          <Pressable disabled={!shortcutEnabled} onPress={() => applyShortcut(12)} style={styles.shortcut}><Text style={styles.shortcutText}>+1 año</Text></Pressable>
        </View>
      )}
      {!!error && <Text style={styles.error}>{error}</Text>}
      {!error && !!hint && <Text style={styles.hint}>{hint}</Text>}
      {shortcutBaseValue !== undefined && !shortcutEnabled && !error && (
        <Text style={styles.hint}>Selecciona primero la fecha de calibración.</Text>
      )}

      <Modal animationType="fade" onRequestClose={() => setOpen(false)} transparent visible={open}>
        <View style={styles.backdrop}>
          <View style={styles.calendar}>
            <View style={styles.header}>
              <Pressable onPress={() => moveMonth(-1)} style={styles.nav}><Text style={styles.navText}>‹</Text></Pressable>
              <Text style={styles.month}>{MONTHS[visibleMonth.month - 1]} {visibleMonth.year}</Text>
              <Pressable onPress={() => moveMonth(1)} style={styles.nav}><Text style={styles.navText}>›</Text></Pressable>
            </View>
            <View style={styles.grid}>
              {WEEKDAYS.map((day, index) => <Text key={`${day}-${index}`} style={styles.weekday}>{day}</Text>)}
              {cells.map((date, index) => {
                const selected = date === value;
                const isToday = date === today;
                return date ? (
                  <Pressable
                    key={date}
                    onPress={() => { onChange(date); setOpen(false); }}
                    style={[styles.day, isToday && styles.today, selected && styles.selected]}
                  >
                    <Text style={[styles.dayText, selected && styles.selectedText]}>{Number(date.slice(-2))}</Text>
                  </Pressable>
                ) : <View key={`empty-${index}`} style={styles.day} />;
              })}
            </View>
            <Pressable onPress={() => setOpen(false)} style={styles.close}><Text style={styles.closeText}>Cerrar</Text></Pressable>
          </View>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  field: { gap: spacing.xs, marginBottom: spacing.sm },
  label: { color: colors.textMuted, fontSize: 12, fontWeight: '700' },
  input: { alignItems: 'center', backgroundColor: colors.surface, borderColor: colors.borderStrong, borderRadius: radius.md, borderWidth: 1, flexDirection: 'row', justifyContent: 'space-between', minHeight: 44, paddingHorizontal: spacing.md },
  inputError: { borderColor: colors.danger },
  disabled: { opacity: 0.5 },
  value: { color: colors.text },
  placeholder: { color: colors.textSubtle },
  icon: { color: colors.accent, fontSize: 18 },
  shortcuts: { flexDirection: 'row', gap: spacing.sm },
  shortcut: { paddingHorizontal: spacing.sm, paddingVertical: spacing.xs },
  shortcutText: { color: colors.accent, fontSize: 12, fontWeight: '700' },
  error: { color: colors.danger, fontSize: 12, fontWeight: '600' },
  hint: { color: colors.textSubtle, fontSize: 12 },
  backdrop: { alignItems: 'center', backgroundColor: 'rgba(0,0,0,0.42)', flex: 1, justifyContent: 'center', padding: spacing.lg },
  calendar: { backgroundColor: colors.surface, borderRadius: radius.lg, maxWidth: 380, padding: spacing.lg, width: '100%' },
  header: { alignItems: 'center', flexDirection: 'row', justifyContent: 'space-between', marginBottom: spacing.md },
  nav: { alignItems: 'center', height: 40, justifyContent: 'center', width: 40 },
  navText: { color: colors.accent, fontSize: 30 },
  month: { color: colors.text, fontSize: 17, fontWeight: '800' },
  grid: { flexDirection: 'row', flexWrap: 'wrap' },
  weekday: { color: colors.textMuted, fontSize: 12, fontWeight: '800', textAlign: 'center', width: '14.2857%' },
  day: { alignItems: 'center', aspectRatio: 1, borderRadius: 999, justifyContent: 'center', marginVertical: 2, width: '14.2857%' },
  today: { borderColor: colors.accent, borderWidth: 1 },
  selected: { backgroundColor: colors.primary },
  dayText: { color: colors.text },
  selectedText: { color: '#fff', fontWeight: '800' },
  close: { alignSelf: 'flex-end', marginTop: spacing.md, padding: spacing.sm },
  closeText: { color: colors.accent, fontWeight: '700' },
});
