import { MaterialCommunityIcons } from '@expo/vector-icons';
import { router } from 'expo-router';
import {
  useEffect,
  useRef,
  useState,
  type ComponentProps,
  type ReactNode,
} from 'react';
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
 * Primitives compartidos del flujo LAB/FieldSheets.
 *
 * Regla visual:
 * - ActionTile: acciones launcher / entrada a un proceso.
 * - PrimaryButton: confirmar la acción principal de un formulario/paso.
 * - SecondaryButton: acción auxiliar.
 * - AdministrativeButton: operación administrativa excepcional.
 * - DangerButton: operación destructiva.
 */

export function Screen({ children }: { children: ReactNode }) {
  return <View style={styles.screen}>{children}</View>;
}

export function BackButton({
  onPress,
  label = '‹ Volver',
  disabled,
}: {
  onPress?(): void;
  label?: string;
  disabled?: boolean;
}) {
  return (
    <Pressable
      disabled={disabled}
      hitSlop={8}
      onPress={onPress ?? (() => router.back())}
      style={[styles.navAction, disabled && styles.navActionDisabled]}
    >
      <Text style={styles.navActionText}>{label}</Text>
    </Pressable>
  );
}

export function HomeButton({
  label = 'Inicio',
  disabled,
}: {
  label?: string;
  disabled?: boolean;
}) {
  return (
    <Pressable
      disabled={disabled}
      hitSlop={8}
      onPress={() => router.replace('/(technician)')}
      style={[styles.navAction, disabled && styles.navActionDisabled]}
    >
      <Text style={styles.navActionText}>{label}</Text>
    </Pressable>
  );
}

export function CloseButton({
  onPress,
  label = 'Cerrar',
  disabled,
}: {
  onPress(): void;
  label?: string;
  disabled?: boolean;
}) {
  return (
    <Pressable
      disabled={disabled}
      hitSlop={8}
      onPress={onPress}
      style={[styles.navAction, disabled && styles.navActionDisabled]}
    >
      <Text style={styles.navActionText}>{label}</Text>
    </Pressable>
  );
}

export function Section({
  title,
  description,
  children,
}: {
  title?: string;
  description?: string;
  children: ReactNode;
}) {
  return (
    <View style={styles.section}>
      {title && <Text style={styles.sectionTitle}>{title}</Text>}
      {description && (
        <Text style={styles.sectionDescription}>{description}</Text>
      )}
      {children}
    </View>
  );
}

export function Card({ children }: { children: ReactNode }) {
  return <View style={styles.card}>{children}</View>;
}

export function Field({
  label,
  value,
  onChange,
  placeholder,
  multiline,
  keyboardType,
  error,
  hint,
  required,
}: {
  label: string;
  value: string;
  onChange(value: string): void;
  placeholder?: string;
  multiline?: boolean;
  keyboardType?:
    | 'default'
    | 'numeric'
    | 'decimal-pad'
    | 'email-address'
    | 'phone-pad';
  error?: string;
  hint?: string;
  required?: boolean;
}) {
  return (
    <View style={styles.field}>
      <Text style={styles.label}>{label}{required ? ' *' : ''}</Text>

      <TextInput
        keyboardType={keyboardType ?? 'default'}
        multiline={multiline}
        onChangeText={onChange}
        placeholder={placeholder}
        placeholderTextColor={colors.textSubtle}
        style={[styles.input, multiline && styles.inputMultiline, !!error && styles.inputError]}
        value={value}
      />
      {!!error && <Text style={styles.fieldError}>{error}</Text>}
      {!error && !!hint && <Text style={styles.fieldHint}>{hint}</Text>}
    </View>
  );
}

