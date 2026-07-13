const PAGE_CAPACITY = 920;
const TABLE_HEADER_COST = 34;
const TABLE_ROW_COST = 18;

function blockCost(block) {
  const type = String(block?.block_type || '').toLowerCase();
  if (type.includes('clientblock') || type.includes('generaldatablock')) return 58;
  if (type.includes('equipmentblock') || type.includes('equipmentdatablock')) return 92;
  if (type.includes('calibrationdatablock')) return 50;
  if (type.includes('environmentalblock')) return 42;
  if (type.includes('observationsblock')) return 78;
  if (type.includes('signaturesblock')) return 112;
  if (type.includes('controlleddiagramblock')) return 150;
  return 62;
}

function isTableBlock(block) {
  return String(block?.block_type || '').includes('TableBlock') || block?.block_type === 'ResultsTableBlock';
}

function createPage() {
  return { units: [], used: 0 };
}

export function paginateFieldSheet(blocks = [], resultSections = [], options = {}) {
  const capacity = Number(options.capacity) || PAGE_CAPACITY;
  const sectionsByKey = Object.fromEntries((resultSections || []).map((item) => [item.key, item]));
  const pages = [createPage()];

  function currentPage() {
    return pages[pages.length - 1];
  }

  function newPage() {
    if (!currentPage().units.length) return currentPage();
    const page = createPage();
    pages.push(page);
    return page;
  }

  function addUnit(unit, cost, forceBreak = false) {
    if (forceBreak) newPage();
    if (currentPage().units.length && currentPage().used + cost > capacity) newPage();
    currentPage().units.push(unit);
    currentPage().used += cost;
  }

  for (const block of blocks) {
    if (block.visible === false || block.capture_visible === false) continue;
    if (block.block_type === 'HeaderBlock' || block.block_type === 'FooterBlock') continue;

    if (!isTableBlock(block)) {
      addUnit({ kind: 'block', block }, blockCost(block), Boolean(block.metadata?.break_before));
      continue;
    }

    const sections = block.sections?.length
      ? block.sections.map((section) => ({ ...section, rows: sectionsByKey[section.key]?.rows || [] }))
      : [{ ...(sectionsByKey[block.key] || {}), key: block.key, title: block.title }];

    for (const section of sections) {
      const allRows = section.rows || [];
      let cursor = 0;
      let continuation = false;
      let renderedEmpty = false;
      if (section.metadata?.break_before) newPage();

      do {
        const available = capacity - currentPage().used - TABLE_HEADER_COST;
        const rowsThatFit = Math.max(1, Math.floor(available / TABLE_ROW_COST));
        if (allRows.length && rowsThatFit < Math.min(2, allRows.length - cursor) && currentPage().units.length) {
          newPage();
          continue;
        }
        const take = allRows.length ? Math.min(allRows.length - cursor, Math.max(1, rowsThatFit)) : 0;
        const pageRows = allRows.slice(cursor, cursor + take);
        const cost = TABLE_HEADER_COST + Math.max(1, pageRows.length) * TABLE_ROW_COST;
        addUnit({ kind: 'table', block, section: { ...section, rows: pageRows }, continuation }, cost);
        cursor += take;
        if (!allRows.length) renderedEmpty = true;
        continuation = true;
        if (cursor < allRows.length) newPage();
      } while (cursor < allRows.length || (!allRows.length && !renderedEmpty));
    }
  }

  return pages.filter((page) => page.units.length).map((page, index, allPages) => ({
    ...page,
    pageNumber: index + 1,
    pageCount: allPages.length,
  }));
}

export const fieldSheetPaginationMetrics = Object.freeze({
  pageCapacity: PAGE_CAPACITY,
  tableHeaderCost: TABLE_HEADER_COST,
  tableRowCost: TABLE_ROW_COST,
});
