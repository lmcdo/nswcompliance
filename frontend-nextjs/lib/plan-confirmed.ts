/**
 * Whether we have been able to look at a council's plan lately (DQ-153).
 *
 * prior-art-checked: reuse not viable because lib/dcp-provisions-query.ts and
 * the route's `dcp_currency` block read instrument_currency.verified_at (set by
 * the weekly monitor after a clean run), which is not set when the council's
 * website blocks the monitor -- the case this exists for. This reads the
 * per-chapter check date and latest monitor result the monitor writes.
 *
 * It applies the SAME rule as the DQ-153 red number (scripts/dq_probe_live.py):
 * over 14 days since a check, never checked, or latest result 'waf_blocked' --
 * over the council's chapters that serve rules. One bad chapter is enough.
 * tests/test_manual_intake.py fails if the two ever drift apart.
 */

export const PLAN_STALE_AFTER_DAYS = 14;

export interface PlanCheck {
  /** ISO date of the OLDEST dated check over the council's serving chapters, or null if none is dated. */
  checked_on: string | null;
  /** At least one serving chapter has never been checked. */
  never_checked: boolean;
  /** At least one serving chapter's latest monitor result is 'waf_blocked'. */
  blocked: boolean;
}

type Row = { chapters?: number | string | null; oldest?: Date | string | null; never?: boolean | null; blocked?: boolean | null };
type Query = (sql: string, params: unknown[]) => Promise<{ rows: Row[] }>;

export const PLAN_CONFIRMED_SQL = `
  SELECT count(*) AS chapters,
         min(r.url_last_checked) AS oldest,
         bool_or(r.url_last_checked IS NULL) AS never,
         bool_or(COALESCE((SELECT x.outcome FROM dcp_monitor_chapter_results x
                           WHERE x.chapter_id = r.id
                           ORDER BY x.checked_at DESC, x.id DESC LIMIT 1) = 'waf_blocked', FALSE)) AS blocked
  FROM dcp_chapter_registry r
  WHERE r.council = $1 AND r.is_active = TRUE AND r.doc_type = 'dcp'
    AND EXISTS (SELECT 1 FROM regulatory_provisions p
                WHERE p.source_council = r.council AND p.source_chapter_key = r.chapter_key
                  AND p.is_current = TRUE AND p.v2_is_actionable = TRUE)`;

/** null = no council, or the council has no chapter serving rules (nothing to say). */
export async function loadPlanCheck(query: Query, council: string | null): Promise<PlanCheck | null> {
  if (!council) return null;
  const res = await query(PLAN_CONFIRMED_SQL, [council]);
  const row = res.rows.length > 0 ? res.rows[0] : undefined;
  if (!row || Number(row.chapters ?? 0) === 0) return null;
  const d = row.oldest ? (row.oldest instanceof Date ? row.oldest : new Date(row.oldest)) : null;
  return {
    checked_on: d && !Number.isNaN(d.getTime()) ? d.toISOString() : null,
    never_checked: row.never === true,
    blocked: row.blocked === true,
  };
}

/** Which line to show: undefined/null = none (old response, or no serving chapters). */
export type PlanNotice = 'blocked' | 'never' | 'old' | null;

export function planNotice(check: PlanCheck | null | undefined, now: Date, days = PLAN_STALE_AFTER_DAYS): PlanNotice {
  if (!check) return null;
  if (check.blocked) return 'blocked';
  if (check.never_checked) return 'never';
  if (!check.checked_on) return null;
  const t = Date.parse(check.checked_on);
  if (Number.isNaN(t)) return null;
  return now.getTime() - t > days * 86_400_000 ? 'old' : null;
}
