/**
 * Autosave silencioso del borrador de un TechnicalReport.
 *
 * Comparte el PATRÓN del autosave de FieldSheet (debounce, un guardado en
 * vuelo, generación de contexto, fallo visible sin perder cambios) pero NO su
 * autoridad: es un módulo propio y no importa nada de field-sheet-autosave.
 * Sólo persiste `capture_values`; folio, tipo, revisión, firma, PDF y
 * responsable nunca pasan por aquí.
 *
 * - change() guarda el último valor, marca dirty y reprograma el debounce:
 *   jamás hay un PATCH por tecla.
 * - Un solo PATCH en vuelo. Lo que cambie durante el vuelo sigue dirty y se
 *   guarda después, en orden.
 * - Un fallo conserva dirty y los valores locales; el siguiente change() o
 *   flush() reintenta.
 * - leave() persiste lo pendiente; sólo si queda guardado invalida el
 *   contexto. Si falla no se pierde nada y se bloquea la salida.
 */

export const TECHNICAL_REPORT_AUTOSAVE_DEBOUNCE_MS = 800;

export type TechnicalReportAutosaveStatus = 'idle' | 'dirty' | 'saving' | 'saved' | 'error';

export type TechnicalReportAutosaveOptions<TValues, TResult> = {
  debounceMs?: number;
  /** Persiste `values`. Debe lanzar si falla. */
  save(values: TValues): Promise<TResult>;
  /** Sólo se invoca para resultados vigentes (mismo contexto, no obsoletos). */
  onSaved?(result: TResult): void;
  onStatusChange?(status: TechnicalReportAutosaveStatus, error?: unknown): void;
  setTimer?(callback: () => void, ms: number): unknown;
  clearTimer?(handle: unknown): void;
};

export type TechnicalReportAutosave<TValues> = {
  change(values: TValues): void;
  /** Persiste de inmediato lo pendiente. true si todo quedó guardado. */
  flush(): Promise<boolean>;
  /** Salir del contexto: true si todo quedó guardado (contexto invalidado). */
  leave(): Promise<boolean>;
  /** El contexto cambió: una respuesta en vuelo deja de aplicarse. */
  invalidateContext(): void;
  isDirty(): boolean;
  getStatus(): TechnicalReportAutosaveStatus;
};

export function createTechnicalReportAutosave<TValues, TResult>(
  options: TechnicalReportAutosaveOptions<TValues, TResult>,
): TechnicalReportAutosave<TValues> {
  const debounceMs = options.debounceMs ?? TECHNICAL_REPORT_AUTOSAVE_DEBOUNCE_MS;
  const setTimer = options.setTimer ?? ((callback, ms) => setTimeout(callback, ms));
  const clearTimer = options.clearTimer ?? ((handle) => clearTimeout(handle as ReturnType<typeof setTimeout>));

  let latest: TValues | undefined;
  let changeVersion = 0;
  let savedVersion = 0;
  let issuedSeq = 0;
  let lastAppliedSeq = 0;
  let generation = 0;
  let timer: unknown = null;
  let inFlight: { promise: Promise<boolean>; generation: number } | null = null;
  let status: TechnicalReportAutosaveStatus = 'idle';

  const dirty = () => changeVersion > savedVersion;
  const currentFlight = () => inFlight;

  function setStatus(next: TechnicalReportAutosaveStatus, error?: unknown) {
    status = next;
    options.onStatusChange?.(next, error);
  }

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

  function run(): Promise<boolean> {
    if (inFlight) return inFlight.promise;
    if (!dirty() || latest === undefined) return Promise.resolve(true);
    const values = latest;
    const versionAtStart = changeVersion;
    const seq = ++issuedSeq;
    const startedGeneration = generation;
    setStatus('saving');
    let current!: Promise<boolean>;
    current = (async () => {
      await Promise.resolve();
      try {
        const result = await options.save(values);
        if (startedGeneration !== generation) {
          if (dirty() && timer === null) schedule();
          return true;
        }
        savedVersion = Math.max(savedVersion, versionAtStart);
        if (seq > lastAppliedSeq) {
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
      latest = values;
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
          if (!ok && flight.generation === generation) return false;
          continue;
        }
        if (!dirty()) return true;
        if (!(await run())) return false;
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
      latest = undefined;
      changeVersion = 0;
      savedVersion = 0;
      setStatus('idle');
    },
    isDirty: dirty,
    getStatus: () => status,
  };
}
