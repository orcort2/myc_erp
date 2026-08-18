const MAX_RECONNECT_DELAY_MS = 30_000;

export function reconnectDelayMs(attempt: number, random = Math.random): number {
  const exponential = Math.min(1_000 * (2 ** Math.max(0, attempt)), MAX_RECONNECT_DELAY_MS);
  const jitter = Math.floor(exponential * 0.2 * random());
  return Math.min(exponential + jitter, MAX_RECONNECT_DELAY_MS);
}

export function shouldRetryClose(code: number): boolean {
  return code !== 1000 && code !== 1008 && code !== 4403;
}
