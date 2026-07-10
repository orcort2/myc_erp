import { useMemo, useRef, useState } from 'react';

import DocumentPreviewRenderer from '../../components/document-designer/DocumentPreviewRenderer.jsx';
import {
  createInitialTestDocument,
  mmToPx,
} from '../../components/document-designer/documentDesignerModel.js';

import '../../components/document-designer/document-designer.css';

const ELEMENT_CATALOG = [
  { type: 'text', label: 'Texto', description: 'Contenido libre' },
  { type: 'image', label: 'Imagen', description: 'Logo o recurso' },
  { type: 'line', label: 'Línea', description: 'Separador' },
  { type: 'rectangle', label: 'Rectángulo', description: 'Marco o fondo' },
  { type: 'document-code', label: 'Código', description: 'Código documental' },
  { type: 'document-revision', label: 'Revisión', description: 'Revisión vigente' },
  { type: 'signature-line', label: 'Firma', description: 'Espacio de firma' },
];

const MIN_ZOOM = 0.35;
const MAX_ZOOM = 1.5;
const ZOOM_STEP = 0.1;

function clampZoom(value) {
  return Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, value));
}

function findElementById(definition, elementId) {
  if (!elementId) {
    return null;
  }

  for (const page of definition.pages || []) {
    const element = (page.objects || []).find((item) => item.id === elementId);

    if (element) {
      return element;
    }
  }

  return null;
}

function updateElementById(definition, elementId, updater) {
  return {
    ...definition,
    pages: (definition.pages || []).map((page) => ({
      ...page,
      objects: (page.objects || []).map((element) =>
        element.id === elementId ? updater(element) : element,
      ),
    })),
  };
}

function NumberField({ label, value, onChange, step = 1 }) {
  return (
    <label className="document-inspector-field">
      <span>{label}</span>
      <input
        type="number"
        value={value}
        step={step}
        onChange={(event) => onChange(Number(event.target.value))}
      />
    </label>
  );
}

