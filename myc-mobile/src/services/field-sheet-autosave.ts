import type { LabFieldSheet } from '@/src/types/lab-work-order';

/**
 * Autosave silencioso de la FieldSheet draft/in_progress (sin framework: sólo
 * temporizadores y promesas, para poder probarlo de forma pura).
 *
 * Contrato:
 * - change() actualiza el último valor conocido, marca dirty y reprograma el
 *   debounce; jamás bloquea la escritura.
 * - Un solo guardado en vuelo a la vez (single-flight): dos PATCH concurrentes
 *   podrían aplicarse en orden inverso en el servidor y dejar el valor viejo.
 *   Los cambios que llegan durante un guardado siguen dirty y disparan otro.
 * - Cada guardado lleva un seq monotónico y la generación del contexto
 *   (equipo/hoja). Un resultado sólo es aplicable si su generación sigue
 *   vigente y su seq es mayor al último aplicado (shouldApplySaveResult).
 * - Un fallo nunca limpia dirty ni toca los valores locales; el siguiente
 *   change() o flush() reintenta.
 * - Salir de un contexto tiene tres semánticas distintas (nunca "fingen"
 *   cancelar una petición ya enviada; el HTTP en vuelo sigue existiendo y
 *   single-flight lo respeta incluso entre contextos):
 *     leave()             persiste lo pendiente; sólo si queda guardado
 *                         invalida el contexto. Si falla NO se pierde nada.
 *     invalidateContext() el contexto cambió por una acción programática: una
 *                         respuesta en vuelo deja de ser aplicable a la UI.
 *     discard()           descarta cambios locales aún NO enviados; el PATCH
 *                         ya enviado no se deshace, sólo se espera a que termine.
 * - El autosave NO envía results_rows ni completa la hoja: PATCH sobre la
 *   misma hoja editable (el backend no crea revisión por ello).
 */

export const FIELD_SHEET_AUTOSAVE_DEBOUNCE_MS = 800;

export type AutosaveStatus = 'idle' | 'dirty' | 'saving' | 'saved' | 'error';

export function shouldApplySaveResult(input: {
  seq: number;
  generation: number;
  lastAppliedSeq: number;
  currentGeneration: number;
}): boolean {
  return input.generation === input.currentGeneration && input.seq > input.lastAppliedSeq;
}

export type AutosaveOptions<TValues, TResult> = {
  debounceMs?: number;
  /** Persiste `values`. Debe lanzar si falla. */
  save(values: TValues): Promise<TResult>;
  /** Sólo se invoca para resultados aplicables (no obsoletos). */
  onSaved?(result: TResult): void;
  onStatusChange?(status: AutosaveStatus, error?: unknown): void;
  setTimer?(callback: () => void, ms: number): unknown;
  clearTimer?(handle: unknown): void;
};

export type Autosave<TValues> = {
  change(values: TValues): void;
  /** Persiste de inmediato lo pendiente. true si todo quedó guardado. */
  flush(): Promise<boolean>;
  /** Abandonar el contexto actual: true si quedó todo guardado (y el contexto
   * se invalida); false si el guardado falló -- el draft sigue intacto y dirty. */
  leave(): Promise<boolean>;
  /** El contexto cambió: la respuesta en vuelo ya no es aplicable. No descarta
   * cambios ni abre un guardado concurrente con el que sigue vivo. */
  invalidateContext(): void;
  /** Descarte explícito de cambios locales NO enviados. Resuelve cuando el
   * guardado ya enviado (si hay) terminó; ese PATCH no puede cancelarse. */
  discard(): Promise<void>;
  isDirty(): boolean;
  getStatus(): AutosaveStatus;
};

