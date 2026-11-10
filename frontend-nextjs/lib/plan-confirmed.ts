/**
 * The date we last reached a council's website and looked at its plan (DQ-153).
 *
 * prior-art-checked: reuse not viable because lib/dcp-provisions-query.ts and
 * the route's `dcp_currency` block read instrument_currency.verified_at (set by
 * the weekly monitor after a clean run), which is not set when the council's
 * website blocks the monitor -- the case this exists for. This reads the
 * per-chapter check date the monitor writes (dcp_chapter_registry.url_last_checked).
 *
 * The date is the OLDEST over the council's chapters that serve rules: one
 * blocked chapter is enough to make the plan possibly out of date.
 */

export const PLAN_STALE_AFTER_DAYS = 30;

type Query = (sql: string, params: unknown[]) => Promise<{ rows: Array<{ oldest?: Date | string | null }> }>;

export const PLAN_CONFIRMED_SQL = `
  SELECT min(r.url_last_checked) AS oldest, bool_or(r.url_last_checked IS NULL) AS never
  FROM dcp_chapter_registry r
  WHERE r.council = $1 AND r.is_active = TRUE AND r.doc_type = 'dcp'
    AND EXISTS (SELECT 1 FROM regulatory_provisions p
                WHERE p.source_council = r.council AND p.source_chapter_key = r.chapter_key
                  AND p.is_current = TRUE AND p.v2_is_actionable = TRUE)`;

/** ISO date of the oldest check, or null when the council has no chapters or one was never checked. */
export async function loadPlanConfirmed(query: Query, council: string | null): Promise<string | null> {
  if (!council) return null;
  const res = await query(PLAN_CONFIRMED_SQL, [council]);
  const row = res.rows[0] as { oldest?: Date | string | null; never?: boolean | null } | undefined;
  if (!row || row.never || !row.oldest) return null;
  const d = row.oldest instanceof Date ? row.oldest : new Date(row.oldest);
  return Number.isNaN(d.getTime()) ? null : d.toISOString();
}

/**
 * True when the plan has gone more than `days` since its oldest dated check.
 * undefined (old response) and null (no chapters, or a chapter never checked --
 * the DQ-153 red number covers that) show nothing: no date means no claim.
 */
export function planCheckIsOld(confirmed: string | null | undefined, now: Date, days = PLAN_STALE_AFTER_DAYS): boolean {
  if (!confirmed) return false;
  const t = Date.parse(confirmed);
  if (Number.isNaN(t)) return false;
  return now.getTime() - t > days * 86_400_000;
}
