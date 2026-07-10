import mycLogo from '../../assets/myc-logo.png';

import {
  mmToPx,
  normalizeDocumentDefinition,
  pxToMm,
  validateDocumentDefinition,
} from './documentDesignerModel.js';

const ASSET_REGISTRY = {
  'myc-logo': mycLogo,
};

function resolveBindingValue(element, definition, data = {}) {
  if (!element.binding) {
    return element.fallback_value ?? '';
  }

  if (Object.prototype.hasOwnProperty.call(data, element.binding)) {
    return data[element.binding];
  }

  if (
    definition.bindings &&
    Object.prototype.hasOwnProperty.call(definition.bindings, element.binding)
  ) {
    return definition.bindings[element.binding];
  }

  return element.fallback_value ?? '';
}

function toCssFontSize(value) {
  const number = Number(value);

  if (!Number.isFinite(number) || number <= 0) {
    return '12px';
  }

  return `${number}px`;
}

function buildCommonElementStyle(element) {
  return {
    position: 'absolute',
    left: `${mmToPx(element.x)}px`,
    top: `${mmToPx(element.y)}px`,
    width: `${mmToPx(element.width)}px`,
    height: `${mmToPx(element.height)}px`,
    transform: `rotate(${Number(element.rotation) || 0}deg)`,
    transformOrigin: 'center',
    zIndex: Number(element.z_index) || 1,
    display: element.visible === false ? 'none' : undefined,
    boxSizing: 'border-box',
  };
}

function buildTextStyle(element) {
  const style = element.style || {};

  return {
    ...buildCommonElementStyle(element),
    alignItems:
      style.vertical_align === 'middle'
        ? 'center'
        : style.vertical_align === 'bottom'
          ? 'flex-end'
          : 'flex-start',
    color: style.color || '#111827',
    display: element.visible === false ? 'none' : 'flex',
    fontFamily: style.font_family || 'Arial, Helvetica, sans-serif',
    fontSize: toCssFontSize(style.font_size),
    fontStyle: style.font_style || 'normal',
    fontWeight: style.font_weight || 400,
    justifyContent:
      style.text_align === 'center'
        ? 'center'
        : style.text_align === 'right'
          ? 'flex-end'
          : 'flex-start',
    lineHeight: style.line_height || 1.25,
    overflow: style.overflow || 'hidden',
    textAlign: style.text_align || 'left',
    whiteSpace: 'pre-wrap',
    wordBreak: 'break-word',
  };
}

function SelectionHandles({ visible }) {
  if (!visible) {
    return null;
  }

  return (
    <>
      <span className="mde-selection-handle is-top-left" aria-hidden="true" />
      <span className="mde-selection-handle is-top-right" aria-hidden="true" />
      <span className="mde-selection-handle is-bottom-left" aria-hidden="true" />
      <span className="mde-selection-handle is-bottom-right" aria-hidden="true" />
    </>
  );
}

function createDragHandler({
  element,
  page,
  zoom,
  onSelectElement,
  onMoveElement,
}) {
  return (event) => {
    if (event.button !== 0) {
      return;
    }

    event.stopPropagation();
    onSelectElement?.(element.id);

    if (element.locked || !onMoveElement) {
      return;
    }

    event.preventDefault();

    const startClientX = event.clientX;
    const startClientY = event.clientY;
    const startX = Number(element.x) || 0;
    const startY = Number(element.y) || 0;
    const safeZoom = Math.max(0.01, Number(zoom) || 1);

    const maxX = Math.max(0, Number(page.width) - Number(element.width || 0));
    const maxY = Math.max(0, Number(page.height) - Number(element.height || 0));

    function handlePointerMove(pointerEvent) {
      const deltaXmm = pxToMm((pointerEvent.clientX - startClientX) / safeZoom);
      const deltaYmm = pxToMm((pointerEvent.clientY - startClientY) / safeZoom);

      const nextX = Math.min(maxX, Math.max(0, startX + deltaXmm));
      const nextY = Math.min(maxY, Math.max(0, startY + deltaYmm));

      onMoveElement(element.id, {
        x: Number(nextX.toFixed(2)),
        y: Number(nextY.toFixed(2)),
      });
    }

    function handlePointerUp() {
      window.removeEventListener('pointermove', handlePointerMove);
      window.removeEventListener('pointerup', handlePointerUp);
      window.removeEventListener('pointercancel', handlePointerUp);
      document.body.classList.remove('is-mde-dragging');
    }

    document.body.classList.add('is-mde-dragging');
    window.addEventListener('pointermove', handlePointerMove);
    window.addEventListener('pointerup', handlePointerUp);
    window.addEventListener('pointercancel', handlePointerUp);
  };
}

