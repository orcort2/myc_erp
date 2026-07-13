import { officialFieldSheetTemplates } from '../constants/officialFieldSheetTemplates.js';

const normalize = (value) => String(value || '')
  .normalize('NFD')
  .replace(/[\u0300-\u036f]/g, '')
  .toLowerCase()
  .replace(/[^a-z0-9]+/g, ' ')
  .trim();

// Catálogo declarativo: puede sustituirse por configuración backend sin tocar el componente.
export const fieldSheetTemplateMappings = Object.freeze([
  ['tld 6 canales', 'tld_6_canales'], ['temperatura lectura directa 6 canales', 'tld_6_canales'],
  ['temperatura lectura directa', 'tld'], ['tld', 'tld'],
  ['detector de gases', 'detector_gases'], ['valvula de seguridad', 'valvula_seguridad'],
  ['verificacion de equipos', 'verificacion_equipos'], ['maestro de altura', 'maestro_altura'],
  ['par torsional', 'par_torsional'], ['torquimetro', 'par_torsional'],
  ['bascula', 'bascula'], ['balanza', 'bascula'], ['calibrador', 'calibradores'], ['vernier', 'calibradores'],
  ['anemometro', 'anemometro'], ['angulimetro', 'angulimetro'], ['cronometro', 'cronometro'],
  ['indicador de caratula', 'dimensional'], ['micrometro', 'dimensional'], ['medidor de espesores', 'dimensional'],
  ['multimetro', 'electrica'], ['amperimetro', 'electrica'], ['megaohmetro', 'electrica'], ['electrica', 'electrica'],
  ['flujo', 'flujo'], ['presion', 'presion'], ['manometro', 'presion'], ['vacuometro', 'presion'],
  ['pesas', 'pesas'], ['peso patron', 'pesas'], ['regla', 'reglas'], ['sonometro', 'sonido'], ['sonido', 'sonido'],
  ['tacometro', 'tacometro'], ['temperatura', 'temperatura'], ['termometro', 'temperatura'], ['copa', 'copa'],
]);

export function suggestOfficialFieldSheetTemplate({ serviceType, instrumentType, magnitude, equipmentName } = {}) {
  const candidates = [serviceType, instrumentType, magnitude, equipmentName].map(normalize).filter(Boolean);
  for (const candidate of candidates) {
    const mapping = fieldSheetTemplateMappings.find(([term]) => candidate.includes(term));
    if (mapping && officialFieldSheetTemplates[mapping[1]]) {
      return { templateKey: mapping[1], matchedBy: mapping[0] };
    }
  }
  return { templateKey: '', matchedBy: '' };
}
