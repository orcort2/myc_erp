import { parseCivilDate } from '@/src/services/civil-date';
import {
  blitGlyph,
  createBitmapCanvas,
  glyphPixelSize,
  packBitmap,
  type BitmapCanvas,
} from './bitmap-canvas';
import { normalizeForBitmapFont } from './bitmap-font-5x7';
import type { LabelProfile } from './label-profile';
import {
  profileCanvasPx,
  profileSafeAreaPx,
} from './label-profile';
import type {
  LabLabelPayload,
  RasterLabel,
} from './label-types';
import { drawMycBadge } from './myc-badge';

/**
 * Renderer determinista:
 *
 * LabLabelPayload + LabelProfile + dpi -> RasterLabel
 *
 * Composición actual:
 *
 *                 CALIBRADO
 *
 *   [ LOGO MYC ]   FECHA DE CAL ...
 *                  PROX. CAL ...
 *                  CODIGO ...
 *                  O.T. ...
 *                  INFORME ...
 *
 * El logo ocupa como máximo ~30% del área horizontal disponible.
 * CALIBRADO es el elemento visual predominante.
 *
 * Por ahora esta plantilla sigue siendo exclusivamente de CALIBRACIÓN.
 * VERIFICADO se añadirá cuando la hoja de campo distinga formalmente
 * ambos tipos de servicio.
 */

export type LabelRenderErrorCode =
  | 'missing_calibration_date'
  | 'missing_certificate_folio';

export class LabelRenderError extends Error {
  readonly code: LabelRenderErrorCode;

  constructor(
    code: LabelRenderErrorCode,
    message: string,
  ) {
    super(message);
    this.code = code;
    this.name = 'LabelRenderError';
  }
}

const MIN_SCALE = 1;

/**
 * El título puede crecer más que el resto.
 */
const TITLE_MAX_SCALE = 5;

/**
 * El cuerpo debe conservar legibilidad y suficiente ancho para
 * fechas, códigos y folios.
 */
const BODY_MAX_SCALE = 5;

const CHAR_ADVANCE_DOTS = 6;

const NOT_AVAILABLE = 'N/A';
const TRUNCATION_MARK = '>';

const STATUS_TITLE = 'CALIBRADO';

function formatDateDDMMYYYY(
  value: string,
): string {
  const parsed =
    parseCivilDate(
      value,
    );

  if (!parsed) {
    return value;
  }

  const day =
    String(
      parsed.day,
    ).padStart(
      2,
      '0',
    );

  const month =
    String(
      parsed.month,
    ).padStart(
      2,
      '0',
    );

  return `${day}/${month}/${parsed.year}`;
}

export type LabelLine = {
  label: string;
  value: string;
};

/**
 * Contenido funcional de la etiqueta.
 *
 * Mantiene exactamente los cinco datos actuales.
 */
export function buildLabelLines(
  payload: LabLabelPayload,
): LabelLine[] {
  if (
    !payload.calibrationDate ||
    !payload.calibrationDate.trim()
  ) {
    throw new LabelRenderError(
      'missing_calibration_date',
      'La hoja no tiene fecha de calibración capturada; complétala antes de imprimir la etiqueta.',
    );
  }

  if (
    !payload.certificateFolio ||
    !payload.certificateFolio.trim()
  ) {
    throw new LabelRenderError(
      'missing_certificate_folio',
      'El equipo aún no tiene folio de certificado asignado. No se puede imprimir la etiqueta final.',
    );
  }

  return [
    {
      label: 'FECHA DE CAL',
      value:
        formatDateDDMMYYYY(
          payload.calibrationDate,
        ),
    },
    {
      label: 'PROX. CAL',
      value:
        payload.nextCalibrationDate
          ? formatDateDDMMYYYY(
              payload.nextCalibrationDate,
            )
          : NOT_AVAILABLE,
    },
    {
      label: 'CODIGO',
      value:
        payload.equipmentCode,
    },
    {
      label: 'O.T.',
      value:
        payload.workOrderFolio,
    },
    {
      label: 'INFORME',
      value:
        payload.certificateFolio,
    },
  ];
}

function lineText(
  line: LabelLine,
): string {
  return `${line.label} ${line.value}`;
}

function textWidthPx(
  text: string,
  scale: number,
): number {
  return (
    normalizeForBitmapFont(
      text,
    ).length *
    CHAR_ADVANCE_DOTS *
    scale
  );
}

/**
 * Si una línea no cabe ni siquiera a la escala elegida,
 * sólo se recorta el valor.
 *
 * La etiqueta del campo siempre permanece visible.
 */