export default function DocumentDesignerLabPage() {
  const canvasAreaRef = useRef(null);
  const [documentDefinition, setDocumentDefinition] = useState(() =>
    createInitialTestDocument(),
  );
  const [selectedElementId, setSelectedElementId] = useState(null);
  const [zoom, setZoom] = useState(0.82);

  const selectedElement = useMemo(
    () => findElementById(documentDefinition, selectedElementId),
    [documentDefinition, selectedElementId],
  );

  function updateSelectedElement(changes) {
    if (!selectedElementId) {
      return;
    }

    setDocumentDefinition((current) =>
      updateElementById(current, selectedElementId, (element) => ({
        ...element,
        ...changes,
      })),
    );
  }

  function updateSelectedStyle(changes) {
    if (!selectedElementId) {
      return;
    }

    setDocumentDefinition((current) =>
      updateElementById(current, selectedElementId, (element) => ({
        ...element,
        style: {
          ...(element.style || {}),
          ...changes,
        },
      })),
    );
  }

  function handleFitDocument() {
    const canvasWidth = canvasAreaRef.current?.clientWidth || 0;
    const page = documentDefinition.pages?.[0];

    if (!canvasWidth || !page) {
      setZoom(0.82);
      return;
    }

    const availableWidth = Math.max(240, canvasWidth - 80);
    const pageWidthPx = mmToPx(page.width || 210);
    setZoom(clampZoom(availableWidth / pageWidthPx));
  }

  return (
    <section className="document-designer-lab">
      <header className="document-designer-lab__header">
        <div>
          <span className="document-designer-lab__eyebrow">
            Laboratorio documental
          </span>

          <h1>Diseñador de documentos</h1>

          <p>
            Entorno experimental para construir y validar objetos documentales
            reutilizables sin afectar Control Documental ni los módulos operativos.
          </p>
        </div>

        <span className="document-designer-lab__status">Desarrollo</span>
      </header>

      <div className="document-designer-lab__workspace">
        <aside className="document-designer-panel document-designer-panel--catalog">
          <div className="document-designer-panel__header">
            <h2>Objetos documentales</h2>
            <span>{ELEMENT_CATALOG.length} iniciales</span>
          </div>

          <div className="document-object-catalog">
            {ELEMENT_CATALOG.map((item) => (
              <button
                key={item.type}
                type="button"
                className="document-object-catalog__item"
                disabled
                title="La inserción se habilitará en una fase posterior"
              >
                <span className="document-object-catalog__icon" aria-hidden="true">
                  {item.label.slice(0, 1)}
                </span>
                <span>
                  <strong>{item.label}</strong>
                  <small>{item.description}</small>
                </span>
              </button>
            ))}
          </div>
        </aside>

        <main className="document-designer-canvas-shell">
          <div className="document-designer-toolbar">
            <div>
              <strong>Documento de prueba</strong>
              <span>A4 vertical · {Math.round(zoom * 100)}%</span>
            </div>

            <div className="document-designer-toolbar__actions">
              <div className="document-zoom-control" aria-label="Controles de zoom">
                <button
                  type="button"
                  onClick={() => setZoom((current) => clampZoom(current - ZOOM_STEP))}
                  aria-label="Alejar"
                >
                  −
                </button>
                <output>{Math.round(zoom * 100)}%</output>
                <button
                  type="button"
                  onClick={() => setZoom((current) => clampZoom(current + ZOOM_STEP))}
                  aria-label="Acercar"
                >
                  +
                </button>
                <button type="button" onClick={handleFitDocument}>
                  Ajustar
                </button>
              </div>

              <button type="button" disabled>
                Vista previa
              </button>

              <button type="button" disabled>
                Guardar borrador
              </button>
            </div>
          </div>

          <div
            ref={canvasAreaRef}
            className="document-designer-canvas-area"
            onClick={(event) => {
              if (event.target === event.currentTarget) {
                setSelectedElementId(null);
              }
            }}
          >
            <DocumentPreviewRenderer
              definition={documentDefinition}
              zoom={zoom}
              selectedElementId={selectedElementId}
              onSelectElement={setSelectedElementId}
              onClearSelection={() => setSelectedElementId(null)}
            />
          </div>
        </main>

        <aside className="document-designer-panel document-designer-panel--inspector">
          <div className="document-designer-panel__header">
            <h2>Inspector</h2>
            <span>{selectedElement ? selectedElement.type : 'Sin selección'}</span>
          </div>

          {!selectedElement ? (
            <div className="document-designer-empty">
              Selecciona un objeto del documento para editar sus propiedades.
            </div>
          ) : (
            <div className="document-inspector">
              <section className="document-inspector-section">
                <div className="document-inspector-section__title">
                  <strong>{selectedElement.id}</strong>
                  <span>{selectedElement.type}</span>
                </div>

                <div className="document-inspector-grid">
                  <NumberField
                    label="X"
                    value={selectedElement.x}
                    step={0.5}
                    onChange={(value) => updateSelectedElement({ x: value })}
                  />
                  <NumberField
                    label="Y"
                    value={selectedElement.y}
                    step={0.5}
                    onChange={(value) => updateSelectedElement({ y: value })}
                  />
                  <NumberField
                    label="Ancho"
                    value={selectedElement.width}
                    step={0.5}
                    onChange={(value) => updateSelectedElement({ width: value })}
                  />
                  <NumberField
                    label="Alto"
                    value={selectedElement.height}
                    step={0.5}
                    onChange={(value) => updateSelectedElement({ height: value })}
                  />
                  <NumberField
                    label="Rotación"
                    value={selectedElement.rotation || 0}
                    step={1}
                    onChange={(value) => updateSelectedElement({ rotation: value })}
                  />
                  <NumberField
                    label="Capa"
                    value={selectedElement.z_index || 1}
                    step={1}
                    onChange={(value) => updateSelectedElement({ z_index: value })}
                  />
                </div>
              </section>

              {(selectedElement.type === 'text' ||
                selectedElement.type === 'document-code' ||
                selectedElement.type === 'document-revision') && (
                <section className="document-inspector-section">
                  <h3>Contenido</h3>

                  {selectedElement.type === 'text' ? (
                    <label className="document-inspector-field document-inspector-field--full">
                      <span>Texto</span>
                      <textarea
                        value={selectedElement.content || ''}
                        onChange={(event) =>
                          updateSelectedElement({ content: event.target.value })
                        }
                      />
                    </label>
                  ) : (
                    <label className="document-inspector-field document-inspector-field--full">
                      <span>Valor de respaldo</span>
                      <input
                        type="text"
                        value={selectedElement.fallback_value || ''}
                        onChange={(event) =>
                          updateSelectedElement({
                            fallback_value: event.target.value,
                          })
                        }
                      />
                    </label>
                  )}

                  <div className="document-inspector-grid">
                    <NumberField
                      label="Fuente"
                      value={selectedElement.style?.font_size || 12}
                      step={1}
                      onChange={(value) => updateSelectedStyle({ font_size: value })}
                    />

                    <label className="document-inspector-field">
                      <span>Alineación</span>
                      <select
                        value={selectedElement.style?.text_align || 'left'}
                        onChange={(event) =>
                          updateSelectedStyle({ text_align: event.target.value })
                        }
                      >
                        <option value="left">Izquierda</option>
                        <option value="center">Centro</option>
                        <option value="right">Derecha</option>
                      </select>
                    </label>

                    <label className="document-inspector-field">
                      <span>Color</span>
                      <input
                        type="color"
                        value={selectedElement.style?.color || '#111827'}
                        onChange={(event) =>
                          updateSelectedStyle({ color: event.target.value })
                        }
                      />
                    </label>

                    <label className="document-inspector-check">
                      <input
                        type="checkbox"
                        checked={Number(selectedElement.style?.font_weight) >= 700}
                        onChange={(event) =>
                          updateSelectedStyle({
                            font_weight: event.target.checked ? 700 : 400,
                          })
                        }
                      />
                      <span>Negritas</span>
                    </label>
                  </div>
                </section>
              )}

              {selectedElement.type === 'signature-line' ? (
                <section className="document-inspector-section">
                  <h3>Firma</h3>
                  <label className="document-inspector-field document-inspector-field--full">
                    <span>Etiqueta</span>
                    <input
                      type="text"
                      value={selectedElement.label || ''}
                      onChange={(event) =>
                        updateSelectedElement({ label: event.target.value })
                      }
                    />
                  </label>
                </section>
              ) : null}

              <section className="document-inspector-section">
                <h3>Estado</h3>
                <div className="document-inspector-switches">
                  <label className="document-inspector-check">
                    <input
                      type="checkbox"
                      checked={selectedElement.visible !== false}
                      onChange={(event) =>
                        updateSelectedElement({ visible: event.target.checked })
                      }
                    />
                    <span>Visible</span>
                  </label>

                  <label className="document-inspector-check">
                    <input
                      type="checkbox"
                      checked={Boolean(selectedElement.locked)}
                      onChange={(event) =>
                        updateSelectedElement({ locked: event.target.checked })
                      }
                    />
                    <span>Bloqueado</span>
                  </label>
                </div>
              </section>
            </div>
          )}
        </aside>
      </div>
    </section>
  );
}