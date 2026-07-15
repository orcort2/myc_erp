import { Check, ChevronDown, Search, X } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';

import { listSatCatalogRecords } from '../../services/api.js';

export default function SatCatalogField({
  catalog,
  catalogCode,
  label,
  onChange,
  value,
  showAllOnOpen = false,
}) {
  const [isEditing, setIsEditing] = useState(false);
  const [query, setQuery] = useState('');
  const [items, setItems] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const fieldRef = useRef(null);
  const inputRef = useRef(null);
  const [activeIndex, setActiveIndex] = useState(-1);

  useEffect(() => {
    if (!isEditing) return undefined;

    const handlePointerDown = (event) => {
      if (!fieldRef.current?.contains(event.target)) {
        setIsEditing(false);
        setQuery('');
        setItems([]);
        setError('');
      }
    };

    document.addEventListener('pointerdown', handlePointerDown);

    return () => {
      document.removeEventListener('pointerdown', handlePointerDown);
    };
  }, [isEditing]);

  useEffect(() => {
    if (!catalog || !isEditing) return undefined;

    const normalizedQuery = query.trim();

    if (!normalizedQuery && !showAllOnOpen) {
      setItems([]);
      setError('');
      setIsLoading(false);
      return undefined;
    }

    let active = true;

    const timer = window.setTimeout(async () => {
      setIsLoading(true);
      setError('');

      try {
        const result = await listSatCatalogRecords(catalogCode, {
          search: normalizedQuery,
          limit: showAllOnOpen ? 200 : 20,
        });

        if (!active) return;

        setItems(Array.isArray(result?.items) ? result.items : []);
      } catch (requestError) {
        if (!active) return;

        setItems([]);
        setError(
          requestError?.message ||
            'No fue posible consultar el catálogo.'
        );
      } finally {
        if (active) {
          setIsLoading(false);
        }
      }
    }, normalizedQuery ? 220 : 0);

    return () => {
      active = false;
      window.clearTimeout(timer);
    };
  }, [catalog, catalogCode, isEditing, query]);

  function openEditor() {
    if (!catalog) return;

    setIsEditing(true);
    setQuery('');
    setItems([]);
    setError('');
    setActiveIndex(-1);

    window.requestAnimationFrame(() => {
      inputRef.current?.focus();
    });
  }

  function closeEditor() {
    setIsEditing(false);
    setQuery('');
    setItems([]);
    setError('');
  }

  function selectItem(item) {
    onChange({
      id: item.id ?? null,
      code: String(item.code ?? '').trim(),
      name: item.name || '',
    });

    closeEditor();
  }

  function onInputKeyDown(event) {
    if (event.key === 'ArrowDown') { event.preventDefault(); setActiveIndex((index) => Math.min(index + 1, items.length - 1)); }
    if (event.key === 'ArrowUp') { event.preventDefault(); setActiveIndex((index) => Math.max(index - 1, 0)); }
    if (event.key === 'Enter' && activeIndex >= 0 && items[activeIndex]) { event.preventDefault(); selectItem(items[activeIndex]); }
    if (event.key === 'Escape') { event.preventDefault(); closeEditor(); }
  }

  if (!catalog) {
    return (
      <div className="invoice-sat-field invoice-sat-field--unavailable">
        <span>{label}</span>
        <small>Catálogo no disponible en la instalación local.</small>
      </div>
    );
  }

  const hasValue = Boolean(value?.code);
  const selectedLabel = hasValue
    ? `${value.code}${value.name ? ` · ${value.name}` : ''}`
    : 'Sin seleccionar';

  return (
    <div
      className={`invoice-sat-field ${
        isEditing ? 'is-editing' : ''
      }`}
      ref={fieldRef}
    >
      <span>{label}</span>

      {!isEditing ? (
        <button
          className={`invoice-sat-field__value ${
            hasValue ? 'has-value' : 'is-empty'
          }`}
          onClick={openEditor}
          aria-expanded="false"
          type="button"
        >
          <span className="invoice-sat-field__value-text">
            {hasValue ? <Check size={15} /> : null}
            <strong>{selectedLabel}</strong>
          </span>

          <span className="invoice-sat-field__change">
            {hasValue ? 'Cambiar' : 'Seleccionar'}
            <ChevronDown size={15} />
          </span>
        </button>
      ) : (
        <div className="invoice-sat-field__editor">
          <div className="invoice-sat-field__control">
            <Search aria-hidden="true" size={15} />

            <input
              aria-activedescendant={activeIndex >= 0 ? `${catalogCode}-option-${items[activeIndex]?.id}` : undefined}
              aria-label={`Buscar ${label} en ${catalog.name}`}
              aria-expanded="true"
              aria-controls={`${catalogCode}-options`}
              aria-autocomplete="list"
              role="combobox"
              onChange={(event) => setQuery(event.target.value)}
              onKeyDown={onInputKeyDown}
              placeholder={`Buscar en ${catalog.name}`}
              ref={inputRef}
              value={query}
            />

            <button
              aria-label={`Cerrar búsqueda de ${label}`}
              className="invoice-sat-field__close"
              onClick={closeEditor}
              type="button"
            >
              <X size={15} />
            </button>
          </div>

          <div className="invoice-sat-field__results" id={`${catalogCode}-options`} role="listbox">
            {!query.trim() && !showAllOnOpen ? <small>Escribe una clave o descripción para buscar.</small> : null}

            {isLoading ? (
              <small>Consultando catálogo local…</small>
            ) : null}

            {error ? (
              <small className="invoice-sat-field__error">
                {error}
              </small>
            ) : null}

            {!isLoading &&
            !error &&
            query.trim() &&
            !items.length ? (
              <small>Sin coincidencias en el catálogo local.</small>
            ) : null}

            {items.map((item) => (
              <button
                aria-selected={activeIndex === items.indexOf(item)}
                id={`${catalogCode}-option-${item.id}`}
                key={item.id ?? `${item.code}-${item.name}`}
                onClick={() => selectItem(item)}
                role="option"
                type="button"
              >
                <strong>{item.code} — {item.name || 'Sin descripción'}</strong>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
