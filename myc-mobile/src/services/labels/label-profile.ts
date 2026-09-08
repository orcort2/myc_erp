/**
 * Perfil físico de plantilla, independiente de cualquier impresora. El DPI
 * NO vive aquí: pertenece a las capacidades de renderizado/dispositivo (ver
 * LabelPrinterAdapter.dpi) -- hoy las dos impresoras conocidas (NIIMBOT B1,
 * NELKO PM220) son 203 dpi, pero eso es una coincidencia del hardware
 * actual, nunca una suposición permanente de MYC.
 */
export type LabelOrientation = 'landscape' | 'portrait';

export type LabelProfile = {
  id: string;
  /** Tamaño físico del medio (mm) -- NUNCA el área segura de contenido.
   * No confundir con las dimensiones de impresión de ninguna impresora. */
  physicalWidthMm: number;
  physicalHeightMm: number;
  /** Margen de seguridad aproximado alrededor del contenido (mm) por lado. */
  safeMarginMm: number;
  orientation: LabelOrientation;
};

/**
 * Plantilla física real de MYC: 50x30 mm es el tamaño físico del medio
 * (NUNCA cambiar esto a 48x28 -- esa es sólo el área de contenido segura,
 * aprox. 1 mm de margen por lado, ver safeMarginMm). No confundir con
 * ninguna limitación de cabezal de impresión (esa es una capacidad de la
 * impresora, ver LabelPrinterAdapter, no del perfil).
 */
export const MYC_50X30: LabelProfile = {
  id: 'MYC_50X30',
  physicalWidthMm: 50,
  physicalHeightMm: 30,
  safeMarginMm: 1,
  orientation: 'landscape',
};

export type PixelSize = { widthPx: number; heightPx: number };
export type PixelRect = { x: number; y: number; widthPx: number; heightPx: number };

/** px = round(mm / 25.4 * dpi) -- única función de conversión mm->px del
 * proyecto; todo lo demás debe importarla en vez de repetir la fórmula. */
export function mmToPx(mm: number, dpi: number): number {
  return Math.round((mm / 25.4) * dpi);
}

/** Lienzo físico completo del perfil a un DPI dado (p.ej. MYC_50X30 a 203
 * dpi ~= 400x240 px). */
export function profileCanvasPx(profile: LabelProfile, dpi: number): PixelSize {
  return {
    widthPx: mmToPx(profile.physicalWidthMm, dpi),
    heightPx: mmToPx(profile.physicalHeightMm, dpi),
  };
}

/** Área seguro de contenido (p.ej. ~48x28 mm ~= 384x224 px a 203 dpi para
 * MYC_50X30) -- ver advertencia en LabelProfile.physicalWidthMm: esto es lo
 * que puede variar por impresora/perfil, la plantilla física 50x30 no. */
export function profileSafeAreaPx(profile: LabelProfile, dpi: number): PixelRect {
  const marginPx = mmToPx(profile.safeMarginMm, dpi);
  const canvas = profileCanvasPx(profile, dpi);
  return {
    x: marginPx,
    y: marginPx,
    widthPx: canvas.widthPx - marginPx * 2,
    heightPx: canvas.heightPx - marginPx * 2,
  };
}
