/**
 * Choose which DCP parking row (if any) can be stated as "the rate".
 *
 * prior-art-checked: no existing helper does this. lib/upzoning.ts and
 * app/api/capacity/calculate/route.ts both read dcp_setback_controls but take the
 * first N rows without inspecting `condition`; app/api/dcp/structured-controls
 * groups rows for DISPLAY and never reduces them to one value. This is the
 * reduction step none of them perform, extracted rather than inlined so it can be
 * unit-tested without a database.
 *
 * WHY IT IS NOT JUST `rows[0]`
 * ----------------------------
 * `condition` is a row SELECTOR, not a footnote. A single (lga, dev_type) group
 * routinely holds a resident rate, a visitor rate and a zone-specific rate side
 * by side:
 *
 *   ashfield / multi_dwelling_housing  1    spaces/dwelling  "R3 zone; plus ..."
 *   ashfield / multi_dwelling_housing  0.2  spaces/dwelling  "visitor parking; ..."
 *
 * Taking the first row hands back 0.2 as though it were the dwelling rate. That
 * is the DQ-32 defect (the capacity engine picking a setback without reading its
 * condition) reproduced in a new place.
 *
 * Measured against the live table on 2026-08-01, control_type='car_parking',
 * currency- and needs_review-guarded: of 123 (lga, dev_type) groups, 27 have
 * exactly one unconditioned row, 96 have none, and 0 have more than one. So the
 * safe rule is narrow and almost never ambiguous in the base case.
 *
 * THE RULE
 * --------
 *   exactly one unconditioned row  -> state it as the rate; conditioned siblings
 *                                     ride along as ADDITIONS, never replacements
 *   zero unconditioned rows        -> there is no "the rate"; return them all with
 *                                     their conditions and say so
 *   more than one unconditioned    -> genuinely ambiguous; return them all. Never
 *                                     break the tie by ordering.
 */

export interface ParkingControlRow {
  value_min: string | number | null;
  value_max: string | number | null;
  unit: string | null;
  condition: string | null;
  source_text: string | null;
  section_ref: string | null;
  dcp_version: string | null;
  pdf_page: number | null;
  dev_type: string | null;
}

export interface ParkingRate {
  rate: number | null;
  rate_max: number | null;
  unit: string;
  applies_when: string | null;
  dev_type: string | null;
  source_text: string | null;
  section_ref: string | null;
  pdf_page: number | null;
}

export type ParkingSelection =
  | { kind: 'none' }
  | { kind: 'single'; base: ParkingRate; additional: ParkingRate[]; dcpVersion: string | null }
  | { kind: 'conditional'; rates: ParkingRate[]; dcpVersion: string | null };

/** A condition is present only if it has non-whitespace content. */
function hasCondition(row: ParkingControlRow): boolean {
  return Boolean((row.condition ?? '').trim());
}

function toNumber(value: string | number | null): number | null {
  if (value === null || value === undefined) return null;
  const n = typeof value === 'number' ? value : parseFloat(value);
  // NaN would serialise to null in JSON anyway, but doing it here means a caller
  // reading `rate !== null` can trust that it got a usable number.
  return Number.isFinite(n) ? n : null;
}

export function toParkingRate(row: ParkingControlRow): ParkingRate {
  return {
    rate: toNumber(row.value_min),
    rate_max: toNumber(row.value_max),
    unit: row.unit || 'spaces',
    applies_when: (row.condition ?? '').trim() || null,
    dev_type: row.dev_type,
    source_text: row.source_text,
    section_ref: row.section_ref,
    pdf_page: row.pdf_page,
  };
}

export function selectParkingRate(rows: ParkingControlRow[]): ParkingSelection {
  if (!rows || rows.length === 0) return { kind: 'none' };

  const dcpVersion = rows[0]?.dcp_version ?? null;
  const unconditioned = rows.filter((r) => !hasCondition(r));

  if (unconditioned.length === 1) {
    return {
      kind: 'single',
      base: toParkingRate(unconditioned[0]),
      additional: rows.filter(hasCondition).map(toParkingRate),
      dcpVersion,
    };
  }

  return { kind: 'conditional', rates: rows.map(toParkingRate), dcpVersion };
}
