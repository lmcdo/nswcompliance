/**
 * fetch with a hard deadline that covers the WHOLE reply, inside one time limit for the lookup.
 *
 * One stalled NSW map call used to hold the whole /api/property response until the 30 s gateway
 * limit (bushfire stalled 40 s on 2026-10-21). The old timer stopped when the first bytes arrived,
 * so a reply that stalled mid-body still hung. Now the timer stays live until the body is read
 * (the lib/lot-adjacency.ts `post()` pattern), and every call also stops when the lookup's own
 * time limit (`withLookupBudget`) runs out. A timed-out call REJECTS — callers must treat that as
 * "not checked", never as "the map found nothing".
 *
 * prior-art-checked: reuse not viable because services/arcgis_client.py is Python; grep of
 * frontend-nextjs/lib + app found no TS fetchWithTimeout/withTimeout helper.
 */
import { AsyncLocalStorage } from 'node:async_hooks';

export const MAP_LOOKUP_TIMEOUT_MS = 8000;

const budget = new AsyncLocalStorage<AbortSignal>();

export const LOOKUP_OUT_OF_TIME = 'Property lookup ran out of time';
/** After the limit, calls that saw the signal settle as "not checked" within this grace; then the lookup stops. */
export const LOOKUP_GRACE_MS = 2000;

/**
 * Run `fn` with one time limit: every call made through this file stops when it runs out. Work that
 * cannot see the signal (a database query) is cut off too: past the limit plus a short grace, this
 * REJECTS with LOOKUP_OUT_OF_TIME, so the caller always answers instead of hanging.
 */
export async function withLookupBudget<T>(ms: number, fn: () => Promise<T>): Promise<T> {
  const controller = new AbortController();
  let hardStop: ReturnType<typeof setTimeout> | undefined;
  const timer = setTimeout(() => controller.abort(new Error(`lookup ran out of time after ${ms} ms`)), ms);
  const stopped = new Promise<never>((_, reject) => {
    hardStop = setTimeout(() => reject(new Error(`${LOOKUP_OUT_OF_TIME} after ${ms + LOOKUP_GRACE_MS} ms`)), ms + LOOKUP_GRACE_MS);
  });
  try {
    return await Promise.race([budget.run(controller.signal, fn), stopped]);
  } finally {
    clearTimeout(timer);
    clearTimeout(hardStop);
  }
}

/** `p`, but rejecting once the running lookup is out of time (for work that cannot take a signal). */
export function withinLookupBudget<T>(p: Promise<T>): Promise<T> {
  const outer = budget.getStore();
  if (!outer) return p;
  return new Promise<T>((resolve, reject) => {
    const stop = () => reject(new Error('lookup ran out of time'));
    // Always handle `p`, even when already out of time, so its own failure is never unhandled.
    p.then(resolve, reject).finally(() => outer.removeEventListener('abort', stop));
    if (outer.aborted) stop();
    else outer.addEventListener('abort', stop, { once: true });
  });
}

/** The running lookup's time limit, if any (for code that builds its own signal). */
export function lookupBudgetSignal(): AbortSignal | undefined {
  return budget.getStore();
}

/** Wait `ms`, but stop early (rejecting) when the lookup runs out of time. */
export function lookupSleep(ms: number): Promise<void> {
  const outer = budget.getStore();
  return new Promise((resolve, reject) => {
    if (outer?.aborted) return reject(new Error('lookup ran out of time'));
    const t = setTimeout(() => { outer?.removeEventListener('abort', stop); resolve(); }, ms);
    const stop = () => { clearTimeout(t); reject(new Error('lookup ran out of time')); };
    outer?.addEventListener('abort', stop, { once: true });
  });
}

/** One log line per outside call: which service, how long, and how it ended. */
function logCall(url: string, started: number, result: string): void {
  let service = url;
  try {
    const u = new URL(url);
    service = `${u.host}${u.pathname.replace(/\/query$/, '')}`;
  } catch { /* keep the raw url */ }
  console.log(`[lookup-call] ${service} ${Date.now() - started}ms ${result}`);
}

/**
 * fetch `url` and read its whole body before `ms` (or the lookup's time limit) runs out. Returns a
 * Response whose body is already in memory, so `.json()` / `.text()` on it cannot stall.
 */
export async function fetchWithTimeout(
  url: string,
  init: RequestInit = {},
  ms: number = MAP_LOOKUP_TIMEOUT_MS,
): Promise<Response> {
  const started = Date.now();
  const outer = budget.getStore();
  const controller = new AbortController();
  let timer: ReturnType<typeof setTimeout> | undefined;
  let onOuter: (() => void) | undefined;
  const deadline = new Promise<never>((_, reject) => {
    // Reject BEFORE aborting: the abort also fails the pending body read, and the caller must see
    // "timed out" (which the planning-layers retry looks for), not a bare "aborted".
    timer = setTimeout(() => {
      reject(new Error(`timed out after ${ms} ms`));
      controller.abort();
    }, ms);
    onOuter = () => {
      reject(new Error('lookup ran out of time'));
      controller.abort();
    };
    if (outer?.aborted) onOuter();
    else outer?.addEventListener('abort', onOuter, { once: true });
  });
  deadline.catch(() => {}); // a deadline nobody is waiting on any more is not an error
  try {
    const res = await Promise.race([fetch(url, { ...init, signal: controller.signal }), deadline]);
    // Some fetch stand-ins (test stubs, polyfills) only offer json(); read whichever exists.
    const read = typeof res.text === 'function' ? res.text() : Promise.resolve(res.json()).then((d) => JSON.stringify(d));
    const body = await Promise.race([read, deadline]);
    logCall(url, started, res.status === 429 ? 'rate-limited 429' : res.ok ? `ok ${res.status}` : `failed ${res.status}`);
    return new Response(body, { status: res.status, statusText: res.statusText });
  } catch (error) {
    logCall(url, started, /timed out|out of time/.test(String(error)) ? `timed out (${error})` : `failed (${error})`);
    throw error;
  } finally {
    clearTimeout(timer);
    if (onOuter) outer?.removeEventListener('abort', onOuter);
  }
}

/**
 * Query an ArcGIS layer and return its `features` array. Throws when the call fails, times out,
 * returns a non-2xx status, or returns an error body (ArcGIS answers HTTP 200 with `{error}`), so
 * the caller can tell "no features" (a real No) from "no answer" (not checked).
 */
export async function arcgisFeatures(url: string, ms: number = MAP_LOOKUP_TIMEOUT_MS): Promise<any[]> {
  const res = await fetchWithTimeout(url, {}, ms);
  if (!res.ok) throw new Error(`map returned ${res.status}`);
  const data = await res.json();
  if (!data || data.error || !Array.isArray(data.features)) throw new Error('map returned no feature list');
  return data.features;
}
