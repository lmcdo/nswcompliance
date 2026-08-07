// prior-art-checked: reuse not viable because no shared module interprets the
// Sentinel-2 surface-change result. Sweep 2026-08-07 — frontend (`app/**`,
// `components/`, `hooks/`, `lib/`): the three consumers each inline their own
// branch (lib/pdf/shadow-report.tsx, components/tools/ShadowTool.tsx,
// components/reports/ShadowDetailDisplay.tsx) and they had ALREADY drifted —
// the Brief checked the no-reading note, the PDF did not. Python
// (`services/`): shadow_detector.py emits the fields but renders nothing.
// Putting the rule in one place is what stops the drift recurring, and keeps
// the jscpd ratchet honest.
/**
 * How to read the Sentinel-2 ground-surface-change result.
 *
 * WHAT THE MEASUREMENT IS. `compute_change_score(lat, lng, 200)` builds a bbox
 * of ±200 m in both axes — a 400 m × 400 m square, 16 hectares — and returns
 * ONE mean bare-soil index for the whole of it. It contains the subject's own
 * lot and a few hundred others. It resolves no direction and cannot isolate a
 * parcel: the index needs the 20 m SWIR band, so a 500 m² lot is about one
 * pixel. Any wording naming an "adjacent lot" or a compass direction described
 * something the measurement does not contain.
 *
 * WHY THE THREE-STATE. Measured 2026-08-07 over all 538 stored shadow reports:
 * the check has NEVER returned a real reading. 231 carry "Insufficient
 * cloud-free scenes", 10 a timeout, 5 an error, and 292 pre-June rows hold a
 * score of exactly 0.0 from before the note key existed. Every one of the 538
 * rendered the negative branch — "No significant ground disturbance detected on
 * adjacent lots" — from a check that produced nothing.
 */

export type SurfaceChangeState = 'detected' | 'none_detected' | 'not_assessed';

/**
 * The area the reading actually covers. Stated wherever a result is rendered.
 *
 * Deliberately NOT phrased as "within 200 m": the bbox is ±200 m on each AXIS,
 * so it is a square whose corners sit ~283 m from the centre. A radial claim
 * would understate the extent the score is drawn from.
 */
export const SURFACE_CHANGE_AREA_NOTE =
  '400m x 400m area centred on this property (about 16 hectares)';

export interface SurfaceChangeInput {
  construction_change_score?: number | null;
  construction_change_detected?: boolean | null;
  construction_change_note?: string | null;
}

/**
 * Classify a stored or freshly computed surface-change result.
 *
 * `not_assessed` when any of:
 *  - a note is present (the service sets one only when the check did NOT
 *    produce a clean reading: cloud cover, timeout, exception);
 *  - the score is null (timeout and exception paths);
 *  - the score is EXACTLY 0.0.
 *
 * The exact-zero rule is a deliberate, documented heuristic for LEGACY ROWS
 * ONLY. It is not load-bearing for anything written from 2026-08-07 onward:
 * `compute_change_score` now returns `change_score: None` on the no-data path
 * (services/sentinel2.py), so a new report can never present missing data as a
 * zero. The rule remains because 292 stored reports were written before that,
 * hold exactly 0.0, carry no note, and would otherwise keep rendering a
 * negative about neighbouring land from a check that never ran.
 *
 * Why exact zero is safe to treat as absence in that corpus: a real result is
 * `round(recent_bsi - baseline_bsi, 4)`, so landing on exactly 0.0000 by
 * measurement is a ~1-in-10,000 coincidence. All 292 pre-note rows hold exactly
 * 0.0 and none holds any other value. The failure mode this accepts — a genuine
 * 0.0000 reported as not-assessed — understates rather than overstates, which
 * is the correct direction for a claim about somebody else's land.
 */
export function surfaceChangeState(data: SurfaceChangeInput): SurfaceChangeState {
  const { construction_change_score: score, construction_change_note: note } = data;
  if (note != null && String(note).trim() !== '') return 'not_assessed';
  if (score == null) return 'not_assessed';
  if (score === 0) return 'not_assessed';
  return data.construction_change_detected ? 'detected' : 'none_detected';
}
