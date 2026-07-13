import { useEffect, useMemo, useRef, useState } from 'react';

import ConfirmDialog from '../../components/ConfirmDialog.jsx';
import DocumentPreviewRenderer from '../../components/document-designer/DocumentPreviewRenderer.jsx';
import {
  calculateGroupMoveDelta,
  clampObjectPosition,
  duplicateDocumentPage,
  insertBlankPageAfter,
  insertObjectIntelligently,
  normalizeObjectGeometry,
  pasteObjectGroup,
  resizeDocumentPage,
} from '../../components/document-designer/documentCanvasEngine.js';
import {
  createDocumentBlock,
  createInitialTestDocument,
  DOCUMENT_BLOCK_LIBRARY,
  mmToPx,
} from '../../components/document-designer/documentDesignerModel.js';

import '../../components/document-designer/document-designer.css';

const MIN_ZOOM = 0.35;
const MAX_ZOOM = 1.5;
const ZOOM_STEP = 0.1;
const PAGE_SIZE_OPTIONS = [
  ['LETTER', 'Carta'],
  ['LEGAL', 'Oficio'],
  ['A4', 'A4'],
  ['A3', 'A3'],
  ['CUSTOM', 'Personalizado'],
];
const PAGE_SIZE_LABELS = Object.fromEntries(PAGE_SIZE_OPTIONS);
const ALIGN_OPTIONS = [['left', 'Izquierda'], ['center', 'Centro'], ['right', 'Derecha']];
const YES_NO = (items) => items.map(([key, label]) => ({ key, label, control: 'checkbox' }));

