import {
  fillRect,
  type BitmapCanvas,
} from './bitmap-canvas';

/**
 * Logo MYC monocromático para impresión térmica.
 *
 * Construido directamente con primitivas raster.
 * No utiliza PNG/SVG ni rasterización externa.
 *
 * El diseño conserva:
 * - doble óvalo exterior;
 * - arco interior superior;
 * - gota;
 * - letras MYC;
 * - graduaciones;
 * - termómetro inferior.
 *
 * Los colores del logotipo original se convierten a negro.
 */

function setPixel(
  canvas: BitmapCanvas,
  x: number,
  y: number,
  black = true,
): void {
  fillRect(
    canvas,
    Math.round(x),
    Math.round(y),
    1,
    1,
    black,
  );
}

function drawLine(
  canvas: BitmapCanvas,
  x0: number,
  y0: number,
  x1: number,
  y1: number,
  thickness = 1,
): void {
  let currentX = Math.round(x0);
  let currentY = Math.round(y0);

  const targetX = Math.round(x1);
  const targetY = Math.round(y1);

  const dx = Math.abs(targetX - currentX);
  const sx = currentX < targetX ? 1 : -1;

  const dy = -Math.abs(targetY - currentY);
  const sy = currentY < targetY ? 1 : -1;

  let error = dx + dy;

  for (;;) {
    fillRect(
      canvas,
      currentX - Math.floor(thickness / 2),
      currentY - Math.floor(thickness / 2),
      thickness,
      thickness,
      true,
    );

    if (
      currentX === targetX &&
      currentY === targetY
    ) {
      break;
    }

    const twiceError = 2 * error;

    if (twiceError >= dy) {
      error += dy;
      currentX += sx;
    }

    if (twiceError <= dx) {
      error += dx;
      currentY += sy;
    }
  }
}

function drawEllipse(
  canvas: BitmapCanvas,
  centerX: number,
  centerY: number,
  radiusX: number,
  radiusY: number,
  thickness: number,
): void {
  const steps = Math.max(
    80,
    Math.round(
      Math.PI *
        Math.max(radiusX, radiusY) *
        2,
    ),
  );

  let previousX =
    centerX + radiusX;

  let previousY =
    centerY;

  for (
    let index = 1;
    index <= steps;
    index += 1
  ) {
    const angle =
      (index / steps) *
      Math.PI *
      2;

    const currentX =
      centerX +
      Math.cos(angle) *
        radiusX;

    const currentY =
      centerY +
      Math.sin(angle) *
        radiusY;

    drawLine(
      canvas,
      previousX,
      previousY,
      currentX,
      currentY,
      thickness,
    );

    previousX =
      currentX;

    previousY =
      currentY;
  }
}

function drawArc(
  canvas: BitmapCanvas,
  centerX: number,
  centerY: number,
  radiusX: number,
  radiusY: number,
  startAngle: number,
  endAngle: number,
  thickness: number,
): void {
  const steps = 90;

  let previousX =
    centerX +
    Math.cos(startAngle) *
      radiusX;

  let previousY =
    centerY +
    Math.sin(startAngle) *
      radiusY;

  for (
    let index = 1;
    index <= steps;
    index += 1
  ) {
    const progress =
      index / steps;

    const angle =
      startAngle +
      (endAngle - startAngle) *
        progress;

    const currentX =
      centerX +
      Math.cos(angle) *
        radiusX;

    const currentY =
      centerY +
      Math.sin(angle) *
        radiusY;

    drawLine(
      canvas,
      previousX,
      previousY,
      currentX,
      currentY,
      thickness,
    );

    previousX =
      currentX;

    previousY =
      currentY;
  }
}

function fillCircle(
  canvas: BitmapCanvas,
  centerX: number,
  centerY: number,
  radius: number,
  black = true,
): void {
  const r =
    Math.max(
      1,
      Math.round(radius),
    );

  for (
    let offsetY = -r;
    offsetY <= r;
    offsetY += 1
  ) {
    const horizontal =
      Math.floor(
        Math.sqrt(
          Math.max(
            0,
            r * r -
              offsetY *
                offsetY,
          ),
        ),
      );

    fillRect(
      canvas,
      Math.round(centerX - horizontal),
      Math.round(centerY + offsetY),
      horizontal * 2 + 1,
      1,
      black,
    );
  }
}

