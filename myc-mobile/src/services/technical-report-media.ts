import type { TechnicalReportEvidenceType } from '@/src/types/technical-report';

/**
 * Captura y preparación de fotografías de evidencia (SG-4C).
 *
 * La selección de medios vive detrás de `EvidenceMediaProvider` para poder
 * probar el flujo sin cámara física. La implementación real (cámara/galería
 * + redimensionado) requiere módulos nativos de Expo que NO están instalados
 * hoy (ver reporte SG-4C); mientras no exista proveedor, la UI no ofrece
 * "Agregar foto" y sólo muestra/elimina la evidencia ya subida.
 */

export type EvidenceSource = 'camera' | 'library';

/** Imagen ya preparada para subir: JPEG comprimido y orientación corregida. */
export type PreparedEvidenceImage = {
  uri: string;
  width: number;
  height: number;
  /** Siempre JPEG tras la preparación (HEIC se convierte en el dispositivo). */
  mimeType: 'image/jpeg';
  fileName: string;
  sizeBytes: number | null;
};

export type EvidenceMediaProvider = {
  /** Devuelve null si el técnico cancela. Lanza si falta permiso o falla. */
  capture(source: EvidenceSource): Promise<PreparedEvidenceImage | null>;
  availableSources: readonly EvidenceSource[];
};

/** Un paso de preparación: lado mayor máximo y calidad JPEG. */
export type EvidenceCompressionPass = { maxLongEdgePx: number; jpegQuality: number };

/** Política única de compresión (objetivo: <= 500 KiB sin perder legibilidad
 * de etiquetas ni conexiones). Cada paso parte del original (nunca se
 * recomprime un JPEG ya comprimido) y se detiene en cuanto el archivo cabe en
 * el objetivo. Máximo 3 pasos, sin loops abiertos; el piso es 1400 px / 0.60.
 * Backend rechaza > 5 MiB (barrera dura). */
export const EVIDENCE_IMAGE_POLICY = {
  maxLongEdgePx: 1800,
  jpegQuality: 0.75,
  targetMaxBytes: 500 * 1024,
  hardMaxBytes: 5 * 1024 * 1024,
  passes: [
    { maxLongEdgePx: 1800, jpegQuality: 0.75 },
    { maxLongEdgePx: 1800, jpegQuality: 0.6 },
    { maxLongEdgePx: 1400, jpegQuality: 0.6 },
  ],
} as const satisfies { passes: readonly EvidenceCompressionPass[] } & Record<string, unknown>;

export const MAX_EVIDENCE_PER_REPORT = 20;

/** Dimensiones finales: el lado mayor no excede maxLongEdgePx y nunca se amplía. */
export function planEvidenceResize(
  width: number,
  height: number,
  maxLongEdgePx: number = EVIDENCE_IMAGE_POLICY.maxLongEdgePx,
): { width: number; height: number } {
  const longEdge = Math.max(width, height);
  if (longEdge <= maxLongEdgePx) return { width, height };
  const scale = maxLongEdgePx / longEdge;
  return { width: Math.round(width * scale), height: Math.round(height * scale) };
}

let provider: EvidenceMediaProvider | null = null;

/** Registro del proveedor concreto (la app lo instala al arrancar cuando
 * existan los módulos nativos; las pruebas inyectan uno falso). */
export function setEvidenceMediaProvider(next: EvidenceMediaProvider | null): void {
  provider = next;
}

export function getEvidenceMediaProvider(): EvidenceMediaProvider | null {
  return provider;
}

export function buildEvidenceFormData(
  image: PreparedEvidenceImage,
  evidenceType: TechnicalReportEvidenceType,
): FormData {
  const form = new FormData();
  form.append('evidence_type', evidenceType);
  form.append('file', { uri: image.uri, name: image.fileName, type: image.mimeType } as unknown as Blob);
  return form;
}
