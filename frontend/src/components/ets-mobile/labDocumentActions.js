// Acciones documentales sobre PDFs oficiales LAB (OT final y Hojas de Campo
// finales). La fuente es siempre el PDF congelado del backend: ver e imprimir
// usan el visor PDF del navegador (nunca el DOM del modal ni una impresión
// de HTML); descargar conserva el nombre enviado por el servidor.
import {
  downloadServiceOrderMobileFieldSheetPdf,
  downloadServiceOrderMobileWorkOrderPdf,
} from '../../services/api.js';
import { openQuotationPdfWindow } from '../../utils/quotationPdfWindow.js';

const BLOCKED_MESSAGE = 'Permite las ventanas emergentes para abrir el PDF oficial LAB.';

export function workOrderPdfLoader(serviceOrderId, workOrderId) {
  return () => downloadServiceOrderMobileWorkOrderPdf(serviceOrderId, workOrderId);
}

export function fieldSheetPdfLoader(serviceOrderId, fieldSheetId) {
  return () => downloadServiceOrderMobileFieldSheetPdf(serviceOrderId, fieldSheetId);
}

export function viewLabPdf(loadPdf, onError) {
  return openQuotationPdfWindow(loadPdf, { onError, blockedMessage: BLOCKED_MESSAGE });
}

export function printLabPdf(loadPdf, onError) {
  return openQuotationPdfWindow(loadPdf, { print: true, onError, blockedMessage: BLOCKED_MESSAGE });
}

export async function downloadLabPdf(loadPdf, fallbackFilename) {
  const { blob, filename } = await loadPdf();
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename && !['null', 'undefined'].includes(filename) ? filename : fallbackFilename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  return link.download;
}
