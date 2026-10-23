/**
 * Battle-axe lot test for complying development (CDC) of a secondary dwelling.
 *
 * prior-art-checked: lot-shape-analysis.ts measured the lot AND judged it against typed
 * 3 m / 12 m constants; this splits the judgement out so the limits come from
 * cdc_eligibility_standards (code_name 'housing_sepp_sch1', SEPP (Housing) 2021 Sch 1 s2(1)(c)).
 *
 * The limits apply to the CDC route only. A DA is assessed against the council's own
 * controls, so every message names the route. No limits = "not checked", never a pass.
 */

import type { BattleaxeDetectionResult } from '@/lib/geometry/lot-shape-analysis';

export interface BattleaxeLimits {
  /** Minimum access laneway width, metres (stored row battleaxe_access_min_width). */
  accessMinWidth: number;
  /** Lot excluding the laneway measures at least this by this, metres (battleaxe_lot_min_dimension). */
  lotMinDimension: number;
  /** Instrument reference, e.g. "Sch 1 s2(1)(c)". */
  ref: string;
  /** Verbatim clause text the limits were read from. */
  quote: string;
  /** PDF page of the clause, when known. */
  pdfPage: number | null;
}

/** Measurements within this many metres of a limit are reported as close, not as pass/fail. */
export const NEAR_LIMIT_M = 0.2;

export type BattleaxeCdcStatus = 'meets' | 'fails' | 'near' | 'not_checked';

const MAP_NOTE = 'measured from the cadastre map; a survey confirms it';

/**
 * Judge a detected battle-axe lot against the stored CDC limits.
 * meetsMinimumRequirements: true / false, or null when the limits could not be read or a
 * measurement sits within NEAR_LIMIT_M of a limit.
 */
export function applyBattleaxeLimits(
  b: BattleaxeDetectionResult,
  limits: BattleaxeLimits | null,
): BattleaxeDetectionResult & { cdcStatus: BattleaxeCdcStatus; cdcRef: string | null; cdcPdfPage: number | null } {
  if (!b.isBattleaxe) {
    return { ...b, cdcStatus: 'not_checked', cdcRef: null, cdcPdfPage: null };
  }
  if (!limits) {
    return {
      ...b,
      meetsMinimumRequirements: null,
      complianceIssues: [
        `Access way ${b.accessWayWidth.toFixed(1)} m wide (${MAP_NOTE}). The complying development (CDC) minimum for a battle-axe lot could not be read, so this was not checked.`,
      ],
      cdcStatus: 'not_checked',
      cdcRef: null,
      cdcPdfPage: null,
    };
  }

  const src = `SEPP (Housing) 2021 ${limits.ref}`;
  const square = `${limits.lotMinDimension} m by ${limits.lotMinDimension} m`;
  // The 12 m by 12 m test needs both sides of the main lot: its narrowest width across and
  // its length along. Either missing = that part not checked, never assumed.
  const tests: Array<{ value: number | undefined; min: number; what: string; limit: string }> = [
    { value: b.accessWayWidth, min: limits.accessMinWidth, what: 'Access way width', limit: `${limits.accessMinWidth} m` },
    { value: b.mainLotMinWidth, min: limits.lotMinDimension, what: 'Main lot narrowest width (without the access way)', limit: square },
    { value: b.mainLotLength, min: limits.lotMinDimension, what: 'Main lot length (without the access way)', limit: square },
  ];

  const issues: string[] = [];
  let anyFail = false;
  let anyNear = false;
  let anyUnmeasured = false;
  for (const t of tests) {
    if (t.value == null || !Number.isFinite(t.value) || t.value <= 0) {
      anyUnmeasured = true;
      issues.push(`${t.what} could not be measured from the cadastre map, so the ${t.limit} complying development (CDC) test for a battle-axe lot (${src}) was not checked.`);
      continue;
    }
    const shown = t.value.toFixed(1);
    if (Math.abs(t.value - t.min) <= NEAR_LIMIT_M) {
      anyNear = true;
      issues.push(`${t.what} ${shown} m (${MAP_NOTE}), close to the ${t.limit} that complying development (CDC) needs for a battle-axe lot (${src}).`);
    } else if (t.value < t.min) {
      anyFail = true;
      issues.push(`${t.what} ${shown} m (${MAP_NOTE}). Complying development (CDC) needs at least ${t.limit} for a battle-axe lot (${src}), so CDC is likely not available here. For a DA, the council assesses the lot against its own controls.`);
    }
  }

  const cdcStatus: BattleaxeCdcStatus = anyFail ? 'fails' : anyNear ? 'near' : anyUnmeasured ? 'not_checked' : 'meets';
  return {
    ...b,
    meetsMinimumRequirements: anyFail ? false : anyNear || anyUnmeasured ? null : true,
    complianceIssues: issues,
    cdcStatus,
    cdcRef: src,
    cdcPdfPage: limits.pdfPage,
  };
}
