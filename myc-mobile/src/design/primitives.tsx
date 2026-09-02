import { router } from 'expo-router';
import { useEffect, useRef, useState, type ReactNode } from 'react';
import {
  AccessibilityInfo,
  ActivityIndicator,
  Animated,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';

import { colors, radius, spacing, typography } from '@/src/design/tokens';

/**
 * Fase 6: primitives compartidos del flujo LAB/FieldSheets -- reemplazan el
 * patrón de StyleSheet ad hoc repetido por pantalla. No son obligatorios
 * fuera de esta área; sí evitan seguir duplicando el mismo botón/card/badge
 * con estilos ligeramente distintos cada vez.
 */

export function Screen({ children }: { children: ReactNode }) {
  return <View style={styles.screen}>{children}</View>;
}

/**
 * Cierre UX 2026-09: semántica de navegación consistente -- antes varias
 * pantallas etiquetaban "‹ Inicio" un botón que en realidad ejecutaba
 * router.back() (Volver, no Inicio). Back vuelve al paso anterior del
 * flujo; Inicio va explícitamente a la raíz del módulo; Cerrar cierra un
 * modal/fullscreen. No usar Inicio como sustituto de Back.
 */
export function BackButton({ onPress, label = '‹ Volver', disabled }: { onPress?(): void; label?: string; disabled?: boolean }) {
  return (
    <Pressable disabled={disabled} hitSlop={8} onPress={onPress ?? (() => router.back())} style={[styles.navAction, disabled && styles.navActionDisabled]}>
      <Text style={styles.navActionText}>{label}</Text>
    </Pressable>
  );
}

export function HomeButton({ label = 'Inicio', disabled }: { label?: string; disabled?: boolean }) {
  return (
    <Pressable disabled={disabled} hitSlop={8} onPress={() => router.replace('/(technician)')} style={[styles.navAction, disabled && styles.navActionDisabled]}>
      <Text style={styles.navActionText}>{label}</Text>
    </Pressable>
  );
}

export function CloseButton({ onPress, label = 'Cerrar', disabled }: { onPress(): void; label?: string; disabled?: boolean }) {
  return (
    <Pressable disabled={disabled} hitSlop={8} onPress={onPress} style={[styles.navAction, disabled && styles.navActionDisabled]}>
      <Text style={styles.navActionText}>{label}</Text>
    </Pressable>
  );
}

export function Section({ title, description, children }: { title?: string; description?: string; children: ReactNode }) {
  return (
    <View style={styles.section}>
      {title && <Text style={styles.sectionTitle}>{title}</Text>}
      {description && <Text style={styles.sectionDescription}>{description}</Text>}
      {children}
    </View>
  );
}

export function Card({ children }: { children: ReactNode }) {
  return <View style={styles.card}>{children}</View>;
}

export function Field({ label, value, onChange, placeholder, multiline, keyboardType }: {
  label: string;
  value: string;
  onChange(value: string): void;
  placeholder?: string;
  multiline?: boolean;
  keyboardType?: 'default' | 'numeric' | 'decimal-pad' | 'email-address' | 'phone-pad';
}) {
  return (
    <View style={styles.field}>
      <Text style={styles.label}>{label}</Text>
      <TextInput
        keyboardType={keyboardType ?? 'default'}
        multiline={multiline}
        onChangeText={onChange}
        placeholder={placeholder}
        placeholderTextColor={colors.textSubtle}
        style={[styles.input, multiline && styles.inputMultiline]}
        value={value}
      />
    </View>
  );
}

/** Datos congelados/de sólo lectura (modalidad, folio, cliente documental,
 * OT, equipo) -- se presentan como información, nunca como un input
 * deshabilitado ambiguo. */
export function ReadOnlyField({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.field}>
      <Text style={styles.label}>{label}</Text>
      <Text style={styles.readOnlyValue}>{value || '—'}</Text>
    </View>
  );
}

export function ActionRow({ children }: { children: ReactNode }) {
  return <View style={styles.actionRow}>{children}</View>;
}

type ButtonProps = { label: string; onPress(): void; disabled?: boolean; loading?: boolean };

export function PrimaryButton({ label, onPress, disabled, loading }: ButtonProps) {
  return (
    <Pressable disabled={disabled || loading} onPress={onPress} style={[styles.primaryButton, disabled && styles.buttonDisabled]}>
      {loading ? <ActivityIndicator color="#fff" /> : <Text style={styles.primaryButtonText}>{label}</Text>}
    </Pressable>
  );
}

