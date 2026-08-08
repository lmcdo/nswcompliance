// prior-art-checked: no existing TS client wraps the guarded DCP controls
// read — the ~5 routes each ran their own inline SQL against
// dcp_setback_controls (campaign item 5 census, 2026-08-03). This is the ONE
// module allowed to source those rows, and it does so by proxying the Python
// path (app/api/upzoning/route.ts precedent), so the guard stack — is_current,
// needs_review exclusion, zone filtering, dev-type routing, deterministic
// order, as-at — has exactly one implementation (conveyancing_db.
// fetch_dcp_setbacks). Consumers SHAPE rows; they never re-implement guards.

const PYTHON_API = process.env.PYTHON_API_URL || 'http://localhost:8000';

/** One guarded control row, as served by /pipeline/dcp-controls. */
export interface DcpControlRow {
  type: string;                 // display label
  dev_type: string;
  control_type: 'prescribed' | 'site_derived' | string;
  semantic_type: string;        // front_setback, car_parking, ...
  requirement: string;
  value_min: number | null;
  value_max: number | null;
  unit: string;
  clause: string;
  notes: string;
  source_text: string | null;
  source_chapter_key: string | null;
  pdf_page: number | null;
  dcp_version: string | null;
  // The row's stored applicability constraint, passed through unchanged —
  // consumers must never fabricate a plausible value in its place.
  applicability: string | null;
}

export interface DcpControlsResult {
  available: boolean;
  lga: string;
  reason?: string;
  dcp_name?: string | null;
  dcp_url?: string | null;
  caveat?: string | null;
  clause_ref?: string | null;
  zone_filter_applied?: string | null;
  as_at?: { date: string; precision: string; kind: string | null; basis: string } | null;
  as_at_status?: 'resolved' | 'absent' | 'unavailable' | null;
  as_at_line?: string | null;
  registry_pdf_urls?: Record<string, string>;
  rows?: DcpControlRow[];
}

/** Thrown when the guarded source could not be reached — callers convert
 * this to their route's own visible degraded/error shape, never to an empty
 * success (three states: rows / checked-none / source-unavailable). */
export class DcpControlsUnavailableError extends Error {}

export async function fetchDcpControls(
  lga: string,
  zone?: string | null,
): Promise<DcpControlsResult> {
  const params = new URLSearchParams({ lga });
  if (zone) params.set('zone', zone);
  let res: Response;
  try {
    res = await fetch(`${PYTHON_API}/pipeline/dcp-controls?${params}`, {
      signal: AbortSignal.timeout(20_000),
    });
  } catch (e) {
    throw new DcpControlsUnavailableError(
      `DCP controls source unreachable: ${e instanceof Error ? e.message : String(e)}`,
    );
  }
  if (!res.ok) {
    throw new DcpControlsUnavailableError(
      `DCP controls source returned ${res.status}`,
    );
  }
  return (await res.json()) as DcpControlsResult;
}
