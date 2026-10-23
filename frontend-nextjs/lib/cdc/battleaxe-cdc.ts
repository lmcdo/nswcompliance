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
  const minArea = limits.lotMinDimension * limits.lotMinDimension;
  const tests = [
    { value: b.accessWayWidth, min: limits.accessMinWidth, what: 'Access way', unit: 'm wide', limit: `${limits.accessMinWidth} m` },
    { value: b.mainLotWidth, min: limits.lotMinDimension, what: 'Main lot (without the access way)', unit: 'm wide', limit: `${limits.lotMinDimension} m by ${limits.lotMinDimension} m` },
    { value: b.mainLotArea, min: minArea, what: 'Main lot (without the access way)', unit: 'm² in area', limit: `${limits.lotMinDimension} m by ${limits.lotMinDimension} m` },
  ];

  const issues: string[] = [];
  let anyFail = false;
  let anyNear = false;
  for (const t of tests) {
    const margin = t.unit.startsWith('m²') ? NEAR_LIMIT_M * limits.lotMinDimension * 2 : NEAR_LIMIT_M;
    const shown = t.unit.startsWith('m²') ? t.value.toFixed(0) : t.value.toFixed(1);
    if (Math.abs(t.value - t.min) <= margin) {
      anyNear = true;
      issues.push(`${t.what} ${shown} ${t.unit} (${MAP_NOTE}), close to the ${t.limit} that complying development (CDC) needs for a battle-axe lot (${src}).`);
    } else if (t.value < t.min) {
      anyFail = true;
      issues.push(`${t.what} ${shown} ${t.unit} (${MAP_NOTE}). Complying development (CDC) needs at least ${t.limit} for a battle-axe lot (${src}), so CDC is not available here; a DA is assessed against the council's own controls instead.`);
    }
  }

  const cdcStatus: BattleaxeCdcStatus = anyFail ? 'fails' : anyNear ? 'near' : 'meets';
  return {
    ...b,
    meetsMinimumRequirements: anyFail ? false : anyNear ? null : true,
    complianceIssues: issues,
    cdcStatus,
    cdcRef: src,
    cdcPdfPage: limits.pdfPage,
  };
}
