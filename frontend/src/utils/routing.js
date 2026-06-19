export function getCurrentPath() {
  const pathname = window.location.pathname === '/' ? '/dashboard' : window.location.pathname;
  return `${pathname}${window.location.hash}`;
}

export function navigate(path) {
  window.history.pushState({}, '', path);
  window.dispatchEvent(new PopStateEvent('popstate'));
}