const PROPERTY_FIELDS = {
  'myc-header': [
    { key: 'documentTitle', label: 'Título del documento' },
    ...YES_NO([['showLogo', 'Mostrar logotipo'], ['showBusinessName', 'Mostrar razón social'], ['showAddress', 'Mostrar dirección'], ['showContact', 'Mostrar contacto'], ['showAccreditation', 'Mostrar acreditación']]),
  ],
  'myc-footer': YES_NO([['showBusinessName', 'Mostrar razón social'], ['showAddress', 'Mostrar dirección'], ['showPhones', 'Mostrar teléfonos'], ['showWebsite', 'Mostrar sitio web'], ['showPagination', 'Mostrar paginación']]),
  'client-data': YES_NO([['showTradeName', 'Mostrar nombre comercial'], ['showBusinessName', 'Mostrar razón social'], ['showRfc', 'Mostrar RFC'], ['showAddress', 'Mostrar domicilio'], ['showContact', 'Mostrar contacto'], ['showEmail', 'Mostrar correo']]),
  'equipment-data': YES_NO([['showInstrument', 'Mostrar instrumento'], ['showBrand', 'Mostrar marca'], ['showModel', 'Mostrar modelo'], ['showSerial', 'Mostrar número de serie'], ['showInternalId', 'Mostrar identificación interna'], ['showLocation', 'Mostrar ubicación'], ['showResolution', 'Mostrar división mínima']]),
  'service-data': YES_NO([['showEtsFolio', 'Mostrar folio de ETS'], ['showWorkOrderFolio', 'Mostrar folio de OT'], ['showCertificateFolio', 'Mostrar folio de certificado'], ['showServiceType', 'Mostrar tipo de servicio'], ['showServiceDate', 'Mostrar fecha del servicio'], ['showNextCalibration', 'Mostrar próxima calibración']]),
  'personnel-data': YES_NO([['showTechnician', 'Mostrar técnico'], ['showCaptureResponsible', 'Responsable de captura'], ['showQualityResponsible', 'Responsable de calidad'], ['showAdvisor', 'Mostrar asesor']]),
  'editable-table': [
    { key: 'title', label: 'Título de la tabla' },
    { key: 'columns', label: 'Número de columnas', control: 'number', min: 1, max: 12 },
    { key: 'headers', label: 'Encabezados (separados por coma)', control: 'headers' },
    { key: 'initialRows', label: 'Filas iniciales', control: 'number', min: 1, max: 20 },
    { key: 'showBorders', label: 'Mostrar bordes', control: 'checkbox' },
  ],
  'environmental-conditions': YES_NO([['showTemperature', 'Mostrar temperatura'], ['showHumidity', 'Mostrar humedad'], ['showPressure', 'Mostrar presión'], ['showInitialCondition', 'Mostrar condición inicial'], ['showFinalCondition', 'Mostrar condición final']]),
  results: [
    { key: 'title', label: 'Título' },
    { key: 'columns', label: 'Número de columnas', control: 'number', min: 1, max: 12 },
    { key: 'headers', label: 'Encabezados (separados por coma)', control: 'headers' },
    ...YES_NO([['showUnit', 'Mostrar unidad'], ['showReference', 'Mostrar referencia'], ['showResult', 'Mostrar resultado'], ['showObservation', 'Mostrar observación']]),
  ],
  observations: [{ key: 'title', label: 'Título' }, { key: 'initialText', label: 'Texto inicial', control: 'textarea' }, { key: 'lines', label: 'Número de líneas', control: 'number', min: 1, max: 12 }],
  'signature-single': [{ key: 'title', label: 'Título' }, { key: 'signerLabel', label: 'Etiqueta del firmante' }, ...YES_NO([['showNames', 'Mostrar nombre'], ['showPositions', 'Mostrar puesto'], ['showDates', 'Mostrar fecha']])],
  'signature-double': [{ key: 'title', label: 'Título' }, { key: 'leftLabel', label: 'Firmante izquierdo' }, { key: 'rightLabel', label: 'Firmante derecho' }, ...YES_NO([['showNames', 'Mostrar nombres'], ['showPositions', 'Mostrar puestos'], ['showDates', 'Mostrar fechas']])],
  'signature-triple': [{ key: 'title', label: 'Título' }, { key: 'leftLabel', label: 'Firmante izquierdo' }, { key: 'centerLabel', label: 'Firmante central' }, { key: 'rightLabel', label: 'Firmante derecho' }, ...YES_NO([['showNames', 'Mostrar nombres'], ['showPositions', 'Mostrar puestos'], ['showDates', 'Mostrar fechas']])],
  'document-code': [{ key: 'code', label: 'Código' }, { key: 'showLabel', label: 'Mostrar etiqueta', control: 'checkbox' }, { key: 'align', label: 'Alineación', control: 'select', options: ALIGN_OPTIONS }],
  'document-revision': [{ key: 'revision', label: 'Número o código de revisión' }, { key: 'showRevisionDate', label: 'Mostrar fecha de revisión', control: 'checkbox' }, { key: 'revisionDate', label: 'Fecha', control: 'date' }],
  pagination: [{ key: 'format', label: 'Formato', control: 'select', options: [['Página 1 de 3', 'Página 1 de 3'], ['1 / 3', '1 / 3'], ['Página 1', 'Página 1']] }, { key: 'align', label: 'Alineación', control: 'select', options: ALIGN_OPTIONS }],
  'qr-code': [{ key: 'content', label: 'Contenido', control: 'textarea' }, { key: 'size', label: 'Tamaño', control: 'number', min: 16, max: 80 }, { key: 'label', label: 'Etiqueta' }],
  authentication: [{ key: 'text', label: 'Texto' }, { key: 'folio', label: 'Folio' }, { key: 'url', label: 'URL' }, { key: 'showVerificationCode', label: 'Mostrar código de verificación', control: 'checkbox' }],
  title: [{ key: 'text', label: 'Contenido' }, { key: 'level', label: 'Nivel visual', control: 'select', options: [[1, 'Nivel 1'], [2, 'Nivel 2'], [3, 'Nivel 3']] }, { key: 'align', label: 'Alineación', control: 'select', options: ALIGN_OPTIONS }, { key: 'bold', label: 'Negrita', control: 'checkbox' }, { key: 'fontSize', label: 'Tamaño', control: 'number', min: 8, max: 72 }],
  text: [{ key: 'text', label: 'Contenido', control: 'textarea' }, { key: 'align', label: 'Alineación', control: 'select', options: ALIGN_OPTIONS }, { key: 'bold', label: 'Negrita', control: 'checkbox' }, { key: 'italic', label: 'Cursiva', control: 'checkbox' }, { key: 'fontSize', label: 'Tamaño', control: 'number', min: 6, max: 72 }],
  image: [{ key: 'url', label: 'URL o ruta' }, { key: 'alt', label: 'Texto alternativo' }, { key: 'imageWidth', label: 'Ancho', control: 'number', min: 10, max: 180 }, { key: 'align', label: 'Alineación', control: 'select', options: ALIGN_OPTIONS }],
  divider: [{ key: 'thickness', label: 'Grosor', control: 'number', min: 1, max: 10 }, { key: 'lineStyle', label: 'Estilo de línea', control: 'select', options: [['solid', 'Sólida'], ['dashed', 'Discontinua'], ['dotted', 'Punteada']] }, { key: 'spacingTop', label: 'Espaciado superior', control: 'number', min: 0, max: 30 }, { key: 'spacingBottom', label: 'Espaciado inferior', control: 'number', min: 0, max: 30 }],
  spacer: [{ key: 'height', label: 'Altura', control: 'number', min: 1, max: 100 }],
};