function getInteractiveProps({
  element,
  page,
  zoom,
  isSelected,
  onSelectElement,
  onMoveElement,
}) {
  return {
    className: `mde-preview-object${isSelected ? ' is-selected' : ''}${
      element.locked ? ' is-locked' : ''
    }`,
    'data-object-id': element.id,
    'data-object-type': element.type,
    role: 'button',
    tabIndex: 0,
    'aria-pressed': isSelected,
    'aria-label': `${element.type}: ${element.id}`,
    onClick: (event) => {
      event.stopPropagation();
      onSelectElement?.(element.id);
    },
    onPointerDown: createDragHandler({
      element,
      page,
      zoom,
      onSelectElement,
      onMoveElement,
    }),
    onKeyDown: (event) => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        event.stopPropagation();
        onSelectElement?.(element.id);
      }
    },
  };
}

function TextObject(props) {
  const { element, content, isSelected } = props;
  const interactiveProps = getInteractiveProps(props);

  return (
    <div
      {...interactiveProps}
      className={`${interactiveProps.className} mde-preview-object--text`}
      style={buildTextStyle(element)}
    >
      {String(content ?? '')}
      <SelectionHandles visible={isSelected} />
    </div>
  );
}

function ImageObject(props) {
  const { element, isSelected } = props;
  const source =
    element.source_type === 'asset'
      ? ASSET_REGISTRY[element.source]
      : null;

  const style = {
    ...buildCommonElementStyle(element),
    alignItems: 'center',
    display: element.visible === false ? 'none' : 'flex',
    justifyContent: 'center',
    opacity: Number.isFinite(Number(element.opacity))
      ? Number(element.opacity)
      : 1,
    overflow: 'visible',
  };

  const interactiveProps = getInteractiveProps(props);

  if (!source) {
    return (
      <div
        {...interactiveProps}
        className={`${interactiveProps.className} mde-preview-object--missing`}
        style={style}
      >
        Imagen no disponible
        <SelectionHandles visible={isSelected} />
      </div>
    );
  }

  return (
    <div
      {...interactiveProps}
      className={`${interactiveProps.className} mde-preview-object--image`}
      style={style}
    >
      <img
        src={source}
        alt={element.metadata?.alt || element.id}
        draggable="false"
        style={{
          width: '100%',
          height: '100%',
          display: 'block',
          objectFit: element.fit || 'contain',
          pointerEvents: 'none',
        }}
      />
      <SelectionHandles visible={isSelected} />
    </div>
  );
}

function LineObject(props) {
  const { element, isSelected } = props;
  const isVertical = element.direction === 'vertical';
  const strokeWidth = Math.max(
    1,
    mmToPx(Number(element.stroke_width) || 0.3),
  );

  const interactiveProps = getInteractiveProps(props);

  return (
    <div
      {...interactiveProps}
      className={`${interactiveProps.className} mde-preview-object--line`}
      style={{
        ...buildCommonElementStyle(element),
        display: element.visible === false ? 'none' : 'block',
        overflow: 'visible',
      }}
    >
      <div
        style={
          isVertical
            ? {
                borderLeft: `${strokeWidth}px ${element.stroke_style || 'solid'} ${element.stroke_color || '#111827'}`,
                height: '100%',
                width: 0,
              }
            : {
                borderTop: `${strokeWidth}px ${element.stroke_style || 'solid'} ${element.stroke_color || '#111827'}`,
                height: 0,
                width: '100%',
              }
        }
      />
      <SelectionHandles visible={isSelected} />
    </div>
  );
}