export function fitLineToWidth(
  line: LabelLine,
  scale: number,
  maxWidthPx: number,
): LabelLine {
  if (
    textWidthPx(
      lineText(
        line,
      ),
      scale,
    ) <=
    maxWidthPx
  ) {
    return line;
  }

  let value =
    line.value;

  while (
    value.length >
    0
  ) {
    const candidate =
      `${value.slice(0, -1)}${TRUNCATION_MARK}`;

    if (
      textWidthPx(
        `${line.label} ${candidate}`,
        scale,
      ) <=
      maxWidthPx
    ) {
      return {
        label:
          line.label,
        value:
          candidate,
      };
    }

    value =
      value.slice(
        0,
        -1,
      );
  }

  return {
    label:
      line.label,
    value:
      TRUNCATION_MARK,
  };
}

/**
 * Todos los datos usan la misma escala.
 *
 * Eso mantiene una jerarquía consistente y evita que una línea parezca
 * accidentalmente más importante que las demás.
 */
function resolveCommonScale(
  lines: LabelLine[],
  maxWidthPx: number,
  maxLineHeightPx: number,
): number {
  const heightScale =
    Math.max(
      MIN_SCALE,
      Math.floor(
        (
          maxLineHeightPx *
          0.92
        ) /
          7,
      ),
    );

  let scale =
    Math.min(
      BODY_MAX_SCALE,
      heightScale,
    );

  /*
   * Priorizamos legibilidad física.
   *
   * El cuerpo nunca baja de escala 2 únicamente porque un valor
   * excepcionalmente largo no quepa. fitLineToWidth() recortará
   * únicamente ese valor si fuera necesario.
   */
  while (
    scale >
      MIN_SCALE &&
    lines.some(
      (line) =>
        textWidthPx(
          lineText(line),
          scale,
        ) > maxWidthPx,
    )
  ) {
    scale -= 1;
  }

  return Math.max(
    MIN_SCALE,
    scale,
  );
}
function drawLine(
  canvas: BitmapCanvas,
  text: string,
  x: number,
  y: number,
  scale: number,
): void {
  const normalized =
    normalizeForBitmapFont(
      text,
    );

  for (
    let index = 0;
    index <
    normalized.length;
    index += 1
  ) {
    blitGlyph(
      canvas,
      normalized[index],
      x +
        index *
          CHAR_ADVANCE_DOTS *
          scale,
      y,
      scale,
    );
  }
}

/**
 * Resuelve independientemente la escala del título.
 */
function resolveTitleScale(
  text: string,
  maxWidthPx: number,
  maxHeightPx: number,
): number {
  const heightScale =
    Math.max(
      MIN_SCALE,
      Math.floor(
        maxHeightPx /
          7,
      ),
    );

  let scale =
    Math.min(
      TITLE_MAX_SCALE,
      heightScale,
    );

  while (
    scale >
      MIN_SCALE &&
    textWidthPx(
      text,
      scale,
    ) >
      maxWidthPx
  ) {
    scale -= 1;
  }

  return Math.max(
    MIN_SCALE,
    scale,
  );
}

/**
 * Dibuja texto centrado horizontalmente dentro de un rectángulo.
 */
function drawCenteredText(
  canvas: BitmapCanvas,
  text: string,
  leftPx: number,
  widthPx: number,
  y: number,
  scale: number,
): void {
  const width =
    textWidthPx(
      text,
      scale,
    );

  const x =
    leftPx +
    Math.max(
      0,
      Math.floor(
        (
          widthPx -
          width
        ) /
          2,
      ),
    );

  drawLine(
    canvas,
    text,
    x,
    y,
    scale,
  );
}

