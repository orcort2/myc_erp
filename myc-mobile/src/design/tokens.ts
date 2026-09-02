/**
 * Fase 6: escala común de spacing/color/tipografía para el flujo LAB/
 * FieldSheets -- elimina el patrón de estilos duplicados por pantalla que
 * traía LabTechnicalCapture/LabEquipmentForm/work-orders.tsx (cada uno con
 * su propio StyleSheet.create ad hoc). No es obligatorio adoptar esto en
 * todo Mobile en esta fase; sí lo es dejar de introducir más duplicación en
 * el área que Fase 6 toca.
 */
export const spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 20,
  xl: 32,
} as const;

export const radius = {
  sm: 8,
  md: 10,
  lg: 14,
} as const;

export const colors = {
  background: '#f4f7fa',
  surface: '#ffffff',
  border: '#dbe4ea',
  borderStrong: '#b9c8d2',
  text: '#142b3a',
  textMuted: '#51606f',
  textSubtle: '#637280',
  primary: '#0067a8',
  primarySoft: '#dff3f1',
  accent: '#008f87',
  warning: '#d7a51b',
  warningStrong: '#d87913',
  danger: '#c73636',
  dangerStrong: '#9b1c1c',
  success: '#16834b',
  info: '#2f7fd1',
  purple: '#7a52c9',
} as const;

export const typography = {
  eyebrow: { fontSize: 12, fontWeight: '800' as const, letterSpacing: 1 },
  title: { fontSize: 22, fontWeight: '800' as const },
  sectionTitle: { fontSize: 17, fontWeight: '800' as const },
  label: { fontSize: 12, fontWeight: '700' as const },
  body: { fontSize: 15 },
  meta: { fontSize: 13 },
};