function RectangleObject(props) {
  const { element, isSelected } = props;
  const style = element.style || {};
  const interactiveProps = getInteractiveProps(props);

  return (
    <div
      {...interactiveProps}
      className={`${interactiveProps.className} mde-preview-object--rectangle`}
      style={{
        ...buildCommonElementStyle(element),
        background: style.background || 'transparent',
        border: `${Math.max(
          1,
          mmToPx(Number(style.stroke_width) || 0.3),
        )}px ${style.stroke_style || 'solid'} ${style.stroke_color || '#111827'}`,
        borderRadius: `${mmToPx(Number(style.border_radius) || 0)}px`,
        overflow: 'visible',
      }}
    >
      <SelectionHandles visible={isSelected} />
    </div>
  );
}

function SignatureLineObject(props) {
  const { element, isSelected } = props;
  const style = element.style || {};
  const label = element.label || 'Firma';
  const interactiveProps = getInteractiveProps(props);

  return (
    <div
      {...interactiveProps}
      className={`${interactiveProps.className} mde-preview-object--signature`}
      style={{
        ...buildCommonElementStyle(element),
        alignItems: 'stretch',
        display: element.visible === false ? 'none' : 'flex',
        flexDirection: 'column',
        justifyContent: 'flex-end',
        fontFamily: style.font_family || 'Arial, Helvetica, sans-serif',
        fontSize: toCssFontSize(style.font_size || 9),
        color: style.color || '#111827',
        textAlign: style.text_align || 'center',
        overflow: 'visible',
      }}
    >
      <div className="mde-preview-signature-space" style={{ flex: 1, minHeight: 0 }} />

      <div
        className="mde-preview-signature-rule"
        style={{
          borderTop: `${Math.max(
            1,
            mmToPx(Number(style.stroke_width) || 0.4),
          )}px solid ${style.stroke_color || '#111827'}`,
          marginBottom: '4px',
          width: '100%',
        }}
      />

      <strong>{label}</strong>

      {element.show_name ? (
        <span className="mde-preview-signature-meta">Nombre</span>
      ) : null}

      {element.show_position ? (
        <span className="mde-preview-signature-meta">Puesto</span>
      ) : null}

      {element.show_date ? (
        <span className="mde-preview-signature-meta">Fecha</span>
      ) : null}

      <SelectionHandles visible={isSelected} />
    </div>
  );
}

function UnsupportedObject(props) {
  const { element, isSelected } = props;
  const interactiveProps = getInteractiveProps(props);

  return (
    <div
      {...interactiveProps}
      className={`${interactiveProps.className} mde-preview-object--missing`}
      style={{
        ...buildCommonElementStyle(element),
        overflow: 'visible',
      }}
    >
      Tipo no renderizado: {element.type}
      <SelectionHandles visible={isSelected} />
    </div>
  );
}

function PreviewObject({
  element,
  page,
  definition,
  data,
  zoom,
  selectedElementId,
  onSelectElement,
  onMoveElement,
}) {
  const commonProps = {
    element,
    page,
    zoom,
    isSelected: selectedElementId === element.id,
    onSelectElement,
    onMoveElement,
  };

  switch (element.type) {
    case 'text':
      return <TextObject {...commonProps} content={element.content || ''} />;

    case 'document-code':
    case 'document-revision':
      return (
        <TextObject
          {...commonProps}
          content={resolveBindingValue(element, definition, data)}
        />
      );

    case 'image':
      return <ImageObject {...commonProps} />;

    case 'line':
      return <LineObject {...commonProps} />;

    case 'rectangle':
      return <RectangleObject {...commonProps} />;

    case 'signature-line':
      return <SignatureLineObject {...commonProps} />;

    default:
      return <UnsupportedObject {...commonProps} />;
  }
}