export function SecondaryButton({ label, onPress, disabled, loading }: ButtonProps) {
  return (
    <Pressable disabled={disabled || loading} onPress={onPress} style={[styles.secondaryButton, disabled && styles.buttonDisabled]}>
      {loading ? <ActivityIndicator color={colors.primary} /> : <Text style={styles.secondaryButtonText}>{label}</Text>}
    </Pressable>
  );
}

export function DangerButton({ label, onPress, disabled, loading }: ButtonProps) {
  return (
    <Pressable disabled={disabled || loading} onPress={onPress} style={[styles.dangerButton, disabled && styles.buttonDisabled]}>
      {loading ? <ActivityIndicator color={colors.dangerStrong} /> : <Text style={styles.dangerButtonText}>{label}</Text>}
    </Pressable>
  );
}

/** Jerarquía de botones (cierre UX 2026-09): acciones administrativas
 * (reabrir, cancelar OT, restaurar) son un bucket propio -- ni la acción
 * principal del paso (Primary) ni una alternativa común (Secondary) ni
 * destructiva (Danger). Peso visual reducido a propósito. */
export function AdministrativeButton({ label, onPress, disabled, loading }: ButtonProps) {
  return (
    <Pressable disabled={disabled || loading} onPress={onPress} style={[styles.administrativeButton, disabled && styles.buttonDisabled]}>
      {loading ? <ActivityIndicator color={colors.warningStrong} /> : <Text style={styles.administrativeButtonText}>{label}</Text>}
    </Pressable>
  );
}

export type StatusTone = 'info' | 'warning' | 'success' | 'danger' | 'purple' | 'neutral';

const TONE_COLOR: Record<StatusTone, string> = {
  info: colors.info,
  warning: colors.warning,
  success: colors.success,
  danger: colors.danger,
  purple: colors.purple,
  neutral: colors.textSubtle,
};

export function StatusBadge({ label, tone = 'neutral' }: { label: string; tone?: StatusTone }) {
  const tint = TONE_COLOR[tone];
  return (
    <View style={[styles.badge, { borderColor: tint }]}>
      <Text style={[styles.badgeText, { color: tint }]}>{label}</Text>
    </View>
  );
}

export function AlertBanner({ tone = 'info', children }: { tone?: 'info' | 'warning' | 'danger' | 'success'; children: ReactNode }) {
  const tint = tone === 'danger' ? colors.danger : tone === 'warning' ? colors.warningStrong : tone === 'success' ? colors.success : colors.info;
  return (
    <View style={[styles.alert, { borderColor: tint }]}>
      <Text style={[styles.alertText, { color: tint }]}>{children}</Text>
    </View>
  );
}

export function EmptyState({ title, description }: { title: string; description?: string }) {
  return (
    <View style={styles.emptyState}>
      <Text style={styles.emptyTitle}>{title}</Text>
      {description && <Text style={styles.emptyDescription}>{description}</Text>}
    </View>
  );
}

export function LoadingState({ label }: { label?: string }) {
  return (
    <View style={styles.loadingState}>
      <ActivityIndicator color={colors.primary} />
      {label && <Text style={styles.loadingLabel}>{label}</Text>}
    </View>
  );
}

/**
 * Cierre UX 2026-09: transición suave para cambios de etapa (crear OT ->
 * equipos, equipo -> firma, firma -> captura, selector -> captura,
 * resultados -> siguiente sección, etc.) -- opacity + translateY corto,
 * ~180ms, sobre la API Animated ya usada en MobileSignatureFlow (no hay
 * Reanimated configurado en el proyecto, ver AGENTS.md de myc-mobile).
 * Respeta reduce motion; nunca bloquea la lógica de negocio -- sólo envuelve
 * la presentación, ya montada con sus datos reales. Remonta la animación
 * cuando cambia `transitionKey` (útil para re-disparar la entrada al pasar
 * de un paso a otro dentro de la misma pantalla).
 */
