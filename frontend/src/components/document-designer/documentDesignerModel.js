export const MDE_SCHEMA_VERSION = '1.0';

export const MM_TO_PX = 96 / 25.4;

export const PAGE_SIZES_MM = {
  A4: {
    width: 210,
    height: 297,
  },
  LETTER: {
    width: 215.9,
    height: 279.4,
  },
  LEGAL: {
    width: 215.9,
    height: 355.6,
  },
  HALF_LETTER: {
    width: 139.7,
    height: 215.9,
  },
};

const DEFAULT_MARGINS = {
  top: 12,
  right: 12,
  bottom: 12,
  left: 12,
};

const SUPPORTED_OBJECT_TYPES = new Set([
  'text',
  'image',
  'line',
  'rectangle',
  'document-code',
  'document-revision',
  'signature-line',
  'group',
]);

export function mmToPx(value) {
  const number = Number(value);

  if (!Number.isFinite(number)) {
    return 0;
  }

  return number * MM_TO_PX;
}

export function pxToMm(value) {
  const number = Number(value);

  if (!Number.isFinite(number)) {
    return 0;
  }

  return number / MM_TO_PX;
}

export function getPageDimensions({
  size = 'A4',
  orientation = 'portrait',
  customWidth = null,
  customHeight = null,
} = {}) {
  let width;
  let height;

  if (size === 'CUSTOM') {
    width = Number(customWidth);
    height = Number(customHeight);

    if (!Number.isFinite(width) || width <= 0) {
      throw new Error('El ancho personalizado debe ser mayor que cero.');
    }

    if (!Number.isFinite(height) || height <= 0) {
      throw new Error('El alto personalizado debe ser mayor que cero.');
    }
  } else {
    const pageSize = PAGE_SIZES_MM[size];

    if (!pageSize) {
      throw new Error(`Tamaño de página no soportado: ${size}`);
    }

    width = pageSize.width;
    height = pageSize.height;
  }

  if (orientation === 'landscape') {
    return {
      width: height,
      height: width,
    };
  }

  return {
    width,
    height,
  };
}

export function createDocumentObject(overrides = {}) {
  return {
    schema_version: MDE_SCHEMA_VERSION,
    document: {
      id: 'document-test',
      name: 'Documento de prueba',
      page_size: 'A4',
      orientation: 'portrait',
      unit: 'mm',
      margins: {
        ...DEFAULT_MARGINS,
      },
      background: '#ffffff',
      show_guides: true,
      grid: {
        enabled: true,
        size: 5,
      },
      ...overrides.document,
      margins: {
        ...DEFAULT_MARGINS,
        ...(overrides.document?.margins || {}),
      },
      grid: {
        enabled: true,
        size: 5,
        ...(overrides.document?.grid || {}),
      },
    },
    pages: Array.isArray(overrides.pages)
      ? overrides.pages
      : [createPageObject()],
    styles: {
      ...(overrides.styles || {}),
    },
    bindings: {
      ...(overrides.bindings || {}),
    },
    metadata: {
      created_at: new Date().toISOString(),
      source: 'document-designer-lab',
      ...(overrides.metadata || {}),
    },
  };
}

export function createPageObject(overrides = {}) {
  return {
    id: 'page-1',
    size: 'A4',
    orientation: 'portrait',
    width: 210,
    height: 297,
    margins: {
      ...DEFAULT_MARGINS,
    },
    background: '#ffffff',
    repeatable_header: null,
    repeatable_footer: null,
    objects: [],
    ...overrides,
    margins: {
      ...DEFAULT_MARGINS,
      ...(overrides.margins || {}),
    },
    objects: Array.isArray(overrides.objects) ? overrides.objects : [],
  };
}

