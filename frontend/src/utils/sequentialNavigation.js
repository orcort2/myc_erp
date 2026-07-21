export function getSequentialNavigationState(itemIds = [], activeItemId = null) {
  const currentIndex = itemIds.findIndex((itemId) => Number(itemId) === Number(activeItemId));
  return {
    currentIndex,
    previousId: currentIndex > 0 ? itemIds[currentIndex - 1] : null,
    nextId: currentIndex >= 0 && currentIndex < itemIds.length - 1 ? itemIds[currentIndex + 1] : null,
  };
}