export function FadeIn({ children, transitionKey }: { children: ReactNode; transitionKey?: string | number }) {
  const opacity = useRef(new Animated.Value(0)).current;
  const translateY = useRef(new Animated.Value(6)).current;
  const [reduceMotion, setReduceMotion] = useState(false);

  useEffect(() => {
    let active = true;
    AccessibilityInfo.isReduceMotionEnabled?.()
      .then((value) => { if (active) setReduceMotion(value); })
      .catch(() => undefined);
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (reduceMotion) {
      opacity.setValue(1);
      translateY.setValue(0);
      return;
    }
    opacity.setValue(0);
    translateY.setValue(6);
    Animated.parallel([
      Animated.timing(opacity, { toValue: 1, duration: 180, useNativeDriver: true }),
      Animated.timing(translateY, { toValue: 0, duration: 180, useNativeDriver: true }),
    ]).start();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [transitionKey, reduceMotion]);

  return (
    <Animated.View style={{ opacity, transform: [{ translateY }] }}>
      {children}
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.background },
  section: { gap: spacing.sm, marginBottom: spacing.lg },
  sectionTitle: { ...typography.sectionTitle, color: colors.text },
  sectionDescription: { ...typography.meta, color: colors.textMuted },
  card: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderRadius: radius.lg,
    borderWidth: 1,
    gap: spacing.sm,
    padding: spacing.lg,
    marginBottom: spacing.md,
  },
  field: { gap: spacing.xs, marginBottom: spacing.sm },
  label: { ...typography.label, color: colors.textMuted },
  input: {
    backgroundColor: colors.surface,
    borderColor: colors.borderStrong,
    borderRadius: radius.md,
    borderWidth: 1,
    minHeight: 44,
    paddingHorizontal: spacing.md,
    color: colors.text,
  },
  inputMultiline: { minHeight: 90, paddingTop: spacing.sm, textAlignVertical: 'top' },
  readOnlyValue: { ...typography.body, color: colors.text, paddingVertical: spacing.xs },
  actionRow: { flexDirection: 'row', gap: spacing.sm, marginTop: spacing.md },
  primaryButton: {
    alignItems: 'center', backgroundColor: colors.primary, borderRadius: radius.md,
    paddingVertical: spacing.md, paddingHorizontal: spacing.lg, flex: 1,
  },
  primaryButtonText: { color: '#fff', fontWeight: '800' },
  secondaryButton: {
    alignItems: 'center', borderColor: colors.primary, borderRadius: radius.md, borderWidth: 1,
    paddingVertical: spacing.md, paddingHorizontal: spacing.lg, flex: 1,
  },
  secondaryButtonText: { color: colors.primary, fontWeight: '800' },
  dangerButton: {
    alignItems: 'center', borderColor: colors.danger, borderRadius: radius.md, borderWidth: 1,
    paddingVertical: spacing.md, paddingHorizontal: spacing.lg, flex: 1,
  },
  dangerButtonText: { color: colors.dangerStrong, fontWeight: '800' },
  administrativeButton: {
    alignItems: 'center', backgroundColor: 'transparent', borderColor: colors.warningStrong,
    borderRadius: radius.md, borderWidth: 1, borderStyle: 'dashed',
    paddingVertical: spacing.sm, paddingHorizontal: spacing.md,
  },
  administrativeButtonText: { color: colors.warningStrong, fontWeight: '700', fontSize: 13 },
  buttonDisabled: { opacity: 0.42 },
  navAction: { minHeight: 44, justifyContent: 'center', paddingVertical: spacing.xs },
  navActionDisabled: { opacity: 0.42 },
  navActionText: { color: colors.primary, fontWeight: '700' },
  badge: {
    alignSelf: 'flex-start', borderRadius: 999, borderWidth: 1,
    paddingHorizontal: spacing.sm, paddingVertical: 2,
  },
  badgeText: { fontSize: 12, fontWeight: '800' },
  alert: {
    borderRadius: radius.md, borderWidth: 1, padding: spacing.md, marginBottom: spacing.md,
    backgroundColor: colors.surface,
  },
  alertText: { fontSize: 14, fontWeight: '600' },
  emptyState: { alignItems: 'center', padding: spacing.xl, gap: spacing.xs },
  emptyTitle: { ...typography.sectionTitle, color: colors.text },
  emptyDescription: { ...typography.meta, color: colors.textMuted, textAlign: 'center' },
  loadingState: { alignItems: 'center', padding: spacing.xl, gap: spacing.sm },
  loadingLabel: { ...typography.meta, color: colors.textMuted },
});