export function renderLabel(
  payload: LabLabelPayload,
  profile: LabelProfile,
  dpi: number,
): RasterLabel {
  /**
   * Validación de dominio antes de crear siquiera el canvas.
   */
  const rawLines =
    buildLabelLines(
      payload,
    );

  const canvasSize =
    profileCanvasPx(
      profile,
      dpi,
    );

  const safeArea =
    profileSafeAreaPx(
      profile,
      dpi,
    );

  const canvas =
    createBitmapCanvas(
      canvasSize.widthPx,
      canvasSize.heightPx,
    );

  /*
   * ============================================================
   * 1. ENCABEZADO
   * ============================================================
   *
   * CALIBRADO debe dominar visualmente.
   *
   * Reservamos aproximadamente 25% de la altura útil.
   */

  const titleAreaHeight =
    Math.max(
      1,
      Math.round(
        safeArea.heightPx *
          0.25,
      ),
    );

  /*
   * Dejamos un pequeño margen horizontal para evitar que el título
   * quede demasiado cerca de los límites físicos.
   */
  const titleHorizontalMargin =
    Math.max(
      2,
      Math.round(
        safeArea.widthPx *
          0.03,
      ),
    );

  const titleAvailableWidth =
    Math.max(
      1,
      safeArea.widthPx -
        titleHorizontalMargin *
          2,
    );

  const titleScale =
    resolveTitleScale(
      STATUS_TITLE,
      titleAvailableWidth,
      Math.round(
        titleAreaHeight *
          0.82,
      ),
    );

  const titleGlyphHeight =
    glyphPixelSize(
      titleScale,
    ).heightPx;

  const titleY =
    safeArea.y +
    Math.max(
      0,
      Math.floor(
        (
          titleAreaHeight -
          titleGlyphHeight
        ) /
          2,
      ),
    );

  drawCenteredText(
    canvas,
    STATUS_TITLE,
    safeArea.x +
      titleHorizontalMargin,
    titleAvailableWidth,
    titleY,
    titleScale,
  );

  /*
   * ============================================================
   * 2. CUERPO
   * ============================================================
   */

  const bodyY =
    safeArea.y +
    titleAreaHeight;

  const bodyHeight =
    Math.max(
      1,
      safeArea.heightPx -
        titleAreaHeight,
    );

  /*
   * ============================================================
   * 3. LOGO
   * ============================================================
   *
   * Máximo 30% del ancho útil.
   *
   * También lo limitamos verticalmente al 70% del cuerpo para que no
   * compita con CALIBRADO ni con la información.
   */

  const badgeWidthTarget =
    Math.round(
      safeArea.widthPx *
        0.22,
    );

  const badgeHeightTarget =
    Math.round(
      bodyHeight *
        0.70,
    );

  const badgeSize =
    Math.max(
      1,
      Math.min(
        badgeWidthTarget,
        badgeHeightTarget,
      ),
    );

  const badgeX =
    safeArea.x;

  const badgeY =
    bodyY +
    Math.max(
      0,
      Math.floor(
        (
          bodyHeight -
          badgeSize
        ) /
          2,
      ),
    );

  drawMycBadge(
    canvas,
    badgeX,
    badgeY,
    badgeSize,
  );

  /*
   * ============================================================
   * 4. ÁREA DE DATOS
   * ============================================================
   */

  const badgeGapPx =
    Math.max(
      2,
      Math.round(
        badgeSize *
          0.04,
      ),
    );

  const textAreaX =
    badgeX +
    badgeSize +
    badgeGapPx;

  const textRightMarginPx =
    Math.max(
      4,
      Math.round(
        safeArea.widthPx *
          0.025,
      ),
    );

  const textAreaRight =
    safeArea.x +
    safeArea.widthPx -
    textRightMarginPx;

  const textAreaWidth =
    Math.max(
      1,
      textAreaRight -
        textAreaX,
    );

    const textAreaHeight =
      bodyHeight;

    /*
    * ============================================================
    * CUERPO COMPACTO
    * ============================================================
    *
    * Las líneas ya no se distribuyen por todo el alto disponible.
    *
    * Primero determinamos una escala grande y después agrupamos las
    * cinco líneas como un bloque vertical compacto.
    */

    const maxBodyLineHeight =
      Math.max(
        1,
        Math.floor(
          textAreaHeight /
            rawLines.length,
        ),
      );

    const bodyScale =
      resolveCommonScale(
        rawLines,
        textAreaWidth,
        maxBodyLineHeight,
      );

    const fittedLines =
      rawLines.map(
        (line) =>
          fitLineToWidth(
            line,
            bodyScale,
            textAreaWidth,
          ),
      );

    const glyphHeightPx =
      glyphPixelSize(
        bodyScale,
      ).heightPx;

    /*
    * Separación entre renglones.
    *
    * Aproximadamente 30% de la altura del propio glifo.
    * Esto deja respirar el texto pero elimina los grandes huecos
    * que tenía la primera versión.
    */
    const lineGapPx =
      Math.max(
        2,
        Math.round(
          glyphHeightPx *
            0.30,
        ),
      );

    const compactLineHeightPx =
      glyphHeightPx +
      lineGapPx;

    const textBlockHeight =
      glyphHeightPx *
        fittedLines.length +
      lineGapPx *
        (
          fittedLines.length -
          1
        );

    /*
    * El bloque completo queda centrado verticalmente junto al logo.
    */
    const textBlockY =
      bodyY +
      Math.max(
        0,
        Math.floor(
          (
            textAreaHeight -
            textBlockHeight
          ) /
            2,
        ),
      );
  /*
   * ============================================================
   * 5. DIBUJO DE DATOS
   * ============================================================
   */

    fittedLines.forEach(
      (
        line,
        index,
      ) => {
        const lineY =
          textBlockY +
          index *
            compactLineHeightPx;

        drawLine(
          canvas,
          lineText(
            line,
          ),
          textAreaX,
          lineY,
          bodyScale,
        );
      },
    );

  /*
   * ============================================================
   * 6. RASTER FINAL
   * ============================================================
   */

  return {
    widthPx:
      canvas.widthPx,

    heightPx:
      canvas.heightPx,

    bitmap:
      packBitmap(
        canvas,
      ),

    profileId:
      profile.id,
  };
}