function DocumentPage({
  page,
  definition,
  data,
  zoom,
  selectedElementId,
  onSelectElement,
  onMoveElement,
  onClearSelection,
}) {
  const widthPx = mmToPx(page.width);
  const heightPx = mmToPx(page.height);

  const marginStyle = {
    top: mmToPx(page.margins?.top || 0),
    right: mmToPx(page.margins?.right || 0),
    bottom: mmToPx(page.margins?.bottom || 0),
    left: mmToPx(page.margins?.left || 0),
  };

  return (
    <div
      className="mde-preview-page-frame"
      style={{
        width: `${widthPx * zoom}px`,
        height: `${heightPx * zoom}px`,
      }}
    >
      <article
        className="mde-preview-page"
        data-page-id={page.id}
        style={{
          width: `${widthPx}px`,
          height: `${heightPx}px`,
          background: page.background || '#ffffff',
          transform: `scale(${zoom})`,
          transformOrigin: 'top left',
        }}
        onClick={(event) => {
          if (event.target === event.currentTarget) {
            onClearSelection?.();
          }
        }}
      >
        {definition.document?.show_guides ? (
          <div
            className="mde-preview-page-margins"
            aria-hidden="true"
            style={{
              top: `${marginStyle.top}px`,
              right: `${marginStyle.right}px`,
              bottom: `${marginStyle.bottom}px`,
              left: `${marginStyle.left}px`,
            }}
          />
        ) : null}

        {[...(page.objects || [])]
          .sort(
            (left, right) =>
              (Number(left.z_index) || 0) - (Number(right.z_index) || 0),
          )
          .map((element) => (
            <PreviewObject
              key={element.id}
              element={element}
              page={page}
              definition={definition}
              data={data}
              zoom={zoom}
              selectedElementId={selectedElementId}
              onSelectElement={onSelectElement}
              onMoveElement={onMoveElement}
            />
          ))}
      </article>
    </div>
  );
}

export default function DocumentPreviewRenderer({
  definition,
  data = {},
  zoom = 1,
  showValidation = true,
  selectedElementId = null,
  onSelectElement,
  onMoveElement,
  onClearSelection,
}) {
  const normalizedDefinition = normalizeDocumentDefinition(definition);
  const validation = validateDocumentDefinition(normalizedDefinition);
  const safeZoom = Math.min(2, Math.max(0.25, Number(zoom) || 1));

  return (
    <section className="mde-preview-renderer">
      {showValidation &&
      (validation.errors.length || validation.warnings.length) ? (
        <div
          className={`mde-preview-validation ${
            validation.valid ? 'is-warning' : 'is-error'
          }`}
        >
          <strong>
            {validation.valid
              ? 'Advertencias de definición'
              : 'Errores de definición'}
          </strong>

          {validation.errors.length ? (
            <ul>
              {validation.errors.map((error) => (
                <li key={`error-${error}`}>{error}</li>
              ))}
            </ul>
          ) : null}

          {validation.warnings.length ? (
            <ul>
              {validation.warnings.map((warning) => (
                <li key={`warning-${warning}`}>{warning}</li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}

      <div className="mde-preview-pages">
        {normalizedDefinition.pages.map((page) => (
          <DocumentPage
            key={page.id}
            page={page}
            definition={normalizedDefinition}
            data={data}
            zoom={safeZoom}
            selectedElementId={selectedElementId}
            onSelectElement={onSelectElement}
            onMoveElement={onMoveElement}
            onClearSelection={onClearSelection}
          />
        ))}
      </div>
    </section>
  );
}