export function ReadOnlyField({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
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

/**
 * Tile de acción de alto nivel.
 *
 * Uso:
 * - Generar OT
 * - Generar grupo
 * - Crear cliente
 * - Importar
 * - Entrar a una función principal
 *
 * NO utilizar para:
 * - Guardar
 * - Continuar
 * - Completar
 * - Cancelar
 * - Eliminar
 */
type ActionTileIcon =
  ComponentProps<typeof MaterialCommunityIcons>['name'];

type ActionTileTone = 'primary' | 'secondary' | 'administrative';

export function ActionTile({
  icon,
  label,
  onPress,
  disabled,
  tone = 'primary',
}: {
  icon: ActionTileIcon;
  label: string;
  onPress(): void;
  disabled?: boolean;
  tone?: ActionTileTone;
}) {
  const circleStyle =
    tone === 'administrative'
      ? styles.actionTileIconAdministrative
      : tone === 'secondary'
        ? styles.actionTileIconSecondary
        : styles.actionTileIconPrimary;

  return (
    <Pressable
      accessibilityLabel={label}
      accessibilityRole="button"
      disabled={disabled}
      onPress={onPress}
      style={({ pressed }) => [
        styles.actionTile,
        pressed && styles.actionTilePressed,
        disabled && styles.buttonDisabled,
      ]}
    >
      <View style={[styles.actionTileIcon, circleStyle]}>
        <MaterialCommunityIcons
          color="#fff"
          name={icon}
          size={27}
        />
      </View>

      <Text numberOfLines={2} style={styles.actionTileLabel}>
        {label}
      </Text>
    </Pressable>
  );
}

/**
 * Anatomía compartida de las acciones OPERATIVAS (no launchers -- ver
 * ActionTile arriba). Es la variante horizontal/full-width del mismo
 * lenguaje visual: [círculo con icono] [etiqueta (+ descripción opcional)],
 * con superficie institucional en vez de un rectángulo de texto plano.
 *
 * PrimaryButton/SecondaryButton/AdministrativeButton/DangerButton son
 * wrappers semánticos sobre esta base -- el tono (color, relleno vs
 * contorno) es lo único que cambia entre ellos, nunca la estructura. Los
 * consumidores nunca deciden colores a mano.
 */
type OperationalActionIcon = ActionTileIcon;
type OperationalActionTone = 'primary' | 'secondary' | 'administrative' | 'danger';

type ButtonProps = {
  label: string;
  onPress(): void;
  disabled?: boolean;
  loading?: boolean;
  icon?: OperationalActionIcon;
  description?: string;
};

const TONE_DEFAULT_ICON: Record<OperationalActionTone, OperationalActionIcon> = {
  primary: 'arrow-right-circle',
  secondary: 'chevron-left',
  administrative: 'shield-outline',
  danger: 'trash-can-outline',
};

function OperationalActionButton({
  label,
  onPress,
  disabled,
  loading,
  icon,
  description,
  tone,
}: ButtonProps & { tone: OperationalActionTone }) {
  const resolvedIcon = icon ?? TONE_DEFAULT_ICON[tone];
  return (
    <Pressable
      accessibilityLabel={label}
      accessibilityRole="button"
      disabled={disabled || loading}
      onPress={onPress}
      style={({ pressed }) => [
        styles.operationalAction,
        styles[`operationalAction_${tone}`],
        pressed && styles.operationalActionPressed,
        (disabled || loading) && styles.buttonDisabled,
      ]}
    >
      <View style={[styles.operationalActionIcon, styles[`operationalActionIcon_${tone}`]]}>
        {loading ? (
          <ActivityIndicator color={styles[`operationalActionIconColor_${tone}`].color} size="small" />
        ) : (
          <MaterialCommunityIcons
            color={styles[`operationalActionIconColor_${tone}`].color}
            name={resolvedIcon}
            size={20}
          />
        )}
      </View>
      <View style={styles.operationalActionTextGroup}>
        <Text numberOfLines={2} style={[styles.operationalActionLabel, styles[`operationalActionLabel_${tone}`]]}>
          {label}
        </Text>
        {!!description && (
          <Text numberOfLines={2} style={[styles.operationalActionDescription, styles[`operationalActionDescription_${tone}`]]}>
            {description}
          </Text>
        )}
      </View>
    </Pressable>
  );
}

/** Acción principal del estado actual -- máximo una por sección. */
export function PrimaryButton(props: ButtonProps) {
  return <OperationalActionButton {...props} tone="primary" />;
}

/** Acción auxiliar/no destructiva. */
export function SecondaryButton(props: ButtonProps) {
  return <OperationalActionButton {...props} tone="secondary" />;
}

/** Operación destructiva real (eliminar, cancelar de forma irreversible). */
export function DangerButton(props: ButtonProps) {
  return <OperationalActionButton {...props} tone="danger" />;
}

/** Operación excepcional o administrativa (solicitar excepción, anular, reabrir). */
export function AdministrativeButton(props: ButtonProps) {
  return <OperationalActionButton {...props} tone="administrative" />;
}

/**
 * Composición vertical de acciones operativas full-width (Primary/Secondary/
 * Administrative/Danger, o un ActionRow horizontal como hijo).
 *
 * Distinto de ActionRow: ActionRow es horizontal, para acciones que
 * genuinamente comparten una fila (ver su propio uso). OperationalActionStack
 * es la variante vertical -- un paso de wizard, un formulario -- donde cada
 * acción ocupa el ancho completo y necesita separación vertical consistente.
 * El botón nunca conoce si tiene hermanos: la separación pertenece siempre
 * al contenedor, nunca a un marginTop/marginBottom puesto a mano en cada uno.
 */
export function OperationalActionStack({ children }: { children: ReactNode }) {
  return <View style={styles.operationalActionStack}>{children}</View>;
}

export type StatusTone =
  | 'info'
  | 'warning'
  | 'success'
  | 'danger'
  | 'purple'
  | 'neutral';

const TONE_COLOR: Record<StatusTone, string> = {
  info: colors.info,
  warning: colors.warning,
  success: colors.success,
  danger: colors.danger,
  purple: colors.purple,
  neutral: colors.textSubtle,
};

export function StatusBadge({
  label,
  tone = 'neutral',
}: {
  label: string;
  tone?: StatusTone;
}) {
  const tint = TONE_COLOR[tone];

  return (
    <View style={[styles.badge, { borderColor: tint }]}>
      <Text style={[styles.badgeText, { color: tint }]}>{label}</Text>
    </View>
  );
}

export function AlertBanner({
  tone = 'info',
  children,
}: {
  tone?: 'info' | 'warning' | 'danger' | 'success';
  children: ReactNode;
}) {
  const tint =
    tone === 'danger'
      ? colors.danger
      : tone === 'warning'
        ? colors.warningStrong
        : tone === 'success'
          ? colors.success
          : colors.info;

  return (
    <View style={[styles.alert, { borderColor: tint }]}>
      <Text style={[styles.alertText, { color: tint }]}>
        {children}
      </Text>
    </View>
  );
}

export function EmptyState({
  title,
  description,
}: {
  title: string;
  description?: string;
}) {
  return (
    <View style={styles.emptyState}>
      <Text style={styles.emptyTitle}>{title}</Text>

      {description && (
        <Text style={styles.emptyDescription}>{description}</Text>
      )}
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

export function FadeIn({
  children,
  transitionKey,
}: {
  children: ReactNode;
  transitionKey?: string | number;
}) {
  const opacity = useRef(new Animated.Value(0)).current;
  const translateY = useRef(new Animated.Value(6)).current;
  const [reduceMotion, setReduceMotion] = useState(false);

  useEffect(() => {
    let active = true;

    AccessibilityInfo.isReduceMotionEnabled?.()
      .then((value) => {
        if (active) setReduceMotion(value);
      })
      .catch(() => undefined);

    return () => {
      active = false;
    };
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
      Animated.timing(opacity, {
        toValue: 1,
        duration: 180,
        useNativeDriver: true,
      }),
      Animated.timing(translateY, {
        toValue: 0,
        duration: 180,
        useNativeDriver: true,
      }),
    ]).start();

    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [transitionKey, reduceMotion]);

  return (
    <Animated.View
      style={{
        opacity,
        transform: [{ translateY }],
      }}
    >
      {children}
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: colors.background,
  },

  section: {
    gap: spacing.sm,
    marginBottom: spacing.lg,
  },

  sectionTitle: {
    ...typography.sectionTitle,
    color: colors.text,
  },

  sectionDescription: {
    ...typography.meta,
    color: colors.textMuted,
  },

  card: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderRadius: radius.lg,
    borderWidth: 1,
    gap: spacing.sm,
    padding: spacing.lg,
    marginBottom: spacing.md,
  },

  field: {
    gap: spacing.xs,
    marginBottom: spacing.sm,
  },

  label: {
    ...typography.label,
    color: colors.textMuted,
  },

  input: {
    backgroundColor: colors.surface,
    borderColor: colors.borderStrong,
    borderRadius: radius.md,
    borderWidth: 1,
    minHeight: 44,
    paddingHorizontal: spacing.md,
    color: colors.text,
  },

  inputMultiline: {
    minHeight: 90,
    paddingTop: spacing.sm,
    textAlignVertical: 'top',
  },

  inputError: {
    borderColor: colors.danger,
  },

  fieldError: {
    color: colors.danger,
    fontSize: 12,
    fontWeight: '600',
  },

  fieldHint: {
    color: colors.textSubtle,
    fontSize: 12,
  },

  readOnlyValue: {
    ...typography.body,
    color: colors.text,
    paddingVertical: spacing.xs,
  },

  actionRow: {
    flexDirection: 'row',
    gap: spacing.sm,
    marginTop: spacing.md,
  },

  /*
   * Variante vertical de ActionRow: acciones operativas full-width apiladas,
   * con la separación vertical consistente entre ellas -- ver
   * OperationalActionStack arriba.
   */
  operationalActionStack: {
    gap: spacing.md,
    marginTop: spacing.md,
    width: '100%',
  },

  /*
   * Launcher / shortcut.
   * El contenedor queda prácticamente cuadrado y la leyenda siempre
   * permanece visible debajo del círculo del icono.
   */
  actionTile: {
    alignItems: 'center',
    aspectRatio: 1,
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderRadius: 16,
    borderWidth: 1,
    width: 92,
    height: 92,
    justifyContent: 'center',
    paddingHorizontal: 8,
    paddingVertical: 8,
  },

  actionTilePressed: {
    opacity: 0.72,
  },

  actionTileIcon: {
    alignItems: 'center',
    borderRadius: 999,
    height: 38,
    justifyContent: 'center',
    marginBottom: 6,
    width: 38,
  },

  actionTileIconPrimary: {
    backgroundColor: colors.primary,
  },

  actionTileIconSecondary: {
    backgroundColor: '#008f87',
  },

  actionTileIconAdministrative: {
    backgroundColor: colors.warningStrong,
  },

  actionTileLabel: {
    color: colors.text,
    fontSize: 14,
    fontWeight: '800',
    lineHeight: 18,
    minHeight: 36,
    textAlign: 'center',
  },

  /*
   * Anatomía compartida de las 4 acciones operativas: variante horizontal
   * del lenguaje visual de ActionTile -- [círculo con icono] [etiqueta].
   * minHeight fijo para que acciones vecinas (p.ej. dentro de un
   * ActionRow) compartan alto/radio/padding sin importar el tono, y para
   * que loading nunca cambie las dimensiones del control.
   */
  operationalAction: {
    alignItems: 'center',
    borderRadius: radius.lg,
    borderWidth: 1,
    flex: 1,
    flexDirection: 'row',
    gap: spacing.sm,
    minHeight: 56,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
  },

  operationalActionPressed: {
    opacity: 0.75,
  },

  operationalActionIcon: {
    alignItems: 'center',
    borderRadius: 999,
    height: 36,
    justifyContent: 'center',
    width: 36,
  },

  operationalActionTextGroup: {
    flexShrink: 1,
    gap: 1,
  },

  operationalActionLabel: {
    fontSize: 15,
    fontWeight: '800',
  },

  operationalActionDescription: {
    fontSize: 12,
    fontWeight: '500',
  },

  // Primary: relleno sólido -- la única acción principal de la sección.
  operationalAction_primary: {
    backgroundColor: colors.primary,
    borderColor: colors.primary,
  },
  operationalActionIcon_primary: {
    backgroundColor: 'rgba(255,255,255,0.22)',
  },
  operationalActionIconColor_primary: {
    color: '#fff',
  },
  operationalActionLabel_primary: {
    color: '#fff',
  },
  operationalActionDescription_primary: {
    color: 'rgba(255,255,255,0.85)',
  },

  // Secondary: contorno + acento primario, superficie institucional.
  operationalAction_secondary: {
    backgroundColor: colors.surface,
    borderColor: colors.primary,
  },
  operationalActionIcon_secondary: {
    backgroundColor: colors.primary,
  },
  operationalActionIconColor_secondary: {
    color: '#fff',
  },
  operationalActionLabel_secondary: {
    color: colors.primary,
  },
  operationalActionDescription_secondary: {
    color: colors.textMuted,
  },

  // Administrative: excepcional -- contorno punteado en tono de aviso.
  operationalAction_administrative: {
    backgroundColor: colors.surface,
    borderColor: colors.warningStrong,
    borderStyle: 'dashed',
  },
  operationalActionIcon_administrative: {
    backgroundColor: colors.warningStrong,
  },
  operationalActionIconColor_administrative: {
    color: '#fff',
  },
  operationalActionLabel_administrative: {
    color: colors.warningStrong,
  },
  operationalActionDescription_administrative: {
    color: colors.textMuted,
  },

  // Danger: destructiva real -- contorno en tono de peligro.
  operationalAction_danger: {
    backgroundColor: colors.surface,
    borderColor: colors.danger,
  },
  operationalActionIcon_danger: {
    backgroundColor: colors.danger,
  },
  operationalActionIconColor_danger: {
    color: '#fff',
  },
  operationalActionLabel_danger: {
    color: colors.dangerStrong,
  },
  operationalActionDescription_danger: {
    color: colors.textMuted,
  },

  buttonDisabled: {
    opacity: 0.42,
  },

  navAction: {
    minHeight: 44,
    justifyContent: 'center',
    paddingVertical: spacing.xs,
  },

  navActionDisabled: {
    opacity: 0.42,
  },

  navActionText: {
    color: colors.primary,
    fontWeight: '700',
  },

  badge: {
    alignSelf: 'flex-start',
    borderRadius: 999,
    borderWidth: 1,
    paddingHorizontal: spacing.sm,
    paddingVertical: 2,
  },

  badgeText: {
    fontSize: 12,
    fontWeight: '800',
  },

  alert: {
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    borderWidth: 1,
    marginBottom: spacing.md,
    padding: spacing.md,
  },

  alertText: {
    fontSize: 14,
    fontWeight: '600',
  },

  emptyState: {
    alignItems: 'center',
    gap: spacing.xs,
    padding: spacing.xl,
  },

  emptyTitle: {
    ...typography.sectionTitle,
    color: colors.text,
  },

  emptyDescription: {
    ...typography.meta,
    color: colors.textMuted,
    textAlign: 'center',
  },

  loadingState: {
    alignItems: 'center',
    gap: spacing.sm,
    padding: spacing.xl,
  },

  loadingLabel: {
    ...typography.meta,
    color: colors.textMuted,
  },
});
