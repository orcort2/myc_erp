// Reserve the tab during the click, before awaiting the authenticated request.
// Shared by every authenticated PDF viewer/printer of the ERP (quotations and
// the official LAB documents shown in the ETS); it never prints HTML.
export async function openQuotationPdfWindow(
  loadPdf,
  { print = false, onError, blockedMessage = 'Permite las ventanas emergentes para abrir el PDF de la cotización.' } = {},
) {
  // Keep the navigation handle, but immediately detach the opener.
  const pdfWindow = window.open('about:blank', '_blank');
  if (!pdfWindow) {
    throw new Error(blockedMessage);
  }
  pdfWindow.opener = null;
  let objectUrl;
  let stopWatching = () => {};
  try {
    const { blob, filename } = await loadPdf();
    if (pdfWindow.closed) return null;
    objectUrl = URL.createObjectURL(blob);
    let loadPoll;
    let deadline;
    const handleLoad = () => {
      if (pdfWindow.closed) return;
      try {
        // Ignore the initial blank document and isolated native viewers.
        if (pdfWindow.location.href !== objectUrl) return;
        pdfWindow.addEventListener('pagehide', (event) => {
          // A cached page can be restored and still needs its Blob.
          if (!event.persisted) URL.revokeObjectURL(objectUrl);
        }, { once: true });
      } catch {
        return;
      }
      stopWatching();
      if (print) {
        try {
          pdfWindow.focus();
          pdfWindow.print();
        } catch {
          onError?.(new Error('El PDF está abierto. Usa la opción Imprimir del visor PDF.'));
        }
      }
    };
    stopWatching = () => {
      window.clearInterval(loadPoll);
      window.clearTimeout(deadline);
      pdfWindow.removeEventListener('load', handleLoad);
    };
    // Navigation may discard the blank window's load listener. Poll only
    // during this bounded load phase, never during the viewer's lifetime.
    loadPoll = window.setInterval(() => {
      if (pdfWindow.closed) {
        stopWatching();
        URL.revokeObjectURL(objectUrl);
        return;
      }
      try {
        if (pdfWindow.document?.readyState === 'complete') handleLoad();
      } catch {
        // The deadline handles native viewers that isolate their document.
      }
    }, 1000);
    deadline = window.setTimeout(() => {
      stopWatching();
      if (pdfWindow.closed) URL.revokeObjectURL(objectUrl);
      else if (print) {
        onError?.(new Error('El visor no confirmó la carga. Cuando termine, usa su opción Imprimir.'));
      }
    }, 60000);
    pdfWindow.addEventListener('load', handleLoad);
    pdfWindow.location.replace(objectUrl);
    // If pagehide is unavailable (native viewer), retain the URL: the browser
    // releases URLs when their creating document unloads. No expiry revokes
    // a PDF that might still be displayed, saved or printed.
    return { filename };
  } catch (error) {
    stopWatching();
    if (!pdfWindow.closed) pdfWindow.close();
    if (objectUrl) URL.revokeObjectURL(objectUrl);
    throw error;
  }
}