export function createDocumentElement(type, overrides = {}) {
  if (!SUPPORTED_OBJECT_TYPES.has(type)) {
    throw new Error(`Tipo de objeto documental no soportado: ${type}`);
  }

  return {
    id: overrides.id || createElementId(type),
    type,
    page_id: overrides.page_id || 'page-1',
    x: Number.isFinite(Number(overrides.x)) ? Number(overrides.x) : 20,
    y: Number.isFinite(Number(overrides.y)) ? Number(overrides.y) : 20,
    width: Number.isFinite(Number(overrides.width))
      ? Number(overrides.width)
      : 60,
    height: Number.isFinite(Number(overrides.height))
      ? Number(overrides.height)
      : 10,
    rotation: Number.isFinite(Number(overrides.rotation))
      ? Number(overrides.rotation)
      : 0,
    visible: overrides.visible !== false,
    locked: Boolean(overrides.locked),
    z_index: Number.isFinite(Number(overrides.z_index))
      ? Number(overrides.z_index)
      : 1,
    style: {
      ...(overrides.style || {}),
    },
    binding: overrides.binding ?? null,
    metadata: {
      ...(overrides.metadata || {}),
    },
    ...overrides,
  };
}

export function normalizeDocumentDefinition(definition) {
  const source =
    definition && typeof definition === 'object' ? definition : {};

  const normalizedDocument = createDocumentObject({
    document: source.document || {},
    pages: [],
    styles: source.styles || {},
    bindings: source.bindings || {},
    metadata: source.metadata || {},
  });

  normalizedDocument.schema_version =
    source.schema_version || MDE_SCHEMA_VERSION;

  normalizedDocument.pages = Array.isArray(source.pages)
    ? source.pages.map((page, index) =>
        normalizePageObject(page, `page-${index + 1}`)
      )
    : [createPageObject()];

  return normalizedDocument;
}

export function normalizePageObject(page, fallbackId = 'page-1') {
  const source = page && typeof page === 'object' ? page : {};

  const dimensions = getPageDimensions({
    size: source.size || 'A4',
    orientation: source.orientation || 'portrait',
    customWidth: source.width,
    customHeight: source.height,
  });

  return createPageObject({
    ...source,
    id: source.id || fallbackId,
    width: dimensions.width,
    height: dimensions.height,
    objects: Array.isArray(source.objects)
      ? source.objects
          .map((object) => normalizeDocumentElement(object))
          .filter(Boolean)
      : [],
  });
}

export function normalizeDocumentElement(element) {
  if (!element || typeof element !== 'object') {
    return null;
  }

  if (!SUPPORTED_OBJECT_TYPES.has(element.type)) {
    return null;
  }

  return createDocumentElement(element.type, element);
}

export function validateDocumentDefinition(definition) {
  const errors = [];
  const warnings = [];

  if (!definition || typeof definition !== 'object') {
    return {
      valid: false,
      errors: ['La definición documental no es válida.'],
      warnings,
    };
  }

  if (definition.schema_version !== MDE_SCHEMA_VERSION) {
    warnings.push(
      `La definición usa schema ${definition.schema_version || 'desconocido'}; el Lab utiliza ${MDE_SCHEMA_VERSION}.`
    );
  }

  if (!definition.document?.id) {
    errors.push('El documento debe tener un identificador.');
  }

  if (!definition.document?.name) {
    errors.push('El documento debe tener un nombre.');
  }

  if (!Array.isArray(definition.pages) || definition.pages.length === 0) {
    errors.push('El documento debe contener al menos una página.');
  }

  const pageIds = new Set();
  const elementIds = new Set();

  for (const page of definition.pages || []) {
    if (!page.id) {
      errors.push('Todas las páginas deben tener identificador.');
      continue;
    }

    if (pageIds.has(page.id)) {
      errors.push(`Identificador de página duplicado: ${page.id}`);
    }

    pageIds.add(page.id);

    if (!Number.isFinite(page.width) || page.width <= 0) {
      errors.push(`La página ${page.id} tiene un ancho inválido.`);
    }

    if (!Number.isFinite(page.height) || page.height <= 0) {
      errors.push(`La página ${page.id} tiene un alto inválido.`);
    }

    for (const element of page.objects || []) {
      if (!element.id) {
        errors.push(`Existe un objeto sin identificador en ${page.id}.`);
        continue;
      }

      if (elementIds.has(element.id)) {
        errors.push(`Identificador de objeto duplicado: ${element.id}`);
      }

      elementIds.add(element.id);

      if (!SUPPORTED_OBJECT_TYPES.has(element.type)) {
        errors.push(
          `El objeto ${element.id} usa un tipo no soportado: ${element.type}`
        );
      }

      if (element.width < 0 || element.height < 0) {
        errors.push(
          `El objeto ${element.id} tiene dimensiones negativas.`
        );
      }

      if (
        element.x < 0 ||
        element.y < 0 ||
        element.x + element.width > page.width ||
        element.y + element.height > page.height
      ) {
        warnings.push(
          `El objeto ${element.id} queda total o parcialmente fuera de ${page.id}.`
        );
      }
    }
  }

  return {
    valid: errors.length === 0,
    errors,
    warnings,
  };
}