function clampZoom(value) {
  return Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, value));
}

function findElementLocation(definition, elementId) {
  for (let pageIndex = 0; pageIndex < (definition.pages || []).length; pageIndex += 1) {
    const objectIndex = (definition.pages[pageIndex].objects || []).findIndex((item) => item.id === elementId);
    if (objectIndex >= 0) return { pageIndex, objectIndex };
  }
  return null;
}

function findElementById(definition, elementId) {
  const location = elementId ? findElementLocation(definition, elementId) : null;
  return location ? definition.pages[location.pageIndex].objects[location.objectIndex] : null;
}

function updateElementById(definition, elementId, updater) {
  return {
    ...definition,
    pages: (definition.pages || []).map((page) => ({
      ...page,
      objects: (page.objects || []).map((element) => element.id === elementId ? updater(element, page) : element),
    })),
  };
}

function deepCopy(value) {
  return typeof structuredClone === 'function' ? structuredClone(value) : JSON.parse(JSON.stringify(value));
}

function PropertyControl({ field, value, onChange }) {
  if (field.control === 'checkbox') {
    return <label className="document-inspector-check"><input type="checkbox" checked={Boolean(value)} onChange={(event) => onChange(event.target.checked)} /><span>{field.label}</span></label>;
  }

  const className = `document-inspector-field${field.control === 'textarea' || field.control === 'headers' ? ' document-inspector-field--full' : ''}`;
  if (field.control === 'textarea') return <label className={className}><span>{field.label}</span><textarea value={value ?? ''} onChange={(event) => onChange(event.target.value)} /></label>;
  if (field.control === 'select') return <label className={className}><span>{field.label}</span><select value={value ?? ''} onChange={(event) => onChange(event.target.value)}>{field.options.map(([optionValue, label]) => <option key={optionValue} value={optionValue}>{label}</option>)}</select></label>;
  if (field.control === 'headers') return <label className={className}><span>{field.label}</span><input value={(value || []).join(', ')} onChange={(event) => onChange(event.target.value.split(',').map((item) => item.trim()))} /></label>;
  return <label className={className}><span>{field.label}</span><input type={field.control === 'number' ? 'number' : field.control === 'date' ? 'date' : 'text'} value={value ?? ''} min={field.min} max={field.max} onChange={(event) => onChange(field.control === 'number' ? Number(event.target.value) : event.target.value)} /></label>;
}

function NumberField({ label, value, onChange, step = 1 }) {
  return <label className="document-inspector-field"><span>{label}</span><input type="number" value={value} step={step} onChange={(event) => onChange(Number(event.target.value))} /></label>;
}

