/**
 * Fuente monocromática de 5x7 puntos, autoría propia para este proyecto --
 * NO es una copia de ningún archivo de fuente de terceros (evita cualquier
 * cuestión de licencia; ver AGENTS.md/no-copiar-de-terceros en la auditoría
 * del protocolo NIIMBOT). Cada glifo se escribe como arte ASCII directamente
 * verificable a simple vista ('#' = tinta, '.' = sin tinta), en vez de bytes
 * hexadecimales opacos -- un error de tipeo se nota mirando la forma.
 *
 * Cobertura deliberadamente acotada al vocabulario real de la etiqueta LAB:
 * 0-9, A-Z, espacio, '.', ':', '/', '-'. renderText() normaliza a mayúsculas
 * y sustituye cualquier carácter fuera de este set por un glifo de reemplazo
 * visible (nunca lo omite en silencio -- ver UNKNOWN_GLYPH).
 */

export const GLYPH_WIDTH = 5;
export const GLYPH_HEIGHT = 7;

type GlyphRows = readonly [string, string, string, string, string, string, string];

const UNKNOWN_GLYPH: GlyphRows = [
  '#####',
  '#...#',
  '....#',
  '...#.',
  '..#..',
  '.....',
  '..#..',
];

const GLYPHS: Record<string, GlyphRows> = {
  '0': ['.###.', '#...#', '#..##', '#.#.#', '##..#', '#...#', '.###.'],
  '1': ['..#..', '.##..', '..#..', '..#..', '..#..', '..#..', '.###.'],
  '2': ['.###.', '#...#', '....#', '...#.', '..#..', '.#...', '#####'],
  '3': ['.###.', '#...#', '....#', '..##.', '....#', '#...#', '.###.'],
  '4': ['...#.', '..##.', '.#.#.', '#..#.', '#####', '...#.', '...#.'],
  '5': ['#####', '#....', '####.', '....#', '....#', '#...#', '.###.'],
  '6': ['..##.', '.#...', '#....', '####.', '#...#', '#...#', '.###.'],
  '7': ['#####', '....#', '...#.', '..#..', '.#...', '.#...', '.#...'],
  '8': ['.###.', '#...#', '#...#', '.###.', '#...#', '#...#', '.###.'],
  '9': ['.###.', '#...#', '#...#', '.####', '....#', '...#.', '.##..'],
  A: ['..#..', '.#.#.', '#...#', '#...#', '#####', '#...#', '#...#'],
  B: ['####.', '#...#', '#...#', '####.', '#...#', '#...#', '####.'],
  C: ['.####', '#....', '#....', '#....', '#....', '#....', '.####'],
  D: ['####.', '#...#', '#...#', '#...#', '#...#', '#...#', '####.'],
  E: ['#####', '#....', '#....', '####.', '#....', '#....', '#####'],
  F: ['#####', '#....', '#....', '####.', '#....', '#....', '#....'],
  G: ['.####', '#....', '#....', '#.###', '#...#', '#...#', '.###.'],
  H: ['#...#', '#...#', '#...#', '#####', '#...#', '#...#', '#...#'],
  I: ['.###.', '..#..', '..#..', '..#..', '..#..', '..#..', '.###.'],
  J: ['...##', '....#', '....#', '....#', '....#', '#...#', '.###.'],
  K: ['#...#', '#..#.', '#.#..', '##...', '#.#..', '#..#.', '#...#'],
  L: ['#....', '#....', '#....', '#....', '#....', '#....', '#####'],
  M: ['#...#', '##.##', '#.#.#', '#...#', '#...#', '#...#', '#...#'],
  N: ['#...#', '##..#', '#.#.#', '#..##', '#...#', '#...#', '#...#'],
  O: ['.###.', '#...#', '#...#', '#...#', '#...#', '#...#', '.###.'],
  P: ['####.', '#...#', '#...#', '####.', '#....', '#....', '#....'],
  Q: ['.###.', '#...#', '#...#', '#...#', '#.#.#', '#..#.', '.##.#'],
  R: ['####.', '#...#', '#...#', '####.', '#.#..', '#..#.', '#...#'],
  S: ['.####', '#....', '#....', '.###.', '....#', '....#', '####.'],
  T: ['#####', '..#..', '..#..', '..#..', '..#..', '..#..', '..#..'],
  U: ['#...#', '#...#', '#...#', '#...#', '#...#', '#...#', '.###.'],
  V: ['#...#', '#...#', '#...#', '#...#', '#...#', '.#.#.', '..#..'],
  W: ['#...#', '#...#', '#...#', '#.#.#', '#.#.#', '#.#.#', '.#.#.'],
  X: ['#...#', '#...#', '.#.#.', '..#..', '.#.#.', '#...#', '#...#'],
  Y: ['#...#', '#...#', '.#.#.', '..#..', '..#..', '..#..', '..#..'],
  Z: ['#####', '....#', '...#.', '..#..', '.#...', '#....', '#####'],
  ' ': ['.....', '.....', '.....', '.....', '.....', '.....', '.....'],
  '.': ['.....', '.....', '.....', '.....', '.....', '.##..', '.##..'],
  ':': ['.....', '.##..', '.##..', '.....', '.##..', '.##..', '.....'],
  '/': ['....#', '...#.', '...#.', '..#..', '.#...', '.#...', '#....'],
  '-': ['.....', '.....', '.....', '#####', '.....', '.....', '.....'],
};

/** Quita diacríticos (á->a, ñ->n vía descomposición NFD) antes de mayuscular
 * -- la fuente no tiene glifos acentuados; esto evita que un folio o
 * identificación con acento caiga silenciosamente en UNKNOWN_GLYPH. */
function stripDiacritics(value: string): string {
  return value.normalize('NFD').replace(/[\u0300-\u036f]/g, '');
}

export function glyphFor(char: string): GlyphRows {
  return GLYPHS[char] ?? UNKNOWN_GLYPH;
}

/** Normaliza el texto de entrada al alfabeto soportado por la fuente.
 * Nunca se usa para decidir contenido de negocio, sólo presentación. */
export function normalizeForBitmapFont(value: string): string {
  return stripDiacritics(value).toUpperCase();
}