export function createInitialTestDocument() {
  return createDocumentObject({
    document: {
      id: 'mde-test-document',
      name: 'Documento de prueba MDE',
      page_size: 'A4',
      orientation: 'portrait',
      unit: 'mm',
    },
    pages: [
      createPageObject({
        id: 'page-1',
        size: 'A4',
        orientation: 'portrait',
        objects: [
          createDocumentElement('image', {
            id: 'myc-logo',
            x: 15,
            y: 12,
            width: 38,
            height: 18,
            z_index: 1,
            source_type: 'asset',
            source: 'myc-logo',
            fit: 'contain',
            preserve_aspect_ratio: true,
          }),
          createDocumentElement('text', {
            id: 'company-name',
            x: 55,
            y: 14,
            width: 100,
            height: 8,
            z_index: 2,
            content: 'METROLOGÍA Y SERVICIOS MYC',
            style: {
              font_size: 12,
              font_weight: 700,
              text_align: 'center',
              color: '#111827',
            },
          }),
          createDocumentElement('text', {
            id: 'document-title',
            x: 20,
            y: 42,
            width: 170,
            height: 12,
            z_index: 3,
            content: 'DOCUMENTO DE PRUEBA',
            style: {
              font_size: 16,
              font_weight: 700,
              text_align: 'center',
              color: '#111827',
            },
          }),
          createDocumentElement('document-code', {
            id: 'document-code',
            x: 158,
            y: 14,
            width: 35,
            height: 7,
            z_index: 4,
            binding: 'document.code',
            fallback_value: 'FCA-TEST',
            style: {
              font_size: 10,
              font_weight: 700,
              text_align: 'right',
              color: '#111827',
            },
          }),
          createDocumentElement('document-revision', {
            id: 'document-revision',
            x: 158,
            y: 22,
            width: 35,
            height: 7,
            z_index: 5,
            binding: 'document.revision',
            fallback_value: 'R0',
            style: {
              font_size: 10,
              font_weight: 700,
              text_align: 'right',
              color: '#111827',
            },
          }),
          createDocumentElement('text', {
            id: 'body-copy',
            x: 20,
            y: 70,
            width: 170,
            height: 30,
            z_index: 6,
            content:
              'Este documento valida el contrato inicial del MYC Document Engine.',
            style: {
              font_size: 10,
              font_weight: 400,
              text_align: 'left',
              color: '#344054',
            },
          }),
          createDocumentElement('signature-line', {
            id: 'signature-line',
            x: 55,
            y: 235,
            width: 100,
            height: 22,
            z_index: 7,
            label: 'Firma de autorización',
            show_name: true,
            show_position: false,
            show_date: false,
            style: {
              font_size: 9,
              text_align: 'center',
              stroke_color: '#111827',
              stroke_width: 0.4,
            },
          }),
          createDocumentElement('line', {
            id: 'footer-line',
            x: 15,
            y: 275,
            width: 180,
            height: 0,
            z_index: 8,
            direction: 'horizontal',
            stroke_width: 0.3,
            stroke_style: 'solid',
            stroke_color: '#98a2b3',
          }),
          createDocumentElement('text', {
            id: 'footer-copy',
            x: 15,
            y: 278,
            width: 180,
            height: 8,
            z_index: 9,
            content:
              'Documento experimental generado por MYC Document Engine.',
            style: {
              font_size: 8,
              font_weight: 400,
              text_align: 'center',
              color: '#667085',
            },
          }),
        ],
      }),
    ],
    bindings: {
      'document.code': 'FCA-TEST',
      'document.revision': 'R0',
    },
  });
}

function createElementId(type) {
  const safeType = String(type || 'object')
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '');

  if (
    typeof crypto !== 'undefined' &&
    typeof crypto.randomUUID === 'function'
  ) {
    return `${safeType}-${crypto.randomUUID()}`;
  }

  return `${safeType}-${Date.now()}-${Math.random()
    .toString(16)
    .slice(2)}`;
}