export default function DocumentDesignerLabPage() {
  const canvasAreaRef = useRef(null);
  const clipboardRef = useRef(null);
  const dragSelectionRef = useRef(null);
  const [documentDefinition, setDocumentDefinition] = useState(() => createInitialTestDocument());
  const [activePageId, setActivePageId] = useState(() => createInitialTestDocument().pages[0].id);
  const [selectedObjectIds, setSelectedObjectIds] = useState([]);
  const [clipboardVersion, setClipboardVersion] = useState(0);
  const [pageToDelete, setPageToDelete] = useState(null);
  const [editorNotice, setEditorNotice] = useState('');
  const [zoom, setZoom] = useState(0.82);

  const selectedElementId = selectedObjectIds[selectedObjectIds.length - 1] || null;
  const selectedElement = useMemo(() => findElementById(documentDefinition, selectedElementId), [documentDefinition, selectedElementId]);
  const selectedLocation = useMemo(() => selectedElementId ? findElementLocation(documentDefinition, selectedElementId) : null, [documentDefinition, selectedElementId]);
  const selectedFields = selectedElement?.props ? PROPERTY_FIELDS[selectedElement.type] || [] : [];
  const activePage = documentDefinition.pages.find((page) => page.id === activePageId) || documentDefinition.pages[0];
  const totalObjects = useMemo(() => documentDefinition.pages.reduce((total, page) => total + (page.objects || []).length, 0), [documentDefinition]);
  const hasClipboard = clipboardVersion >= 0 && Boolean(clipboardRef.current?.objects?.length);

  function selectedObjectsFrom(definition = documentDefinition) {
    const selectedIds = new Set(selectedObjectIds);
    return definition.pages.flatMap((page) => (page.objects || []).filter((object) => selectedIds.has(object.id)));
  }

  function updateSelectedElement(changes) {
    if (!selectedElementId || selectedObjectIds.length !== 1) return;
    setDocumentDefinition((current) => updateElementById(current, selectedElementId, (element, page) => {
      const nextElement = { ...element, ...changes };
      if (['x', 'y', 'width', 'height'].some((key) => Object.prototype.hasOwnProperty.call(changes, key))) {
        return { ...nextElement, ...normalizeObjectGeometry(page, nextElement) };
      }
      return nextElement;
    }));
  }

  function updateSelectedStyle(changes) {
    if (!selectedElementId || selectedObjectIds.length !== 1) return;
    setDocumentDefinition((current) => updateElementById(current, selectedElementId, (element) => ({ ...element, style: { ...(element.style || {}), ...changes } })));
  }

  function updateSelectedBlockProps(changes) {
    if (!selectedElementId || selectedObjectIds.length !== 1) return;
    setDocumentDefinition((current) => updateElementById(current, selectedElementId, (element) => ({ ...element, props: { ...(element.props || {}), ...changes } })));
  }

  function updateProperty(field, nextValue) {
    if (field.control === 'number') nextValue = Math.min(field.max ?? Infinity, Math.max(field.min ?? -Infinity, nextValue));
    if (field.key === 'columns') {
      const columns = Math.min(12, Math.max(1, nextValue));
      const headers = Array.from({ length: columns }, (_, index) => selectedElement.props.headers?.[index] || `Columna ${index + 1}`);
      updateSelectedBlockProps({ columns, headers });
      return;
    }
    updateSelectedBlockProps({ [field.key]: nextValue });
    if (selectedElement.type === 'spacer' && field.key === 'height') updateSelectedElement({ height: nextValue });
  }

  function handleAddBlock(type) {
    const block = createDocumentBlock(type);
    const result = insertObjectIntelligently(documentDefinition, block, { targetPageId: activePage?.id });
    setDocumentDefinition(result.definition);
    setActivePageId(result.block.page_id);
    setSelectedObjectIds([result.block.id]);
    setEditorNotice('');
  }

  function handleSelectObject(elementId, pageId, { additive = false } = {}) {
    setActivePageId(pageId);
    setSelectedObjectIds((current) => {
      if (!additive) return [elementId];
      const currentPageId = current.length ? documentDefinition.pages.find((page) => page.objects.some((object) => object.id === current[0]))?.id : pageId;
      if (currentPageId !== pageId) return [elementId];
      return current.includes(elementId) ? current.filter((id) => id !== elementId) : [...current, elementId];
    });
  }

  function handleMoveStart(elementId, pageId) {
    const page = documentDefinition.pages.find((item) => item.id === pageId);
    if (!page) return;
    const ids = selectedObjectIds.includes(elementId) ? selectedObjectIds : [elementId];
    dragSelectionRef.current = {
      pageId,
      objects: page.objects.filter((object) => ids.includes(object.id)).map(deepCopy),
    };
  }

  function handleMoveElement(elementId, position, movement = {}) {
    const snapshot = dragSelectionRef.current;
    if (snapshot?.pageId === movement.pageId && snapshot.objects.length > 1 && snapshot.objects.some((object) => object.id === elementId)) {
      setDocumentDefinition((current) => ({
        ...current,
        pages: current.pages.map((page) => {
          if (page.id !== snapshot.pageId) return page;
          const delta = calculateGroupMoveDelta(page, snapshot.objects, { x: movement.deltaX, y: movement.deltaY });
          const origins = new Map(snapshot.objects.map((object) => [object.id, object]));
          return {
            ...page,
            objects: page.objects.map((object) => {
              const origin = origins.get(object.id);
              return origin ? { ...object, x: Number((origin.x + delta.x).toFixed(2)), y: Number((origin.y + delta.y).toFixed(2)) } : object;
            }),
          };
        }),
      }));
      return;
    }
    setDocumentDefinition((current) => updateElementById(current, elementId, (element, page) => element.locked ? element : { ...element, ...clampObjectPosition(page, element, position) }));
  }

  function handleMoveEnd() {
    dragSelectionRef.current = null;
  }

  function handleReorder(direction) {
    if (!selectedLocation || selectedObjectIds.length !== 1) return;
    setDocumentDefinition((current) => {
      const location = findElementLocation(current, selectedElementId);
      if (!location) return current;
      const pages = current.pages.map((page, pageIndex) => {
        if (pageIndex !== location.pageIndex) return page;
        const objects = [...page.objects];
        const target = location.objectIndex + direction;
        if (target < 0 || target >= objects.length) return page;
        [objects[location.objectIndex], objects[target]] = [objects[target], objects[location.objectIndex]];
        return { ...page, objects: objects.map((item, index) => ({ ...item, z_index: index + 1 })) };
      });
      return { ...current, pages };
    });
  }

  function handleDuplicate() {
    const objects = selectedObjectsFrom();
    if (!objects.length || !activePage) return;
    const result = pasteObjectGroup(documentDefinition, deepCopy(objects), activePage.id);
    setDocumentDefinition(result.definition);
    setActivePageId(result.page.id);
    setSelectedObjectIds(result.objects.map((object) => object.id));
  }

  function handleDelete() {
    if (!selectedObjectIds.length) return;
    const ids = new Set(selectedObjectIds);
    setDocumentDefinition((current) => ({ ...current, pages: current.pages.map((page) => ({ ...page, objects: page.objects.filter((item) => !ids.has(item.id)) })) }));
    setSelectedObjectIds([]);
  }

  function handleCopy(mode = 'copy') {
    const objects = selectedObjectsFrom();
    if (!objects.length) return false;
    const sourceLocation = findElementLocation(documentDefinition, objects[0].id);
    clipboardRef.current = {
      mode,
      objects: deepCopy(objects),
      sourcePageId: sourceLocation ? documentDefinition.pages[sourceLocation.pageIndex].id : activePageId,
    };
    setClipboardVersion((current) => current + 1);
    return true;
  }

  function handleCut() {
    if (handleCopy('cut')) handleDelete();
  }

  function handlePaste() {
    if (!clipboardRef.current?.objects?.length || !activePage) return;
    try {
      const result = pasteObjectGroup(documentDefinition, clipboardRef.current.objects, activePage.id);
      setDocumentDefinition(result.definition);
      setActivePageId(result.page.id);
      setSelectedObjectIds(result.objects.map((object) => object.id));
      clipboardRef.current = { ...clipboardRef.current, mode: 'copy' };
      setClipboardVersion((current) => current + 1);
      setEditorNotice('');
    } catch (error) {
      setEditorNotice(error.message);
    }
  }

  function handleSelectAll() {
    if (!activePage) return;
    setSelectedObjectIds(activePage.objects.map((object) => object.id));
  }

  function handleActivatePage(pageId, clearSelection = true) {
    setActivePageId(pageId);
    if (clearSelection) setSelectedObjectIds([]);
    setEditorNotice('');
  }

  function handleAddPage(sourcePageId = activePage?.id) {
    const result = insertBlankPageAfter(documentDefinition, sourcePageId);
    setDocumentDefinition(result.definition);
    setActivePageId(result.page.id);
    setSelectedObjectIds([]);
  }

  function handleDuplicatePage(pageId) {
    const result = duplicateDocumentPage(documentDefinition, pageId);
    if (!result) return;
    setDocumentDefinition(result.definition);
    setActivePageId(result.page.id);
    setSelectedObjectIds([]);
  }

  function requestDeletePage(pageId) {
    if (documentDefinition.pages.length <= 1) {
      setEditorNotice('El documento debe conservar al menos una hoja.');
      return;
    }
    setPageToDelete(pageId);
  }

  function confirmDeletePage() {
    const pageIndex = documentDefinition.pages.findIndex((page) => page.id === pageToDelete);
    if (pageIndex < 0 || documentDefinition.pages.length <= 1) return setPageToDelete(null);
    const nextPages = documentDefinition.pages.filter((page) => page.id !== pageToDelete);
    const nextActive = nextPages[Math.max(0, pageIndex - 1)] || nextPages[0];
    setDocumentDefinition({ ...documentDefinition, pages: nextPages });
    setActivePageId(nextActive.id);
    setSelectedObjectIds([]);
    setPageToDelete(null);
  }

  function updateActivePageSettings(settings) {
    if (!activePage) return;
    try {
      setDocumentDefinition(resizeDocumentPage(documentDefinition, activePage.id, {
        size: settings.size ?? activePage.size,
        orientation: settings.orientation ?? activePage.orientation,
        customWidth: settings.customWidth ?? activePage.width,
        customHeight: settings.customHeight ?? activePage.height,
        swapDimensions: settings.swapDimensions,
      }));
      setEditorNotice('');
    } catch (error) {
      setEditorNotice(error.message);
    }
  }

  function handleFitDocument() {
    const canvasWidth = canvasAreaRef.current?.clientWidth || 0;
    const page = documentDefinition.pages?.[0];
    if (!canvasWidth || !page) return setZoom(0.82);
    setZoom(clampZoom(Math.max(240, canvasWidth - 80) / mmToPx(page.width || 210)));
  }

  useEffect(() => {
    function handleKeyDown(event) {
      const tagName = event.target?.tagName?.toLowerCase();
      const isEditable = tagName === 'input' || tagName === 'textarea' || tagName === 'select' || event.target?.isContentEditable;
      if (isEditable) return;
      const key = event.key.toLowerCase();
      const command = event.metaKey || event.ctrlKey;
      if (command && key === 'c' && selectedObjectIds.length) { event.preventDefault(); handleCopy(); }
      else if (command && key === 'x' && selectedObjectIds.length) { event.preventDefault(); handleCut(); }
      else if (command && key === 'v' && clipboardRef.current?.objects?.length) { event.preventDefault(); handlePaste(); }
      else if (command && key === 'a') { event.preventDefault(); handleSelectAll(); }
      else if ((event.key === 'Delete' || event.key === 'Backspace') && selectedObjectIds.length) { event.preventDefault(); handleDelete(); }
      else if (event.key === 'Escape') setSelectedObjectIds([]);
    }
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [activePageId, documentDefinition, selectedObjectIds]);

  const selectedPageLength = selectedLocation ? documentDefinition.pages[selectedLocation.pageIndex].objects.length : 0;
  const pageSizeLabel = PAGE_SIZE_LABELS[activePage?.size] || activePage?.size || 'A4';
  const orientationLabel = activePage?.orientation === 'landscape' ? 'Horizontal' : 'Vertical';
  const deletionPage = documentDefinition.pages.find((page) => page.id === pageToDelete);
  const deletionPageNumber = documentDefinition.pages.findIndex((page) => page.id === pageToDelete) + 1;

  return (
    <>
    <section className="document-designer-lab">
      <header className="document-designer-lab__header"><div><span className="document-designer-lab__eyebrow">Laboratorio documental</span><h1>Diseñador de documentos</h1><p>Entorno experimental para construir y validar objetos documentales reutilizables sin afectar Control Documental ni los módulos operativos.</p></div><span className="document-designer-lab__status">Desarrollo</span></header>
      <div className="document-designer-lab__workspace">
        <aside className="document-designer-panel document-designer-panel--catalog">
          <div className="document-designer-panel__header"><h2>Componentes MYC</h2><span>{DOCUMENT_BLOCK_LIBRARY.reduce((total, group) => total + group.blocks.length, 0)} disponibles</span></div>
          <section className="document-page-manager">
            <div className="document-page-manager__header"><strong>Hojas</strong><button type="button" onClick={() => handleAddPage()}>Agregar página</button></div>
            <div className="document-page-list">{documentDefinition.pages.map((page, pageIndex) => <article className={`document-page-card${page.id === activePage?.id ? ' is-active' : ''}`} key={page.id}><button type="button" className="document-page-card__select" onClick={() => handleActivatePage(page.id)}><strong>Página {pageIndex + 1}</strong><span>{PAGE_SIZE_LABELS[page.size] || page.size} · {page.orientation === 'landscape' ? 'Horizontal' : 'Vertical'}</span><small>{page.objects.length} objetos</small></button><div><button type="button" onClick={() => handleDuplicatePage(page.id)}>Duplicar</button><button type="button" onClick={() => requestDeletePage(page.id)} disabled={documentDefinition.pages.length === 1}>Eliminar</button></div></article>)}</div>
          </section>
          <div className="document-object-catalog">{DOCUMENT_BLOCK_LIBRARY.map((group) => <section className="document-object-category" key={group.category}><h3>{group.category}</h3>{group.blocks.map((item) => <button key={item.type} type="button" className="document-object-catalog__item" onClick={() => handleAddBlock(item.type)}><span className="document-object-catalog__icon" aria-hidden="true">{item.label.slice(0, 1)}</span><span><strong>{item.label}</strong><small>{item.description}</small></span></button>)}</section>)}</div>
        </aside>
        <main className="document-designer-canvas-shell">
          <div className="document-designer-toolbar"><div><strong>{documentDefinition.document?.name || 'Documento de prueba'}</strong><span>{pageSizeLabel} {orientationLabel.toLowerCase()} · {Math.round(zoom * 100)}%</span></div><div className="document-designer-toolbar__actions"><div className="document-zoom-control" aria-label="Controles de zoom"><button type="button" onClick={() => setZoom((current) => clampZoom(current - ZOOM_STEP))} aria-label="Alejar">−</button><output>{Math.round(zoom * 100)}%</output><button type="button" onClick={() => setZoom((current) => clampZoom(current + ZOOM_STEP))} aria-label="Acercar">+</button><button type="button" onClick={handleFitDocument}>Ajustar</button></div><button type="button" disabled>Vista previa</button><button type="button" disabled>Guardar borrador</button></div></div>
          <div className="document-designer-statusbar" aria-label="Estado del documento">
            <div><span>Páginas<strong>{documentDefinition.pages.length}</strong></span><span>Objetos<strong>{totalObjects}</strong></span><span>Tamaño<strong>{pageSizeLabel}</strong></span><span>Orientación<strong>{orientationLabel}</strong></span></div>
            {selectedObjectIds.length > 1 ? <div className="document-designer-selection-info"><span className="document-designer-selection-indicator" aria-hidden="true" /><strong>{selectedObjectIds.length} objetos seleccionados</strong><span>Página activa {documentDefinition.pages.findIndex((page) => page.id === activePage?.id) + 1}</span></div> : selectedElement ? <div className="document-designer-selection-info"><span className="document-designer-selection-indicator" aria-hidden="true" /><strong>{selectedElement.label || selectedElement.type}</strong><span>Página {selectedLocation.pageIndex + 1}</span><span>X {Number(selectedElement.x).toFixed(1)} mm</span><span>Y {Number(selectedElement.y).toFixed(1)} mm</span><span>{Number(selectedElement.width).toFixed(1)} × {Number(selectedElement.height).toFixed(1)} mm</span></div> : <div className="document-designer-selection-info is-empty">Página activa {documentDefinition.pages.findIndex((page) => page.id === activePage?.id) + 1} · Ningún objeto seleccionado</div>}
          </div>
          <div className="document-designer-context-actions"><button type="button" onClick={() => handleCopy()} disabled={!selectedObjectIds.length}>Copiar</button><button type="button" onClick={handleCut} disabled={!selectedObjectIds.length}>Cortar</button><button type="button" onClick={handlePaste} disabled={!hasClipboard}>Pegar</button><button type="button" onClick={handleDuplicate} disabled={!selectedObjectIds.length}>Duplicar</button><button type="button" className="is-danger" onClick={handleDelete} disabled={!selectedObjectIds.length}>Eliminar</button></div>
          {editorNotice ? <div className="document-designer-notice">{editorNotice}</div> : null}
          <div ref={canvasAreaRef} className="document-designer-canvas-area" onClick={(event) => { if (event.target === event.currentTarget) setSelectedObjectIds([]); }}><DocumentPreviewRenderer definition={documentDefinition} zoom={zoom} selectedObjectIds={selectedObjectIds} activePageId={activePage?.id} onSelectElement={handleSelectObject} onMoveStart={handleMoveStart} onMoveElement={handleMoveElement} onMoveEnd={handleMoveEnd} onActivatePage={(pageId) => handleActivatePage(pageId, false)} onClearSelection={() => setSelectedObjectIds([])} /></div>
        </main>
        <aside className="document-designer-panel document-designer-panel--inspector">
          <div className="document-designer-panel__header"><h2>Inspector</h2><span>{selectedElement?.label || selectedElement?.type || 'Sin selección'}</span></div>
          <div className="document-inspector">
            <section className="document-inspector-section"><h3>Configuración de página</h3><div className="document-inspector-grid"><label className="document-inspector-field"><span>Tamaño</span><select value={activePage?.size || 'A4'} onChange={(event) => updateActivePageSettings({ size: event.target.value })}>{PAGE_SIZE_OPTIONS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label><label className="document-inspector-field"><span>Orientación</span><select value={activePage?.orientation || 'portrait'} onChange={(event) => updateActivePageSettings({ orientation: event.target.value, swapDimensions: activePage?.size === 'CUSTOM' && event.target.value !== activePage.orientation })}><option value="portrait">Vertical</option><option value="landscape">Horizontal</option></select></label>{activePage?.size === 'CUSTOM' ? <><NumberField label="Ancho (mm)" value={activePage.width} onChange={(value) => updateActivePageSettings({ customWidth: Math.min(1000, Math.max(50, value)) })} /><NumberField label="Alto (mm)" value={activePage.height} onChange={(value) => updateActivePageSettings({ customHeight: Math.min(1000, Math.max(50, value)) })} /></> : null}</div><div className="document-page-settings-actions"><button type="button" onClick={() => handleAddPage(activePage?.id)}>Agregar hoja</button><button type="button" onClick={() => handleDuplicatePage(activePage?.id)}>Duplicar hoja</button><button type="button" className="is-danger" onClick={() => requestDeletePage(activePage?.id)} disabled={documentDefinition.pages.length === 1}>Borrar hoja</button></div></section>
            {selectedObjectIds.length > 1 ? <section className="document-inspector-section"><div className="document-inspector-section__title"><strong>{selectedObjectIds.length} objetos seleccionados</strong><span>Selección múltiple · Página {selectedLocation ? selectedLocation.pageIndex + 1 : ''}</span></div><div className="document-inspector-actions"><button type="button" onClick={() => handleCopy()}>Copiar</button><button type="button" onClick={handleCut}>Cortar</button><button type="button" onClick={handleDuplicate}>Duplicar</button><button type="button" className="is-danger" onClick={handleDelete}>Eliminar</button></div></section> : selectedElement ? <>
            <section className="document-inspector-section"><div className="document-inspector-section__title"><strong>{selectedElement.label || selectedElement.id}</strong><span>{selectedElement.type} · {selectedElement.id}</span></div><div className="document-inspector-actions"><button type="button" onClick={() => handleReorder(-1)} disabled={selectedLocation?.objectIndex === 0}>Mover arriba</button><button type="button" onClick={() => handleReorder(1)} disabled={selectedLocation?.objectIndex === selectedPageLength - 1}>Mover abajo</button><button type="button" onClick={handleDuplicate}>Duplicar</button><button type="button" className="is-danger" onClick={handleDelete}>Eliminar</button></div></section>
            {selectedFields.length ? <section className="document-inspector-section"><h3>Propiedades</h3><div className="document-inspector-grid">{selectedFields.map((field) => <PropertyControl key={field.key} field={field} value={selectedElement.props?.[field.key]} onChange={(value) => updateProperty(field, value)} />)}</div></section> : null}
            {!selectedElement.props && (selectedElement.type === 'text' || selectedElement.type === 'document-code' || selectedElement.type === 'document-revision') ? <section className="document-inspector-section"><h3>Contenido</h3><label className="document-inspector-field document-inspector-field--full"><span>{selectedElement.type === 'text' ? 'Texto' : 'Valor de respaldo'}</span><textarea value={selectedElement.type === 'text' ? selectedElement.content || '' : selectedElement.fallback_value || ''} onChange={(event) => updateSelectedElement(selectedElement.type === 'text' ? { content: event.target.value } : { fallback_value: event.target.value })} /></label><div className="document-inspector-grid"><NumberField label="Fuente" value={selectedElement.style?.font_size || 12} onChange={(value) => updateSelectedStyle({ font_size: value })} /><PropertyControl field={{ key: 'align', label: 'Alineación', control: 'select', options: ALIGN_OPTIONS }} value={selectedElement.style?.text_align || 'left'} onChange={(value) => updateSelectedStyle({ text_align: value })} /></div></section> : null}
            <section className="document-inspector-section"><h3>Geometría</h3><div className="document-inspector-grid"><NumberField label="X" value={selectedElement.x} step={0.5} onChange={(value) => updateSelectedElement({ x: value })} /><NumberField label="Y" value={selectedElement.y} step={0.5} onChange={(value) => updateSelectedElement({ y: value })} /><NumberField label="Ancho" value={selectedElement.width} step={0.5} onChange={(value) => updateSelectedElement({ width: value })} /><NumberField label="Alto" value={selectedElement.height} step={0.5} onChange={(value) => updateSelectedElement({ height: value })} /></div></section>
            <section className="document-inspector-section"><h3>Estado</h3><div className="document-inspector-switches"><label className="document-inspector-check"><input type="checkbox" checked={selectedElement.visible !== false} onChange={(event) => updateSelectedElement({ visible: event.target.checked })} /><span>Visible</span></label><label className="document-inspector-check"><input type="checkbox" checked={Boolean(selectedElement.locked)} onChange={(event) => updateSelectedElement({ locked: event.target.checked })} /><span>Bloqueado</span></label></div></section>
            </> : <div className="document-designer-empty">Selecciona un bloque para editar sus propiedades.</div>}
          </div>
        </aside>
      </div>
    </section>
    <ConfirmDialog isOpen={Boolean(pageToDelete)} title={`¿Borrar la página ${deletionPageNumber}?`} message={`También se eliminarán los ${deletionPage?.objects?.length || 0} objetos contenidos en ella.`} confirmText="Borrar hoja" cancelText="Cancelar" variant="danger" onClose={() => setPageToDelete(null)} onConfirm={confirmDeletePage} />
    </>
  );
}
