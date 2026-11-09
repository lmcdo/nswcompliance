/**
 * Reduce a zone label from the planning portal ("R2 Low Density Residential", "R2: Low Density
 * Residential", "R2") to the bare zone code ("R2"), which is what the controls filter expects.
 *
 * Returns null when no code can be read, and null means "no zone filter" (every row, as before),
 * never a guess. The backend filter (scripts/conveyancing_db.py zone_row_applies) keeps a row when
 * in doubt, so a missing zone can show an extra row but a wrong parse cannot hide a right one.
 *
 * prior-art-checked: lib/plan-brief.ts zoneGroup maps a zone onto the brief's group labels
 * (R2/R3/R4/B/ANY) and drops the exact code; the controls filter needs the exact code.
 */
export function zoneCode(raw: string | null | undefined): string | null {
  const m = (raw ?? '').trim().toUpperCase().match(/^[A-Z]{1,2}\d[A-Z0-9]*/);
  return m ? m[0] : null;
}