export function createFieldSheetAutosave<TValues, TResult>(
  options: AutosaveOptions<TValues, TResult>,
): Autosave<TValues> {
  const debounceMs = options.debounceMs ?? FIELD_SHEET_AUTOSAVE_DEBOUNCE_MS;
  const setTimer = options.setTimer ?? ((callback, ms) => setTimeout(callback, ms));
  const clearTimer = options.clearTimer ?? ((handle) => clearTimeout(handle as ReturnType<typeof setTimeout>));

  let latestValues: TValues | undefined;
  let changeVersion = 0;
  let savedVersion = 0;
  let issuedSeq = 0;
  let lastAppliedSeq = 0;
  let generation = 0;
  let timer: unknown = null;
  let inFlight: { promise: Promise<boolean>; generation: number } | null = null;
  let status: AutosaveStatus = 'idle';

  function setStatus(next: AutosaveStatus, error?: unknown) {
    status = next;
    options.onStatusChange?.(next, error);
  }

  const dirty = () => changeVersion > savedVersion;
  const currentFlight = (): { promise: Promise<boolean>; generation: number } | null => inFlight;

  function cancelTimer() {
    if (timer !== null) {
      clearTimer(timer);
      timer = null;
    }
  }

  function schedule() {
    cancelTimer();
    timer = setTimer(() => {
      timer = null;
      void run();
    }, debounceMs);
  }

  /** Un guardado; resuelve true si terminó bien. Nunca lanza. */
  function run(): Promise<boolean> {
    if (inFlight) return inFlight.promise;
    if (!dirty() || latestValues === undefined) return Promise.resolve(true);
    const values = latestValues;
    const versionAtStart = changeVersion;
    const seq = ++issuedSeq;
    const startedGeneration = generation;
    setStatus('saving');
    let current!: Promise<boolean>;
    current = (async () => {
      await Promise.resolve(); // `current` ya asignado antes de cualquier finally
      try {
        const result = await options.save(values);
        if (startedGeneration !== generation) {
          // Contexto cambiado mientras volaba: su respuesta no se aplica, pero
          // lo pendiente del contexto NUEVO (que esperó este vuelo) arranca ya.
          if (dirty() && timer === null) schedule();
          return true;
        }
        savedVersion = Math.max(savedVersion, versionAtStart);
        if (shouldApplySaveResult({ seq, generation: startedGeneration, lastAppliedSeq, currentGeneration: generation })) {
          lastAppliedSeq = seq;
          options.onSaved?.(result);
        }
        if (dirty()) {
          setStatus('dirty');
          if (timer === null) schedule();
        } else {
          setStatus('saved');
        }
        return true;
      } catch (error) {
        if (startedGeneration === generation) setStatus('error', error);
        return false;
      } finally {
        if (currentFlight()?.promise === current) inFlight = null;
      }
    })();
    inFlight = { promise: current, generation: startedGeneration };
    return current;
  }

  return {
    change(values) {
      latestValues = values;
      changeVersion += 1;
      setStatus('dirty');
      schedule();
    },
    async flush() {
      cancelTimer();
      for (;;) {
        if (inFlight) {
          const flight = inFlight;
          const ok = await flight.promise;
          // el fallo de un vuelo de OTRO contexto no es de este draft
          if (!ok && flight.generation === generation) return false;
          continue;
        }
        if (!dirty()) return true;
        const ok = await run();
        if (!ok) return false;
      }
    },
    async leave() {
      if (!(await this.flush())) return false;
      this.invalidateContext();
      return true;
    },
    invalidateContext() {
      cancelTimer();
      generation += 1;
      latestValues = undefined;
      changeVersion = 0;
      savedVersion = 0;
      setStatus('idle');
      // inFlight NO se toca: sigue siendo la petición viva (single-flight).
    },
    async discard() {
      const flight = currentFlight();
      this.invalidateContext();
      if (flight) await flight.promise;
    },
    isDirty: dirty,
    getStatus: () => status,
  };
}

/**
 * Campos de la hoja que el backend es autoridad de refrescar sin que el
 * técnico los edite (reception_date es readonly dentro de la FieldSheet
 * canónica). Se mezclan sobre los valores locales SIN reemplazarlos: la
 * captura aún no persistida sobrevive a cambiar la fecha de recepción.
 */
export const AUTHORITATIVE_REFRESH_KEYS = ['reception_date'] as const;

export function mergeAuthoritativeSheetFields(
  values: Record<string, unknown>,
  refreshed: LabFieldSheet,
  keys: readonly string[] = AUTHORITATIVE_REFRESH_KEYS,
): Record<string, unknown> {
  const source = refreshed as unknown as Record<string, unknown>;
  const next = { ...values };
  for (const key of keys) {
    if (key in source) next[key] = source[key];
  }
  return next;
}

/**
 * Mezcla la respuesta de un autosave en la hoja local: metadatos y columnas
 * del servidor, pero results_rows se conserva tal cual — los Resultados se
 * guardan por su propio camino (saveResultsRows) y un autosave nunca debe
 * pisarlos con una lectura anterior.
 */
export function mergeAutosavedSheet(current: LabFieldSheet | null, saved: LabFieldSheet): LabFieldSheet | null {
  if (!current || current.id !== saved.id) return current; // hoja distinta: respuesta obsoleta
  return { ...saved, results_rows: current.results_rows };
}
