/**
 * fetch with a hard deadline.
 *
 * One stalled NSW map call used to hold the whole /api/property response until the 30 s gateway
 * limit (bushfire stalled 40 s on 2026-10-21). The abort signal stops the request; the race stops
 * the wait even when something ignores the signal. A timed-out call REJECTS — callers must treat
 * that as "not checked", never as "the map found nothing".
 *
 * prior-art-checked: reuse not viable because services/arcgis_client.py is Python; grep of
 * frontend-nextjs/lib + app found no TS fetchWithTimeout/withTimeout helper.
 */
export const MAP_LOOKUP_TIMEOUT_MS = 8000;

export function fetchWithTimeout(
  url: string,
  init: RequestInit = {},
  ms: number = MAP_LOOKUP_TIMEOUT_MS,
): Promise<Response> {
  const controller = new AbortController();
  let timer: ReturnType<typeof setTimeout> | undefined;
  const deadline = new Promise<never>((_, reject) => {
    timer = setTimeout(() => {
      controller.abort();
      reject(new Error(`timed out after ${ms} ms`));
    }, ms);
  });
  return Promise.race([fetch(url, { ...init, signal: controller.signal }), deadline])
    .finally(() => clearTimeout(timer));
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
