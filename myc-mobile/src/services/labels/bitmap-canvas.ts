import type { MonochromeBitmap } from './label-types';
import { GLYPH_HEIGHT, GLYPH_WIDTH, glyphFor } from './bitmap-font-5x7';

/**
 * Primitivas de dibujo puras sobre un bitmap monocromático en memoria (un
 * byte por pixel internamente, 0|1 -- se empaqueta a MSB-first sólo al
 * exportar, ver packBitmap). Sin dependencias de Canvas/Skia/nativas: esto
 * es lo que permite que LabelRenderer sea 100% determinista y testeable en
 * Node (tsx --test) sin ningún arnés de render.
 */
export type BitmapCanvas = {
  widthPx: number;
  heightPx: number;
  pixels: Uint8Array; // widthPx * heightPx, 1 byte por pixel, 0|1
};

export function createBitmapCanvas(widthPx: number, heightPx: number): BitmapCanvas {
  return { widthPx, heightPx, pixels: new Uint8Array(widthPx * heightPx) };
}

export function setPixel(canvas: BitmapCanvas, x: number, y: number, ink: boolean): void {
  if (x < 0 || y < 0 || x >= canvas.widthPx || y >= canvas.heightPx) return;
  canvas.pixels[y * canvas.widthPx + x] = ink ? 1 : 0;
}

export function getPixel(canvas: BitmapCanvas, x: number, y: number): boolean {
  if (x < 0 || y < 0 || x >= canvas.widthPx || y >= canvas.heightPx) return false;
  return canvas.pixels[y * canvas.widthPx + x] === 1;
}

export function fillRect(
  canvas: BitmapCanvas,
  x: number,
  y: number,
  widthPx: number,
  heightPx: number,
  ink: boolean,
): void {
  for (let row = 0; row < heightPx; row += 1) {
    for (let col = 0; col < widthPx; col += 1) {
      setPixel(canvas, x + col, y + row, ink);
    }
  }
}

/** Dibuja un glifo escalado por bloques (cada punto de la fuente 5x7 se
 * expande a un cuadrado scale x scale). invert=true dibuja el glifo en
 * "hueco" (blanco) sobre fondo de tinta, usado para el badge MYC. */
export function blitGlyph(
  canvas: BitmapCanvas,
  char: string,
  x: number,
  y: number,
  scale: number,
  options?: { invert?: boolean },
): void {
  const invert = options?.invert ?? false;
  const glyph = glyphFor(char);
  for (let row = 0; row < GLYPH_HEIGHT; row += 1) {
    const line = glyph[row];
    for (let col = 0; col < GLYPH_WIDTH; col += 1) {
      const dot = line[col] === '#';
      const ink = invert ? !dot : dot;
      fillRect(canvas, x + col * scale, y + row * scale, scale, scale, ink);
    }
  }
}

export function glyphPixelSize(scale: number): { widthPx: number; heightPx: number } {
  return { widthPx: GLYPH_WIDTH * scale, heightPx: GLYPH_HEIGHT * scale };
}

/** Empaqueta el bitmap en memoria (1 byte/pixel) al formato final de
 * MonochromeBitmap (1 bit/pixel, MSB primero, stride = ceil(width/8)) --
 * único punto de conversión, para que ni el renderer ni ningún adaptador de
 * impresora reimplementen el empaquetado por su cuenta. */
export function packBitmap(canvas: BitmapCanvas): MonochromeBitmap {
  const stride = Math.ceil(canvas.widthPx / 8);
  const rows: Uint8Array[] = [];
  for (let y = 0; y < canvas.heightPx; y += 1) {
    const row = new Uint8Array(stride);
    for (let x = 0; x < canvas.widthPx; x += 1) {
      if (!getPixel(canvas, x, y)) continue;
      const byteIndex = Math.floor(x / 8);
      const bitIndex = 7 - (x % 8);
      row[byteIndex] |= 1 << bitIndex;
    }
    rows.push(row);
  }
  return { widthPx: canvas.widthPx, heightPx: canvas.heightPx, rows };
}