function drawDrop(
  canvas: BitmapCanvas,
  centerX: number,
  centerY: number,
  size: number,
): void {
  const radius =
    Math.max(
      2,
      size * 0.16,
    );

  const bulbX =
    centerX -
    size * 0.04;

  const bulbY =
    centerY +
    size * 0.08;

  fillCircle(
    canvas,
    bulbX,
    bulbY,
    radius,
    true,
  );

  /*
   * Punta inclinada hacia arriba/derecha,
   * como en el logo original.
   */
  const tipX =
    centerX +
    size * 0.25;

  const tipY =
    centerY -
    size * 0.25;

  const steps =
    Math.max(
      4,
      Math.round(
        size * 0.3,
      ),
    );

  for (
    let index = 0;
    index <= steps;
    index += 1
  ) {
    const progress =
      index / steps;

    const lineX =
      bulbX +
      (tipX - bulbX) *
        progress;

    const lineY =
      bulbY +
      (tipY - bulbY) *
        progress;

    const width =
      Math.max(
        1,
        Math.round(
          radius *
            2 *
            (1 - progress),
        ),
      );

    fillRect(
      canvas,
      Math.round(
        lineX -
          width / 2,
      ),
      Math.round(lineY),
      width,
      2,
      true,
    );
  }
}

function drawGraduations(
  canvas: BitmapCanvas,
  x: number,
  y: number,
  width: number,
  height: number,
): void {
  const count = 6;

  const spacing =
    width /
    (count - 1);

  const thickness =
    Math.max(
      1,
      Math.round(
        height * 0.18,
      ),
    );

  for (
    let index = 0;
    index < count;
    index += 1
  ) {
    const tickX =
      x +
      index *
        spacing;

    const tickHeight =
      index % 2 === 0
        ? height
        : height * 0.72;

    fillRect(
      canvas,
      Math.round(tickX),
      Math.round(y),
      thickness,
      Math.max(
        1,
        Math.round(
          tickHeight,
        ),
      ),
      true,
    );
  }
}

function drawThermometer(
  canvas: BitmapCanvas,
  x: number,
  y: number,
  width: number,
  height: number,
): void {
  const bulbRadius =
    Math.max(
      2,
      height * 0.28,
    );

  const bulbX =
    x +
    width -
    bulbRadius -
    height * 0.08;

  const bulbY =
    y +
    height / 2;

  const tubeLeft =
    x +
    height * 0.18;

  const tubeRight =
    bulbX -
    bulbRadius *
      0.55;

  const outerThickness =
    Math.max(
      1,
      Math.round(
        height * 0.08,
      ),
    );

  const tubeTop =
    bulbY -
    height * 0.13;

  const tubeBottom =
    bulbY +
    height * 0.13;

  /*
   * Contorno del tubo.
   */
  drawLine(
    canvas,
    tubeLeft,
    tubeTop,
    tubeRight,
    tubeTop,
    outerThickness,
  );

  drawLine(
    canvas,
    tubeLeft,
    tubeBottom,
    tubeRight,
    tubeBottom,
    outerThickness,
  );

  /*
   * Extremo redondeado izquierdo.
   */
  drawArc(
    canvas,
    tubeLeft,
    bulbY,
    height * 0.15,
    height * 0.15,
    Math.PI / 2,
    Math.PI * 1.5,
    outerThickness,
  );

  /*
   * Circunferencia exterior del bulbo.
   */
  drawEllipse(
    canvas,
    bulbX,
    bulbY,
    bulbRadius,
    bulbRadius,
    outerThickness,
  );

  /*
   * Mercurio.
   */
  const mercuryThickness =
    Math.max(
      1,
      Math.round(
        height * 0.11,
      ),
    );

  drawLine(
    canvas,
    tubeLeft +
      height * 0.12,
    bulbY,
    bulbX,
    bulbY,
    mercuryThickness,
  );

  fillCircle(
    canvas,
    bulbX,
    bulbY,
    bulbRadius * 0.63,
    true,
  );
}

