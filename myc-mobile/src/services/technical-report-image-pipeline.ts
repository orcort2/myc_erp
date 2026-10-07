import {
  EVIDENCE_IMAGE_POLICY,
  planEvidenceResize,
  type EvidenceMediaProvider,
  type EvidenceSource,
  type PreparedEvidenceImage,
} from '@/src/services/technical-report-media';

/**
 * Captura y preparación de una foto de evidencia, desacoplada de Expo y del
 * hardware: todo lo nativo entra por `EvidenceImagePipelineDeps`. El adaptador
 * real (technical-report-media-expo.ts) cablea expo-image-picker y
 * expo-image-manipulator; las pruebas inyectan dependencias falsas.
 */

export type PermissionOutcome = { granted: boolean };

/** Imagen cargada (orientación EXIF ya aplicada al renderizar). */
export type LoadedImage = { width: number; height: number };

export type PickedAsset = { uri: string };

export type EvidenceImagePipelineDeps<THandle extends LoadedImage = LoadedImage> = {
  requestPermission(source: EvidenceSource): Promise<PermissionOutcome>;
  /** null = el técnico canceló. */
  pick(source: EvidenceSource): Promise<PickedAsset | null>;
  /** Carga el original (HEIC/PNG/JPEG) normalizando orientación. */
  load(uri: string): Promise<THandle>;
  resize(image: THandle, size: { width: number; height: number }): Promise<THandle>;
  /** Guarda como JPEG con la calidad dada; la salida es un archivo nuevo. */
  saveJpeg(image: THandle, quality: number): Promise<{ uri: string; width: number; height: number }>;
  fileSize(uri: string): Promise<number | null>;
  fileName(): string;
};

export class EvidencePermissionError extends Error {
  constructor(readonly source: EvidenceSource) {
    super(
      source === 'camera'
        ? 'MYC Mobile no tiene permiso para usar la cámara. Actívalo en Ajustes para tomar fotos del reporte.'
        : 'MYC Mobile no tiene permiso para acceder a tus fotos. Actívalo en Ajustes para adjuntar evidencia.',
    );
    this.name = 'EvidencePermissionError';
  }
}

export class EvidenceProcessingError extends Error {
  constructor(cause?: unknown) {
    super('No fue posible preparar la foto para subirla. Intenta nuevamente con otra imagen.');
    this.name = 'EvidenceProcessingError';
    this.cause = cause;
  }
}

/**
 * Permiso -> selector -> normalización a JPEG (HEIC/HEIF/PNG incluidos) ->
 * redimensionado sin ampliar -> compresión por pasos acotados (máx. 3, cada
 * uno desde el original). Devuelve null si el técnico cancela.
 */
export async function captureEvidenceImage<THandle extends LoadedImage>(
  source: EvidenceSource,
  deps: EvidenceImagePipelineDeps<THandle>,
): Promise<PreparedEvidenceImage | null> {
  const permission = await deps.requestPermission(source);
  if (!permission.granted) throw new EvidencePermissionError(source);

  const picked = await deps.pick(source);
  if (!picked) return null;

  try {
    const original = await deps.load(picked.uri);
    let best: { uri: string; width: number; height: number; size: number | null } | null = null;
    for (const pass of EVIDENCE_IMAGE_POLICY.passes) {
      const target = planEvidenceResize(original.width, original.height, pass.maxLongEdgePx);
      const resized = target.width === original.width && target.height === original.height
        ? original
        : await deps.resize(original, target);
      const saved = await deps.saveJpeg(resized, pass.jpegQuality);
      const size = await deps.fileSize(saved.uri);
      best = { ...saved, size };
      // Tamaño desconocido: no se sigue recomprimiendo a ciegas.
      if (size === null || size <= EVIDENCE_IMAGE_POLICY.targetMaxBytes) break;
    }
    if (!best) throw new Error('Sin resultado de compresión');
    if (best.size !== null && best.size > EVIDENCE_IMAGE_POLICY.hardMaxBytes) {
      throw new Error('La foto excede el límite permitido incluso comprimida');
    }
    return {
      uri: best.uri,
      width: best.width,
      height: best.height,
      mimeType: 'image/jpeg',
      fileName: deps.fileName(),
      sizeBytes: best.size,
    };
  } catch (error) {
    throw new EvidenceProcessingError(error);
  }
}

export function createEvidenceMediaProvider<THandle extends LoadedImage>(
  deps: EvidenceImagePipelineDeps<THandle>,
  availableSources: readonly EvidenceSource[] = ['camera', 'library'],
): EvidenceMediaProvider {
  return {
    availableSources,
    capture: (source) => captureEvidenceImage(source, deps),
  };
}
