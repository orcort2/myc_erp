import { parseCivilDate } from '@/src/services/civil-date';
import { blitGlyph, createBitmapCanvas, glyphPixelSize, packBitmap, type BitmapCanvas } from './bitmap-canvas';
import { normalizeForBitmapFont } from './bitmap-font-5x7';
import type { LabelProfile } from './label-profile';
import { profileCanvasPx, profileSafeAreaPx } from './label-profile';
import type { LabLabelPayload, RasterLabel } from './label-types';
import { drawMycBadge } from './myc-badge';

/**
 * Renderer determinista: LabLabelPayload + LabelProfile + dpi -> RasterLabel.
 * Dueño de layout, texto, insignia MYC, posicionamiento, área segura,
 * tipografía y la conversión final a raster monocromático. El adaptador de
 * impresora (NIIMBOT, NELKO, o el que siga) NUNCA ve estos campos ni sabe
 * qué significan -- sólo recibe el RasterLabel ya compuesto (ver
 * printers/types.ts LabelPrinterAdapter.print).
 *
 * NO incluye QR ni ningún dato fuera de los 5 campos v1 confirmados
 * (FECHA DE CAL, PROX. CAL, CODIGO, O.T., INFORME) -- agregar contenido
 * nuevo a la plantilla es una decisión de producto explícita, no algo que
 * este renderer deba inventar sólo porque la arquitectura lo permitiría.
 */

export type LabelRenderErrorCode = 'missing_calibration_date';

export class LabelRenderError extends Error {
  readonly code: LabelRenderErrorCode;

  constructor(code: LabelRenderErrorCode, message: string) {
    super(message);
    this.code = code;
    this.name = 'LabelRenderError';
  }
}

const MIN_SCALE = 1;
const MAX_SCALE = 4;
const CHAR_ADVANCE_DOTS = 6; // 5 puntos de glifo + 1 de espaciado
const NOT_AVAILABLE = 'N/A';
const PENDING_FOLIO = 'PENDIENTE';
const TRUNCATION_MARK = '>';

function formatDateDDMMYYYY(value: string): string {
  const parsed = parseCivilDate(value);
  // Un valor que el backend no debería producir nunca se oculta: se imprime
  // tal cual llegó, para que el problema sea visible y depurable en la
  // etiqueta física en vez de perderse en un raster "en blanco".
  if (!parsed) return value;
  const day = String(parsed.day).padStart(2, '0');
  const month = String(parsed.month).padStart(2, '0');
  return `${day}/${month}/${parsed.year}`;
}

export type LabelLine = { label: string; value: string };

/** Extraído como función pura exportada para poder probar el contenido
 * textual exacto de cada línea (fecha formateada, N/A, PENDIENTE) sin
 * depender de inspección de píxeles/OCR sobre el raster final. */
export function buildLabelLines(payload: LabLabelPayload): LabelLine[] {
  if (!payload.calibrationDate || !payload.calibrationDate.trim()) {
    throw new LabelRenderError(
      'missing_calibration_date',
      'La hoja no tiene fecha de calibración capturada; complétala antes de imprimir la etiqueta.',
    );
  }
  return [
    { label: 'FECHA DE CAL', value: formatDateDDMMYYYY(payload.calibrationDate) },
    {
      label: 'PROX. CAL',
      value: payload.nextCalibrationDate ? formatDateDDMMYYYY(payload.nextCalibrationDate) : NOT_AVAILABLE,
    },
    { label: 'CODIGO', value: payload.equipmentCode },
    { label: 'O.T.', value: payload.workOrderFolio },
    { label: 'INFORME', value: payload.certificateFolio ?? PENDING_FOLIO },
  ];
}

function lineText(line: LabelLine): string {
  return `${line.label} ${line.value}`;
}

function textWidthPx(text: string, scale: number): number {
  return normalizeForBitmapFont(text).length * CHAR_ADVANCE_DOTS * scale;
}

/** Recorta únicamente el VALOR (nunca la etiqueta) por el final, agregando
 * TRUNCATION_MARK, hasta que quepa en maxWidthPx a la escala dada. Preferir
 * un identificador completo sobre espacio decorativo: sólo se llega aquí si
 * ni siquiera MIN_SCALE alcanzó para mostrarlo completo. */
export function fitLineToWidth(line: LabelLine, scale: number, maxWidthPx: number): LabelLine {
  if (textWidthPx(lineText(line), scale) <= maxWidthPx) return line;
  let value = line.value;
  while (value.length > 0) {
    const candidate = `${value.slice(0, -1)}${TRUNCATION_MARK}`;
    if (textWidthPx(`${line.label} ${candidate}`, scale) <= maxWidthPx) {
      return { label: line.label, value: candidate };
    }
    value = value.slice(0, -1);
  }
  return { label: line.label, value: TRUNCATION_MARK };
}

function resolveCommonScale(lines: LabelLine[], maxWidthPx: number, maxLineHeightPx: number): number {
  const heightScale = Math.max(MIN_SCALE, Math.floor((maxLineHeightPx * 0.82) / 7));
  let scale = Math.min(MAX_SCALE, heightScale);
  while (scale > MIN_SCALE && lines.some((line) => textWidthPx(lineText(line), scale) > maxWidthPx)) {
    scale -= 1;
  }
  return Math.max(MIN_SCALE, scale);
}

function drawLine(canvas: BitmapCanvas, text: string, x: number, y: number, scale: number): void {
  const normalized = normalizeForBitmapFont(text);
  for (let index = 0; index < normalized.length; index += 1) {
    blitGlyph(canvas, normalized[index], x + index * CHAR_ADVANCE_DOTS * scale, y, scale);
  }
}

export function renderLabel(payload: LabLabelPayload, profile: LabelProfile, dpi: number): RasterLabel {
  const canvasSize = profileCanvasPx(profile, dpi);
  const safeArea = profileSafeAreaPx(profile, dpi);
  const canvas = createBitmapCanvas(canvasSize.widthPx, canvasSize.heightPx);

  const badgeSize = Math.max(1, Math.round(safeArea.heightPx * 0.2));
  const badgeGapPx = Math.max(1, Math.round(badgeSize * 0.15));
  drawMycBadge(canvas, safeArea.x, safeArea.y, badgeSize);

  const rawLines = buildLabelLines(payload);
  const textAreaY = safeArea.y + badgeSize + badgeGapPx;
  const textAreaHeightPx = safeArea.y + safeArea.heightPx - textAreaY;
  const lineHeightPx = Math.floor(textAreaHeightPx / rawLines.length);

  const scale = resolveCommonScale(rawLines, safeArea.widthPx, lineHeightPx);
  const fittedLines = rawLines.map((line) => fitLineToWidth(line, scale, safeArea.widthPx));

  const glyphHeightPx = glyphPixelSize(scale).heightPx;
  fittedLines.forEach((line, index) => {
    const lineTop = textAreaY + index * lineHeightPx;
    const lineCenterY = lineTop + Math.max(0, Math.round((lineHeightPx - glyphHeightPx) / 2));
    drawLine(canvas, lineText(line), safeArea.x, lineCenterY, scale);
  });

  return {
    widthPx: canvas.widthPx,
    heightPx: canvas.heightPx,
    bitmap: packBitmap(canvas),
    profileId: profile.id,
  };
}
