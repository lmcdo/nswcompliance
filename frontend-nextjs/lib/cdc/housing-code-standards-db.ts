/**
 * Server-side loader for the stored Housing Code standards.
 * Uses the app's shared pool (lib/db). Read-only SELECT.
 *
 * prior-art-checked: thin loader over the shared lib/db query(); nothing else loads these rows in TS.
 */

import { query } from '@/lib/db';
import { parseRows, type ParsedRow, type StandardRow } from './housing-code-standards';

export interface LoadedStandards {
  rows: StandardRow[];
  parsed: ParsedRow[];
  /** Set when the table could not be read: every check must then be "Not checked". */
  error: string | null;
}

export async function loadHousingCodeStandards(): Promise<LoadedStandards> {
  try {
    const result = await query(
      `SELECT id, code_name, standard_type, numeric_value, text_value, applicable_zones,
              conditionality, ref_number, source_quote, source_provision_ids, effective_date, is_active,
              manual_verified, stale_since
         FROM cdc_eligibility_standards
        WHERE code_name = 'housing_code' AND is_active = TRUE
        ORDER BY id`
    );
    const base = (result?.rows ?? []) as StandardRow[];
    const firstIds = Array.from(new Set(
      base
        .map((r) => (Array.isArray(r.source_provision_ids) ? Number(r.source_provision_ids[0]) : NaN))
        .filter((n) => Number.isInteger(n))
    ));
    const pages = new Map<number, number | null>();
    if (firstIds.length > 0) {
      const pg = await query(
        'SELECT id, pdf_page FROM regulatory_provisions WHERE id = ANY($1::int[])',
        [firstIds]
      );
      for (const p of (pg?.rows ?? []) as { id: number; pdf_page: number | null }[]) {
        pages.set(Number(p.id), p.pdf_page === null ? null : Number(p.pdf_page));
      }
    }
    const rows = base.map((r) => ({
      ...r,
      pdf_page: Array.isArray(r.source_provision_ids)
        ? (pages.get(Number(r.source_provision_ids[0])) ?? null)
        : null,
      numeric_value: r.numeric_value === null || r.numeric_value === undefined ? null : Number(r.numeric_value),
    }));
    return { rows, parsed: parseRows(rows), error: null };
  } catch (err) {
    return {
      rows: [],
      parsed: [],
      error: `stored standards unavailable: ${err instanceof Error ? err.message : 'unknown error'}`,
    };
  }
}
