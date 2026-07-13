import { createPageObject, getPageDimensions } from './documentDesignerModel.js';

export const DEFAULT_OBJECT_GAP = 4;

function finiteNumber(value, fallback = 0) {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
}

function roundMillimeters(value) {
  return Number(finiteNumber(value).toFixed(2));
}

function deepClone(value) {
  return typeof structuredClone === 'function'
    ? structuredClone(value)
    : JSON.parse(JSON.stringify(value));
}

export function createCanvasObjectId(type = 'object') {
  const safeType = String(type).toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'object';
  return `${safeType}-${typeof crypto !== 'undefined' && crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(16).slice(2)}`}`;
}

export function getPrintableBounds(page) {
  const margins = page?.margins || {};
  const left = Math.max(0, finiteNumber(margins.left));
  const top = Math.max(0, finiteNumber(margins.top));
  const right = Math.max(left, finiteNumber(page?.width) - Math.max(0, finiteNumber(margins.right)));
  const bottom = Math.max(top, finiteNumber(page?.height) - Math.max(0, finiteNumber(margins.bottom)));

  return {
    left,
    top,
    right,
    bottom,
    width: Math.max(0, right - left),
    height: Math.max(0, bottom - top),
  };
}

export function normalizeObjectGeometry(page, object, position = object) {
  const bounds = getPrintableBounds(page);
  const width = Math.min(bounds.width, Math.max(0, finiteNumber(object?.width)));
  const height = Math.min(bounds.height, Math.max(0, finiteNumber(object?.height)));
  const maxX = Math.max(bounds.left, bounds.right - width);
  const maxY = Math.max(bounds.top, bounds.bottom - height);

  return {
    width: roundMillimeters(width),
    height: roundMillimeters(height),
    x: roundMillimeters(Math.min(maxX, Math.max(bounds.left, finiteNumber(position?.x, bounds.left)))),
    y: roundMillimeters(Math.min(maxY, Math.max(bounds.top, finiteNumber(position?.y, bounds.top)))),
  };
}

export function clampObjectPosition(page, object, position) {
  const geometry = normalizeObjectGeometry(page, object, position);
  return { x: geometry.x, y: geometry.y };
}

export function objectsOverlap(left, right, gap = 0) {
  if (!left || !right || left.visible === false || right.visible === false) {
    return false;
  }

  const safeGap = Math.max(0, finiteNumber(gap));
  const leftX = finiteNumber(left.x);
  const leftY = finiteNumber(left.y);
  const rightX = finiteNumber(right.x);
  const rightY = finiteNumber(right.y);
  return (
    leftX < rightX + finiteNumber(right.width) + safeGap &&
    leftX + finiteNumber(left.width) + safeGap > rightX &&
    leftY < rightY + finiteNumber(right.height) + safeGap &&
    leftY + finiteNumber(left.height) + safeGap > rightY
  );
}

export function findAvailablePosition(page, block, objects = page?.objects || [], options = {}) {
  const gap = Math.max(0, finiteNumber(options.gap, DEFAULT_OBJECT_GAP));
  const bounds = getPrintableBounds(page);
  const geometry = normalizeObjectGeometry(page, block, {
    x: options.startX ?? bounds.left,
    y: options.startY ?? bounds.top,
  });
  const visibleObjects = objects.filter((item) => item.visible !== false && item.id !== block.id);
  let candidateY = Math.max(bounds.top, geometry.y);

  while (candidateY + geometry.height <= bounds.bottom + 0.001) {
    const candidate = {
      ...block,
      x: geometry.x,
      y: candidateY,
      width: geometry.width,
      height: geometry.height,
    };
    const collisions = visibleObjects.filter((item) => objectsOverlap(candidate, item, gap));

    if (collisions.length === 0) {
      return { x: geometry.x, y: roundMillimeters(candidateY) };
    }

    candidateY = Math.max(
      candidateY + gap,
      ...collisions.map((item) => finiteNumber(item.y) + finiteNumber(item.height) + gap),
    );
  }

  return null;
}

function getPreferredInsertionY(page, objects, gap) {
  const bounds = getPrintableBounds(page);
  const visibleObjects = objects.filter((item) => item.visible !== false);

  if (visibleObjects.length === 0) {
    return bounds.top;
  }

  return Math.max(
    bounds.top,
    ...visibleObjects.map((item) => finiteNumber(item.y) + finiteNumber(item.height) + gap),
  );
}

export function createNextDocumentPage(definition, sourcePageId = null) {
  const pages = definition?.pages || [];
  const source = pages.find((page) => page.id === sourcePageId) || pages[pages.length - 1] || {};
  let sequence = pages.length + 1;
  let id = `page-${sequence}`;
  const existingIds = new Set(pages.map((page) => page.id));

  while (existingIds.has(id)) {
    sequence += 1;
    id = `page-${sequence}`;
  }

  return createPageObject({
    id,
    size: source.size || definition?.document?.page_size || 'A4',
    orientation: source.orientation || definition?.document?.orientation || 'portrait',
    ...(Number.isFinite(Number(source.width)) ? { width: Number(source.width) } : {}),
    ...(Number.isFinite(Number(source.height)) ? { height: Number(source.height) } : {}),
    margins: source.margins || definition?.document?.margins,
    background: source.background || definition?.document?.background || '#ffffff',
    repeatable_header: source.repeatable_header ?? null,
    repeatable_footer: source.repeatable_footer ?? null,
    objects: [],
  });
}

export function calculateInsertionPosition(definition, block, options = {}) {
  const gap = Math.max(0, finiteNumber(options.gap, DEFAULT_OBJECT_GAP));
  const pages = definition?.pages || [];
  if (pages.length === 0) {
    const firstPage = createNextDocumentPage(definition);
    const firstPosition = findAvailablePosition(firstPage, block, [], { gap });
    if (!firstPosition) {
      throw new Error(`El objeto ${block.type || block.id} no cabe dentro del área imprimible.`);
    }
    return { page: firstPage, pageIndex: 0, position: firstPosition, createdPage: true };
  }

  const requestedPageIndex = options.targetPageId
    ? pages.findIndex((page) => page.id === options.targetPageId)
    : pages.length - 1;
  const pageIndex = requestedPageIndex >= 0 ? requestedPageIndex : pages.length - 1;
  const page = pages[pageIndex];
  const objects = page.objects || [];
  const position = findAvailablePosition(page, block, objects, {
    gap,
    startX: getPrintableBounds(page).left,
    startY: getPreferredInsertionY(page, objects, gap),
  });

  if (position) {
    return { page, pageIndex, position, createdPage: false };
  }

  const nextPage = createNextDocumentPage(definition, page.id);
  const nextPosition = findAvailablePosition(nextPage, block, [], { gap });

  if (!nextPosition) {
    throw new Error(`El objeto ${block.type || block.id} no cabe dentro del área imprimible.`);
  }

  return { page: nextPage, pageIndex: pageIndex + 1, position: nextPosition, createdPage: true };
}

export function insertObjectIntelligently(definition, sourceBlock, options = {}) {
  const placement = calculateInsertionPosition(definition, sourceBlock, options);
  const geometry = normalizeObjectGeometry(placement.page, sourceBlock, placement.position);
  const existingObjects = placement.page.objects || [];
  const block = {
    ...sourceBlock,
    ...geometry,
    page_id: placement.page.id,
    rotation: finiteNumber(sourceBlock.rotation),
    z_index: Math.max(0, ...existingObjects.map((item) => finiteNumber(item.z_index))) + 1,
  };
  const targetPage = { ...placement.page, objects: [...existingObjects, block] };
  const pages = placement.createdPage
    ? (() => {
        const nextPages = [...(definition.pages || [])];
        nextPages.splice(placement.pageIndex, 0, targetPage);
        return nextPages;
      })()
    : definition.pages.map((page, index) => index === placement.pageIndex ? targetPage : page);

  return {
    definition: { ...definition, pages },
    block,
    pageIndex: placement.pageIndex,
    createdPage: placement.createdPage,
  };
}

export function getObjectGroupBounds(objects = []) {
  if (!objects.length) {
    return null;
  }

  const left = Math.min(...objects.map((object) => finiteNumber(object.x)));
  const top = Math.min(...objects.map((object) => finiteNumber(object.y)));
  const right = Math.max(...objects.map((object) => finiteNumber(object.x) + finiteNumber(object.width)));
  const bottom = Math.max(...objects.map((object) => finiteNumber(object.y) + finiteNumber(object.height)));
  return { left, top, right, bottom, width: right - left, height: bottom - top };
}

export function calculateGroupMoveDelta(page, objects, requestedDelta = {}) {
  const group = getObjectGroupBounds(objects);
  if (!group) return { x: 0, y: 0 };
  const bounds = getPrintableBounds(page);
  const minX = bounds.left - group.left;
  const maxX = bounds.right - group.right;
  const minY = bounds.top - group.top;
  const maxY = bounds.bottom - group.bottom;
  return {
    x: roundMillimeters(Math.min(maxX, Math.max(minX, finiteNumber(requestedDelta.x)))),
    y: roundMillimeters(Math.min(maxY, Math.max(minY, finiteNumber(requestedDelta.y)))),
  };
}

function groupPlacementIsAvailable(page, objects, existingObjects, delta, gap) {
  const bounds = getPrintableBounds(page);
  return objects.every((object) => {
    const candidate = { ...object, x: finiteNumber(object.x) + delta.x, y: finiteNumber(object.y) + delta.y };
    const inside = candidate.x >= bounds.left && candidate.y >= bounds.top && candidate.x + finiteNumber(candidate.width) <= bounds.right + 0.001 && candidate.y + finiteNumber(candidate.height) <= bounds.bottom + 0.001;
    return inside && !existingObjects.some((existing) => objectsOverlap(candidate, existing, gap));
  });
}

export function calculateGroupPastePosition(page, objects, existingObjects = page?.objects || [], options = {}) {
  const group = getObjectGroupBounds(objects);
  if (!group) return null;
  const bounds = getPrintableBounds(page);
  if (group.width > bounds.width || group.height > bounds.height) return null;
  const gap = Math.max(0, finiteNumber(options.gap, DEFAULT_OBJECT_GAP));
  const offset = finiteNumber(options.offset, 4);
  const desired = calculateGroupMoveDelta(page, objects, { x: offset, y: offset });
  if (groupPlacementIsAvailable(page, objects, existingObjects, desired, gap)) return desired;

  const leftDelta = bounds.left - group.left;
  const maxY = bounds.bottom - group.height;
  for (let y = bounds.top; y <= maxY + 0.001; y += Math.max(1, gap)) {
    const candidate = { x: roundMillimeters(leftDelta), y: roundMillimeters(y - group.top) };
    if (groupPlacementIsAvailable(page, objects, existingObjects, candidate, gap)) return candidate;
  }
  return null;
}

export function pasteObjectGroup(definition, sourceObjects, targetPageId, options = {}) {
  if (!sourceObjects?.length) return null;
  const pages = definition.pages || [];
  const requestedIndex = pages.findIndex((page) => page.id === targetPageId);
  const targetIndex = requestedIndex >= 0 ? requestedIndex : Math.max(0, pages.length - 1);
  let page = pages[targetIndex];
  let pageIndex = targetIndex;
  let createdPage = false;
  let delta = calculateGroupPastePosition(page, sourceObjects, page.objects || [], options);

  if (!delta) {
    page = createNextDocumentPage(definition, page?.id);
    pageIndex = targetIndex + 1;
    createdPage = true;
    delta = calculateGroupPastePosition(page, sourceObjects, [], { ...options, offset: 0 });
  }
  if (!delta) throw new Error('La selección no cabe dentro del área imprimible.');

  const pastedObjects = sourceObjects.map((source, index) => ({
    ...deepClone(source),
    id: createCanvasObjectId(source.type),
    page_id: page.id,
    x: roundMillimeters(finiteNumber(source.x) + delta.x),
    y: roundMillimeters(finiteNumber(source.y) + delta.y),
    z_index: Math.max(0, ...(page.objects || []).map((item) => finiteNumber(item.z_index))) + index + 1,
  }));
  const targetPage = { ...page, objects: [...(page.objects || []), ...pastedObjects] };
  const nextPages = [...pages];
  if (createdPage) nextPages.splice(pageIndex, 0, targetPage);
  else nextPages[pageIndex] = targetPage;

  return {
    definition: { ...definition, pages: nextPages },
    objects: pastedObjects,
    page: targetPage,
    pageIndex,
    createdPage,
  };
}

export function insertBlankPageAfter(definition, sourcePageId) {
  const pages = definition.pages || [];
  const sourceIndex = pages.findIndex((page) => page.id === sourcePageId);
  const insertIndex = sourceIndex >= 0 ? sourceIndex + 1 : pages.length;
  const page = createNextDocumentPage(definition, sourcePageId);
  const nextPages = [...pages];
  nextPages.splice(insertIndex, 0, page);
  return { definition: { ...definition, pages: nextPages }, page, pageIndex: insertIndex };
}

export function duplicateDocumentPage(definition, pageId) {
  const pages = definition.pages || [];
  const sourceIndex = pages.findIndex((page) => page.id === pageId);
  if (sourceIndex < 0) return null;
  const source = pages[sourceIndex];
  const shell = createNextDocumentPage(definition, source.id);
  const page = {
    ...deepClone(source),
    id: shell.id,
    margins: deepClone(source.margins),
    objects: (source.objects || []).map((object) => ({
      ...deepClone(object),
      id: createCanvasObjectId(object.type),
      page_id: shell.id,
    })),
  };
  const nextPages = [...pages];
  nextPages.splice(sourceIndex + 1, 0, page);
  return { definition: { ...definition, pages: nextPages }, page, pageIndex: sourceIndex + 1 };
}

function normalizeObjectAfterPageResize(page, object) {
  const bounds = getPrintableBounds(page);
  let width = finiteNumber(object.width);
  let height = finiteNumber(object.height);
  if ((object.preserve_aspect_ratio || object.type === 'image') && width > 0 && height > 0) {
    const scale = Math.min(1, bounds.width / width, bounds.height / height);
    width *= scale;
    height *= scale;
  }
  return { ...object, ...normalizeObjectGeometry(page, { ...object, width, height }) };
}

export function resizeDocumentPage(definition, pageId, settings) {
  const size = settings.size || 'A4';
  const orientation = settings.orientation || 'portrait';
  const pages = definition.pages.map((page) => {
    if (page.id !== pageId) return page;
    const dimensions = size === 'CUSTOM'
      ? settings.swapDimensions
        ? { width: page.height, height: page.width }
        : {
            width: Math.min(1000, Math.max(50, finiteNumber(settings.customWidth, page.width))),
            height: Math.min(1000, Math.max(50, finiteNumber(settings.customHeight, page.height))),
          }
      : getPageDimensions({ size, orientation });
    const resizedPage = { ...page, size, orientation, width: dimensions.width, height: dimensions.height };
    return { ...resizedPage, objects: (page.objects || []).map((object) => normalizeObjectAfterPageResize(resizedPage, object)) };
  });
  return { ...definition, pages };
}
