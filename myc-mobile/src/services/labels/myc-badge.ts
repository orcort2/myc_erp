import { blitGlyph, fillRect, type BitmapCanvas } from './bitmap-canvas';

/**
 * Reimplementación propia, a resolución de impresión térmica, del isotipo
 * MYC (insignia redondeada oscura con "M"/"C" en hueco y una barra de
 * acento -- ver frontend/src/assets/myc-logo.svg como referencia visual
 * únicamente). Por AGENTS.md, myc-mobile nunca importa ni comparte el
 * asset del ERP: esto es arte propio, a un tamaño y densidad de bit
 * pensados para 203 dpi monocromático, no una conversión de ese PNG/SVG.
 * Un color se pierde por completo en monocromático (la "M" blanca y la "C"
 * turquesa del original se funden en una sola tinta de hueco) -- eso es
 * intencional y suficiente para v1: "optimizar para legibilidad física",
 * no reproducir la paleta.
 */
export function drawMycBadge(canvas: BitmapCanvas, x: number, y: number, size: number): void {
  // Insignia sólida (esquinas recortadas ~12% para sugerir el borde
  // redondeado del original sin necesitar un rasterizador de curvas).
  const corner = Math.max(1, Math.round(size * 0.12));
  fillRect(canvas, x, y, size, size, true);
  fillRect(canvas, x, y, corner, corner, false);
  fillRect(canvas, x + size - corner, y, corner, corner, false);
  fillRect(canvas, x, y + size - corner, corner, corner, false);
  fillRect(canvas, x + size - corner, y + size - corner, corner, corner, false);

  // "M" y "C" en hueco (blanco sobre la insignia), centradas en la mitad
  // superior -- misma composición relativa que el original (glifos en la
  // mitad de arriba, barra de acento hacia abajo).
  const scale = Math.max(1, Math.floor((size * 0.16) / 5));
  const glyphW = 5 * scale;
  const glyphGap = Math.max(1, Math.round(scale));
  const pairWidth = glyphW * 2 + glyphGap;
  const startX = x + Math.round((size - pairWidth) / 2);
  const startY = y + Math.round(size * 0.18);
  blitGlyph(canvas, 'M', startX, startY, scale, { invert: true });
  blitGlyph(canvas, 'C', startX + glyphW + glyphGap, startY, scale, { invert: true });

  // Barra de acento en hueco cerca de la base.
  const barMargin = Math.max(2, Math.round(size * 0.14));
  const barHeight = Math.max(1, Math.round(size * 0.05));
  const barY = y + size - Math.round(size * 0.22);
  fillRect(canvas, x + barMargin, barY, size - barMargin * 2, barHeight, false);
}
