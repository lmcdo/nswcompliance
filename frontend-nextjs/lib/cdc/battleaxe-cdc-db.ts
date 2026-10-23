/**
 * Server-side loader for the battle-axe CDC limits. Read-only SELECT.
 *
 * prior-art-checked: same pattern as housing-code-standards-db.ts, for the separate
 * 'housing_sepp_sch1' rows (SEPP (Housing) 2021 Sch 1 s2(1)(c)).
 */

import { query } from '@/lib/db';
import type { BattleaxeLimits } from './battleaxe-cdc';

/** The two stored limits, or null when either row is missing, stale or unreadable, or its clause is not is_current. */
export async function loadBattleaxeLimits(): Promise<BattleaxeLimits | null> {
  try {
    const result = await query(
      `SELECT s.standard_type, s.numeric_value, s.ref_number, s.source_quote, p.pdf_page, p.is_current
         FROM cdc_eligibility_standards s
         LEFT JOIN regulatory_provisions p ON p.id = s.source_provision_ids[1]
        WHERE s.code_name = 'housing_sepp_sch1'
          AND s.standard_type IN ('battleaxe_access_min_width', 'battleaxe_lot_min_dimension')
          AND s.is_active = TRUE
          AND s.stale_since IS NULL`
    );
    const rows = (result?.rows ?? []) as Array<{
      standard_type: string; numeric_value: string | number | null; ref_number: string | null;
      source_quote: string | null; pdf_page: number | null; is_current: boolean | null;
    }>;
    const byType = new Map(rows.map((r) => [r.standard_type, r]));
    const access = byType.get('battleaxe_access_min_width');
    const dim = byType.get('battleaxe_lot_min_dimension');
    const a = access?.numeric_value == null ? NaN : Number(access.numeric_value);
    const d = dim?.numeric_value == null ? NaN : Number(dim.numeric_value);
    if (!access || !dim || !Number.isFinite(a) || !Number.isFinite(d) || a <= 0 || d <= 0) return null;
    // The clause the limits were copied from must still be current (is_current = TRUE),
    // otherwise the law may have changed under them: not checked, never a stale pass.
    if (access.is_current !== true || dim.is_current !== true) return null;
    return {
      accessMinWidth: a,
      lotMinDimension: d,
      ref: access.ref_number ?? 'Schedule 1',
      quote: access.source_quote ?? '',
      pdfPage: access.pdf_page ?? null,
    };
  } catch (err) {
    console.warn('[battleaxe-cdc] limits could not be read:', err);
    return null;
  }
}
