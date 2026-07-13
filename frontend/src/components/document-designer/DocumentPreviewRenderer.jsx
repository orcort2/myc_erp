import mycLogo from '../../assets/myc-logo.png';

import {
  mmToPx,
  normalizeDocumentDefinition,
  pxToMm,
  validateDocumentDefinition,
} from './documentDesignerModel.js';
import { clampObjectPosition } from './documentCanvasEngine.js';

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
      <span className="mde-selection-indicator" aria-hidden="true">Seleccionado</span>
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
  isSelected,
  onSelectElement,
  onMoveStart,
  onMoveElement,
  onMoveEnd,
}) {
  return (event) => {
    if (event.button !== 0) {
      return;
    }

    event.stopPropagation();
    const additive = event.metaKey || event.ctrlKey || event.shiftKey;
    const preserveSelectionForDrag = isSelected && !additive;
    if (!preserveSelectionForDrag) {
      onSelectElement?.(element.id, page.id, { additive });
    }

    if (additive) {
      return;
    }

    if (element.locked || !onMoveElement) {
      if (preserveSelectionForDrag) {
        onSelectElement?.(element.id, page.id, { additive: false });
      }
      return;
    }

    event.preventDefault();

    const startClientX = event.clientX;
    const startClientY = event.clientY;
    const startX = Number(element.x) || 0;
    const startY = Number(element.y) || 0;
    const safeZoom = Math.max(0.01, Number(zoom) || 1);
    let didMove = false;
    onMoveStart?.(element.id, page.id);

    function handlePointerMove(pointerEvent) {
      if (Math.abs(pointerEvent.clientX - startClientX) + Math.abs(pointerEvent.clientY - startClientY) >= 2) {
        didMove = true;
      }
      const deltaXmm = pxToMm((pointerEvent.clientX - startClientX) / safeZoom);
      const deltaYmm = pxToMm((pointerEvent.clientY - startClientY) / safeZoom);
      const nextPosition = clampObjectPosition(page, element, {
        x: startX + deltaXmm,
        y: startY + deltaYmm,
      });

      onMoveElement(element.id, {
        x: nextPosition.x,
        y: nextPosition.y,
      }, {
        deltaX: deltaXmm,
        deltaY: deltaYmm,
        pageId: page.id,
        moveSelection: isSelected,
      });
    }

    function handlePointerUp() {
      window.removeEventListener('pointermove', handlePointerMove);
      window.removeEventListener('pointerup', handlePointerUp);
      window.removeEventListener('pointercancel', handlePointerUp);
      document.body.classList.remove('is-mde-dragging');
      onMoveEnd?.(element.id, page.id);
      if (!didMove && preserveSelectionForDrag) {
        onSelectElement?.(element.id, page.id, { additive: false });
      }
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
  onMoveStart,
  onMoveElement,
  onMoveEnd,
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
    },
    onPointerDown: createDragHandler({
      element,
      page,
      zoom,
      isSelected,
      onSelectElement,
      onMoveStart,
      onMoveElement,
      onMoveEnd,
    }),
    onKeyDown: (event) => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        event.stopPropagation();
        onSelectElement?.(element.id, page.id, { additive: event.metaKey || event.ctrlKey || event.shiftKey });
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

const SAMPLE_FIELDS = {
  'client-data': [
    ['showTradeName', 'Nombre comercial', 'Cliente de ejemplo'], ['showBusinessName', 'Razón social', 'Cliente MYC, S.A. de C.V.'], ['showRfc', 'RFC', 'XAXX010101000'], ['showAddress', 'Domicilio', 'Domicilio de ejemplo'], ['showContact', 'Contacto', 'Persona de contacto'], ['showEmail', 'Correo', 'cliente@ejemplo.com'],
  ],
  'equipment-data': [
    ['showInstrument', 'Instrumento', 'Instrumento de ejemplo'], ['showBrand', 'Marca', 'Marca ejemplo'], ['showModel', 'Modelo', 'Modelo 000'], ['showSerial', 'Serie', 'SN-0000'], ['showInternalId', 'ID interno', 'MYC-0000'], ['showLocation', 'Ubicación', 'Laboratorio'], ['showResolution', 'División mínima', '0.01'],
  ],
  'service-data': [
    ['showEtsFolio', 'ETS', 'ETS-0000'], ['showWorkOrderFolio', 'OT', 'OT-0000'], ['showCertificateFolio', 'Certificado', 'MYC-0000'], ['showServiceType', 'Servicio', 'Calibración'], ['showServiceDate', 'Fecha', '13/07/2026'], ['showNextCalibration', 'Próxima calibración', 'Julio 2027'],
  ],
  'personnel-data': [
    ['showTechnician', 'Técnico', 'Técnico de ejemplo'], ['showCaptureResponsible', 'Captura', 'Responsable de captura'], ['showQualityResponsible', 'Calidad', 'Responsable de calidad'], ['showAdvisor', 'Asesor', 'Asesor de ejemplo'],
  ],
  'environmental-conditions': [
    ['showTemperature', 'Temperatura', '23.0 °C'], ['showHumidity', 'Humedad', '45 %HR'], ['showPressure', 'Presión', '101.3 kPa'], ['showInitialCondition', 'Condición inicial', 'Estable'], ['showFinalCondition', 'Condición final', 'Estable'],
  ],
};

function BlockShell(props, children, extraStyle = {}) {
  const { element, isSelected } = props;
  const interactiveProps = getInteractiveProps(props);
  return (
    <div
      {...interactiveProps}
      className={`${interactiveProps.className} mde-preview-object--myc-block`}
      style={{
        ...buildCommonElementStyle(element),
        display: element.visible === false ? 'none' : 'flex',
        flexDirection: 'column',
        fontFamily: 'Arial, Helvetica, sans-serif',
        fontSize: '10px',
        overflow: 'hidden',
        ...extraStyle,
      }}
    >
      {children}
      <SelectionHandles visible={isSelected} />
    </div>
  );
}

function SampleFields({ element }) {
  const fields = (SAMPLE_FIELDS[element.type] || []).filter(([flag]) => element.props?.[flag]);
  return (
    <>
      <strong className="mde-myc-block-title">{element.label}</strong>
      <div className="mde-myc-fields">
        {fields.map(([flag, label, value]) => <span key={flag}><b>{label}</b><em>{value}</em></span>)}
      </div>
    </>
  );
}

function ExampleTable({ title, headers, rows = 2, showBorders = true }) {
  const safeHeaders = headers?.length ? headers : ['Columna 1'];
  return (
    <div className={`mde-myc-table${showBorders ? ' has-borders' : ''}`}>
      {title ? <strong>{title}</strong> : null}
      <div className="mde-myc-table-row is-header" style={{ gridTemplateColumns: `repeat(${safeHeaders.length}, minmax(0, 1fr))` }}>{safeHeaders.map((header, index) => <span key={`${header}-${index}`}>{header}</span>)}</div>
      {Array.from({ length: rows }, (_, row) => <div className="mde-myc-table-row" style={{ gridTemplateColumns: `repeat(${safeHeaders.length}, minmax(0, 1fr))` }} key={row}>{safeHeaders.map((_, column) => <span key={column}>Dato {row + 1}.{column + 1}</span>)}</div>)}
    </div>
  );
}

function Signatures({ element, labels }) {
  const props = element.props || {};
  return (
    <><strong className="mde-myc-block-title">{props.title}</strong><div className="mde-myc-signatures">{labels.map((label) => <div key={label}><span className="mde-myc-signature-rule" /><b>{label}</b>{props.showNames ? <small>Nombre de ejemplo</small> : null}{props.showPositions ? <small>Puesto</small> : null}{props.showDates ? <small>Fecha</small> : null}</div>)}</div></>
  );
}

function MycBlockObject(componentProps) {
  const { element } = componentProps;
  const props = element.props || {};

  if (SAMPLE_FIELDS[element.type]) return BlockShell(componentProps, <SampleFields element={element} />);

  switch (element.type) {
    case 'myc-header':
      return BlockShell(componentProps, <div className="mde-myc-header">{props.showLogo ? <img src={mycLogo} alt="MYC" /> : null}<div>{props.showBusinessName ? <strong>METROLOGÍA Y SERVICIOS MYC</strong> : null}<b>{props.documentTitle}</b>{props.showAddress ? <small>Domicilio institucional de ejemplo</small> : null}{props.showContact ? <small>contacto@myc.example</small> : null}</div>{props.showAccreditation ? <span>Acreditación</span> : null}</div>);
    case 'myc-footer':
      return BlockShell(componentProps, <div className="mde-myc-footer"><div>{props.showBusinessName ? <b>Metrología y Servicios MYC</b> : null}{props.showAddress ? <span>Domicilio institucional</span> : null}{props.showPhones ? <span>Tel. 000 000 0000</span> : null}{props.showWebsite ? <span>www.myc.example</span> : null}</div>{props.showPagination ? <strong>Página 1 de 1</strong> : null}</div>);
    case 'editable-table':
      return BlockShell(componentProps, <ExampleTable title={props.title} headers={(props.headers || []).slice(0, props.columns)} rows={props.initialRows} showBorders={props.showBorders} />);
    case 'results': {
      const optionalHeaders = [props.showUnit && 'Unidad', props.showReference && 'Referencia', props.showResult && 'Resultado', props.showObservation && 'Observación'].filter(Boolean);
      const headers = (props.headers?.length ? props.headers : ['Punto', ...optionalHeaders]).slice(0, props.columns);
      return BlockShell(componentProps, <ExampleTable title={props.title} headers={headers} rows={2} showBorders />);
    }
    case 'observations':
      return BlockShell(componentProps, <><strong className="mde-myc-block-title">{props.title}</strong><p className="mde-myc-observations">{props.initialText}</p>{Array.from({ length: Math.max(0, props.lines - 1) }, (_, index) => <span className="mde-myc-writing-line" key={index} />)}</>);
    case 'signature-single':
      return BlockShell(componentProps, <Signatures element={element} labels={[props.signerLabel]} />);
    case 'signature-double':
      return BlockShell(componentProps, <Signatures element={element} labels={[props.leftLabel, props.rightLabel]} />);
    case 'signature-triple':
      return BlockShell(componentProps, <Signatures element={element} labels={[props.leftLabel, props.centerLabel, props.rightLabel]} />);
    case 'document-code':
      return BlockShell(componentProps, <div style={{ textAlign: props.align }}><b>{props.showLabel ? 'Código: ' : ''}</b>{props.code}</div>, { justifyContent: 'center' });
    case 'document-revision':
      return BlockShell(componentProps, <div><b>Revisión: </b>{props.revision}{props.showRevisionDate ? <small> · {props.revisionDate}</small> : null}</div>, { justifyContent: 'center' });
    case 'pagination':
      return BlockShell(componentProps, <div style={{ textAlign: props.align }}>{props.format}</div>, { justifyContent: 'center' });
    case 'qr-code':
      return BlockShell(componentProps, <div className="mde-myc-qr"><span style={{ width: props.size, height: props.size }}>QR</span><small>{props.label}</small></div>, { alignItems: 'center' });
    case 'authentication':
      return BlockShell(componentProps, <div className="mde-myc-auth"><strong>{props.text}</strong><span>Folio: {props.folio}</span>{props.showVerificationCode ? <code>VERIF-MYC-0000</code> : null}<small>{props.url}</small></div>);
    case 'title':
      return BlockShell(componentProps, <div style={{ textAlign: props.align, fontSize: toCssFontSize(props.fontSize), fontWeight: props.bold ? 700 : 400 }}>{props.text}</div>, { justifyContent: 'center' });
    case 'text':
      return BlockShell(componentProps, <div style={{ textAlign: props.align, fontSize: toCssFontSize(props.fontSize), fontWeight: props.bold ? 700 : 400, fontStyle: props.italic ? 'italic' : 'normal' }}>{props.text}</div>);
    case 'image':
      return BlockShell(componentProps, props.url ? <img className="mde-myc-user-image" src={props.url} alt={props.alt} style={{ width: `${props.imageWidth}mm`, alignSelf: props.align === 'right' ? 'flex-end' : props.align === 'center' ? 'center' : 'flex-start' }} /> : <div className="mde-myc-image-placeholder">Imagen de ejemplo<br /><small>{props.alt}</small></div>);
    case 'divider':
      return BlockShell(componentProps, <span style={{ borderTop: `${props.thickness}px ${props.lineStyle} #344054`, marginTop: `${props.spacingTop}px`, marginBottom: `${props.spacingBottom}px`, width: '100%' }} />, { justifyContent: 'center' });
    case 'spacer':
      return BlockShell(componentProps, <span className="mde-myc-spacer">Espaciador · {props.height} mm</span>, { justifyContent: 'center' });
    default:
      return <UnsupportedObject {...componentProps} />;
  }
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
  selectedObjectIds,
  onSelectElement,
  onMoveStart,
  onMoveElement,
  onMoveEnd,
}) {
  const commonProps = {
    element,
    page,
    zoom,
    isSelected: selectedObjectIds.includes(element.id),
    onSelectElement,
    onMoveStart,
    onMoveElement,
    onMoveEnd,
  };

  if (element.props) {
    return <MycBlockObject {...commonProps} />;
  }

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
  selectedObjectIds,
  activePageId,
  onSelectElement,
  onMoveStart,
  onMoveElement,
  onMoveEnd,
  onClearSelection,
  onActivatePage,
}) {
  const widthPx = mmToPx(page.width);
  const heightPx = mmToPx(page.height);

  const marginStyle = {
    top: mmToPx(page.margins?.top || 0),
    right: mmToPx(page.margins?.right || 0),
    bottom: mmToPx(page.margins?.bottom || 0),
    left: mmToPx(page.margins?.left || 0),
  };
  const selectedObjects = (page.objects || []).filter((object) => selectedObjectIds.includes(object.id));
  const groupBounds = selectedObjects.length > 1 ? {
    left: Math.min(...selectedObjects.map((object) => Number(object.x) || 0)),
    top: Math.min(...selectedObjects.map((object) => Number(object.y) || 0)),
    right: Math.max(...selectedObjects.map((object) => (Number(object.x) || 0) + (Number(object.width) || 0))),
    bottom: Math.max(...selectedObjects.map((object) => (Number(object.y) || 0) + (Number(object.height) || 0))),
  } : null;

  return (
    <div
      className={`mde-preview-page-frame${activePageId === page.id ? ' is-active' : ''}`}
      style={{
        width: `${widthPx * zoom}px`,
        height: `${heightPx * zoom}px`,
      }}
    >
      <article
        className={`mde-preview-page${selectedObjects.length > 1 ? ' has-multi-selection' : ''}`}
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
            onActivatePage?.(page.id);
            onClearSelection?.(page.id);
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

        {groupBounds ? (
          <div
            className="mde-selection-group-outline"
            aria-hidden="true"
            style={{
              left: `${mmToPx(groupBounds.left)}px`,
              top: `${mmToPx(groupBounds.top)}px`,
              width: `${mmToPx(groupBounds.right - groupBounds.left)}px`,
              height: `${mmToPx(groupBounds.bottom - groupBounds.top)}px`,
            }}
          >
            <span>{selectedObjects.length} objetos</span>
          </div>
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
              selectedObjectIds={selectedObjectIds}
              onSelectElement={onSelectElement}
              onMoveStart={onMoveStart}
              onMoveElement={onMoveElement}
              onMoveEnd={onMoveEnd}
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
  selectedObjectIds = null,
  activePageId = null,
  onSelectElement,
  onMoveStart,
  onMoveElement,
  onMoveEnd,
  onClearSelection,
  onActivatePage,
}) {
  const normalizedDefinition = normalizeDocumentDefinition(definition);
  const validation = validateDocumentDefinition(normalizedDefinition);
  const safeZoom = Math.min(2, Math.max(0.25, Number(zoom) || 1));
  const selectedIds = Array.isArray(selectedObjectIds)
    ? selectedObjectIds
    : selectedElementId ? [selectedElementId] : [];

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
            selectedObjectIds={selectedIds}
            activePageId={activePageId}
            onSelectElement={onSelectElement}
            onMoveStart={onMoveStart}
            onMoveElement={onMoveElement}
            onMoveEnd={onMoveEnd}
            onClearSelection={onClearSelection}
            onActivatePage={onActivatePage}
          />
        ))}
      </div>
    </section>
  );
}