function drawMycLetters(
  canvas: BitmapCanvas,
  x: number,
  y: number,
  width: number,
): void {
  /**
   * Letras MYC construidas geométricamente.
   *
   * No dependen de la fuente 5x7 porque el logotipo necesita
   * trazos mucho más gruesos y proporciones propias.
   */

  const letterHeight =
    Math.max(
      8,
      Math.round(
        width * 0.28,
      ),
    );

  const stroke =
    Math.max(
      2,
      Math.round(
        letterHeight * 0.18,
      ),
    );

  const gap =
    Math.max(
      2,
      Math.round(
        width * 0.035,
      ),
    );

  const mWidth =
    Math.round(
      width * 0.31,
    );

  const yWidth =
    Math.round(
      width * 0.25,
    );

  const cWidth =
    Math.round(
      width * 0.28,
    );

  const totalWidth =
    mWidth +
    yWidth +
    cWidth +
    gap * 2;

  const startX =
    x +
    Math.max(
      0,
      Math.round(
        (
          width -
          totalWidth
        ) /
          2,
      ),
    );

  const top =
    y;

  const bottom =
    y +
    letterHeight;

  /*
   * ------------------------------------------------------------
   * M
   * ------------------------------------------------------------
   */

  const mX =
    startX;

  drawLine(
    canvas,
    mX,
    bottom,
    mX,
    top,
    stroke,
  );

  drawLine(
    canvas,
    mX + mWidth,
    bottom,
    mX + mWidth,
    top,
    stroke,
  );

  drawLine(
    canvas,
    mX,
    top,
    mX + mWidth * 0.5,
    top + letterHeight * 0.62,
    stroke,
  );

  drawLine(
    canvas,
    mX + mWidth,
    top,
    mX + mWidth * 0.5,
    top + letterHeight * 0.62,
    stroke,
  );

  /*
   * ------------------------------------------------------------
   * Y
   * ------------------------------------------------------------
   */

  const yX =
    mX +
    mWidth +
    gap;

  const yCenter =
    yX +
    yWidth / 2;

  const branchY =
    top +
    letterHeight * 0.48;

  drawLine(
    canvas,
    yX,
    top,
    yCenter,
    branchY,
    stroke,
  );

  drawLine(
    canvas,
    yX + yWidth,
    top,
    yCenter,
    branchY,
    stroke,
  );

  drawLine(
    canvas,
    yCenter,
    branchY,
    yCenter,
    bottom,
    stroke,
  );

  /*
   * ------------------------------------------------------------
   * C
   * ------------------------------------------------------------
   *
   * Arco grueso abierto hacia la derecha.
   */

  const cX =
    yX +
    yWidth +
    gap;

  const cCenterX =
    cX +
    cWidth / 2;

  const cCenterY =
    top +
    letterHeight / 2;

  drawArc(
    canvas,
    cCenterX,
    cCenterY,
    cWidth * 0.46,
    letterHeight * 0.46,
    Math.PI * 0.23,
    Math.PI * 1.77,
    stroke,
  );
}
export function drawMycBadge(
  canvas: BitmapCanvas,
  x: number,
  y: number,
  size: number,
): void {
  /*
   * El asset original es ligeramente más ancho que alto.
   *
   * Como la API histórica recibe un único "size", mantenemos esa API
   * y construimos el logo dentro de ese cuadrado.
   */
  const width =
    size;

  const height =
    size * 0.82;

  const originY =
    y +
    (
      size -
      height
    ) /
      2;

  const centerX =
    x +
    width / 2;

  const centerY =
    originY +
    height / 2;

  const stroke =
    Math.max(
      1,
      Math.round(
        size * 0.018,
      ),
    );

  /*
   * ------------------------------------------------------------
   * DOBLE ÓVALO EXTERIOR
   * ------------------------------------------------------------
   */

  drawEllipse(
    canvas,
    centerX,
    centerY,
    width * 0.48,
    height * 0.48,
    stroke,
  );

  drawEllipse(
    canvas,
    centerX,
    centerY,
    width * 0.455,
    height * 0.455,
    stroke,
  );

  /*
   * ------------------------------------------------------------
   * ARCO SUPERIOR INTERIOR
   * ------------------------------------------------------------
   */

  drawArc(
    canvas,
    centerX,
    originY +
      height * 0.46,
    width * 0.405,
    height * 0.34,
    Math.PI,
    Math.PI * 2,
    Math.max(
      stroke,
      Math.round(
        size * 0.028,
      ),
    ),
  );

  /*
   * ------------------------------------------------------------
   * GOTA
   * ------------------------------------------------------------
   */

  drawDrop(
    canvas,
    centerX,
    originY +
      height * 0.235,
    size * 0.2,
  );

  /*
   * ------------------------------------------------------------
   * MYC
   * ------------------------------------------------------------
   */

  drawMycLetters(
    canvas,
    x +
      width * 0.2,
    originY +
      height * 0.39,
    width * 0.6,
  );

  /*
   * ------------------------------------------------------------
   * ESCALA / GRADUACIONES
   * ------------------------------------------------------------
   */

  drawGraduations(
    canvas,
    x +
      width * 0.34,
    originY +
      height * 0.62,
    width * 0.28,
    height * 0.055,
  );

  /*
   * ------------------------------------------------------------
   * TERMÓMETRO
   * ------------------------------------------------------------
   */

  drawThermometer(
    canvas,
    x +
      width * 0.24,
    originY +
      height * 0.69,
    width * 0.53,
    height * 0.18,
  );

  /*
   * Mantener referencia explícita para evitar que herramientas muy
   * agresivas consideren setPixel código muerto mientras afinamos el
   * raster del logo.
   */
  void setPixel;
}