// prior-art-checked: reuse not viable because the existing granny-flat
// surfaces (reports/granny-flat/page.tsx, GrannyFlatBriefCard.tsx,
// api/reports/granny-flat/generate, lib/pdf/granny-flat-report.tsx) each
// render a stored `confidence` string inline with their own label map; none
// of them derives a state, and there is no shared module between them. This
// is that missing shared reader — the four surfaces are edited to CALL it,
// not to keep their own copies.

/**
 * The one place the granny-flat "what actually happened" state is read.
 *
 * Reports say what happened to the structure list, not how good they are.
 * The high/medium/low ladder this replaces on served surfaces graded every
 * lot that was not human-reviewed as "medium" — but a lot whose scan found
 * nothing has been checked against nothing, which is an unverified result,
 * not a middling one. User ruling 2026-08-06: "if there is no dwelling found
 * that is also not medium confidence."
 *
 * States are produced by `_review_state` in services/granny_flat.py and
 * STORED on the report row from 2026-08-06. This module prefers the stored
 * value and only derives when reading an older row.
 */

export type GrannyReviewState =
  | 'reviewed'
  | 'scan_only_found'
  | 'scan_only_none_found'
  | 'scan_inconclusive'
  | 'not_assessed';

export interface GrannyReviewStateView {
  state: GrannyReviewState;
  label: string;
  detail: string;
  /** True when derived from a pre-2026-08-06 row rather than read from it. */
  derived: boolean;
}

// Kept byte-identical to _REVIEW_STATE_TEXT in services/granny_flat.py.
// Duplicated across the language boundary because the PDF route and the page
// are TypeScript and cannot call the Python module; the Python copy is
// authoritative for rows written since 2026-08-06 (this text is only used
// when rendering a row that predates the stored field).
// tests/test_granny_flat_logic.py::test_review_state_text_matches_typescript
// fails if the two drift.
const TEXT: Record<GrannyReviewState, { label: string; detail: string }> = {
  reviewed: {
    label: 'Reviewed by you',
    detail:
      'You classified each structure the scan found on this lot. This ' +
      'covers only structures the scan detected — one it missed could not ' +
      'be classified, and detection accuracy has never been measured.',
  },
  scan_only_found: {
    label: 'Scan only — structures found, not reviewed',
    detail:
      'The scan found structures on this lot. Nobody has classified what ' +
      'they are, so the count in this report has not been checked against ' +
      'the aerial image. Detection accuracy has never been measured.',
  },
  scan_only_none_found: {
    label: 'Scan only — no secondary structures found',
    detail:
      'The scan found the principal dwelling and no other structures. ' +
      'Nothing has been checked against the aerial image. Small, shaded or ' +
      'tree-covered structures can be missed, and detection accuracy has ' +
      'never been measured.',
  },
  scan_inconclusive: {
    label: 'Scan inconclusive — no structures found',
    detail:
      'The scan returned no structures at all on this lot, not even a ' +
      'principal dwelling. That more likely means the scan could not read ' +
      'this image than that the lot is empty. Treat the structure count on ' +
      'this report as unknown.',
  },
  not_assessed: {
    label: 'Not assessed',
    detail:
      'The structure scan did not run, or its result could not be read back. ' +
      'The structure count on this report has not been checked against the ' +
      'aerial image, and the number of buildings on this lot is unknown.',
  },
};

const VALID = new Set<string>(Object.keys(TEXT));

/**
 * Resolve the state for a report row or a live confirm response.
 *
 * @param stored   the row's `outputs` object, or the confirm response body
 * @param inputs   the row's `inputs` object (legacy rows keep the counts here)
 *
 * Reading order matters. A stored state is used verbatim; anything else is a
 * pre-2026-08-06 row, and those are derived under one hard rule: they can
 * never resolve to `reviewed`. No surface could record a human count before
 * 2026-08-06 (the standalone tool passed `onCountChange` to a component that
 * never called it), so crediting a review to a legacy row would invent the
 * exact evidence this change exists to stop inventing.
 */
export function resolveGrannyReviewState(
  stored: Record<string, unknown> | null | undefined,
  inputs?: Record<string, unknown> | null,
): GrannyReviewStateView {
  const s = stored ?? {};

  const storedState = s.review_state;
  if (typeof storedState === 'string' && VALID.has(storedState)) {
    const state = storedState as GrannyReviewState;
    // Prefer the text stored with the row so a re-pulled report reads exactly
    // as it did when it was generated, even if the wording here later changes.
    const label = typeof s.review_state_label === 'string' && s.review_state_label
      ? s.review_state_label
      : TEXT[state].label;
    const detail = typeof s.review_state_detail === 'string' && s.review_state_detail
      ? s.review_state_detail
      : TEXT[state].detail;
    return { state, label, detail, derived: false };
  }

  // --- Legacy row (pre-2026-08-06) -----------------------------------------
  // The confirm write puts the carried structures in `outputs`, and no
  // completed row currently holds them in `inputs` (measured 2026-08-06).
  // Both are checked anyway: the structure array is stronger evidence than
  // the count — it carries is_main_dwelling — so losing it to a column
  // change would silently downgrade a row that still had its evidence.
  // Section 2 of the measurement script COALESCEs the same two columns.
  const detected = Array.isArray(s.detected_structures)
    ? s.detected_structures
    : (inputs ?? {}).detected_structures;
  if (Array.isArray(detected)) {
    if (detected.length === 0) return view('scan_inconclusive');
    // `=== true`, not truthiness. A JSON round-trip that yields the STRING
    // 'false' is truthy, so a loose test would count a secondary structure as
    // the principal dwelling and the report would say nothing was found
    // beside the house. Anything that is not exactly `true` counts as
    // secondary — that direction says "structures found, not reviewed",
    // which overstates nothing and hides nothing.
    const secondary = detected.filter(
      (d) => (d && typeof d === 'object'
        ? (d as Record<string, unknown>).is_main_dwelling !== true
        : true),
    );
    return view(secondary.length > 0 ? 'scan_only_found' : 'scan_only_none_found');
  }

  // No structure array: the counts are all that survive. `samgeo_structure_count`
  // is the TOTAL including the principal dwelling — verified against the 60
  // detect rows on 2026-08-06 (samgeo=3 -> 1 main + 2 secondary; samgeo=1 ->
  // main only). Reading it as a secondary count would report every ordinary
  // single-house lot as having a granny flat already.
  const raw = (inputs ?? {}).samgeo_structure_count ?? s.samgeo_structure_count;
  const count = strictCount(raw);
  // null = detection failed, never recorded, or unparseable. NEVER treated as
  // zero: that is the three-state contract the detect endpoint writes
  // (#745 D4), and zero is a claim that the scan RAN and returned nothing.
  // `== null` deliberately: catches undefined too, so a strictCount contract
  // change or a hand-built object can never fall through to the count tests.
  if (count == null) return view('not_assessed');
  if (count === 0) return view('scan_inconclusive');
  if (count === 1) return view('scan_only_none_found');
  return view('scan_only_found');
}

/**
 * A structure count, or null if the value is not one.
 *
 * `Number()` is not usable here: `Number('')` and `Number(null)` are 0, and
 * `Number(true)` is 1 — so a blank string would report "the scan ran and
 * found nothing" and a boolean would report "the principal dwelling only".
 * Both are claims about the world derived from a malformed field. Only a
 * non-negative integer, or a string of digits, is a count.
 */
function strictCount(raw: unknown): number | null {
  if (typeof raw === 'number') {
    return Number.isInteger(raw) && raw >= 0 ? raw : null;
  }
  if (typeof raw === 'string' && /^\d+$/.test(raw.trim())) {
    return Number(raw.trim());
  }
  return null;
}

function view(state: GrannyReviewState): GrannyReviewStateView {
  return { state, label: TEXT[state].label, detail: TEXT[state].detail, derived: true };
}

/** Severity for surfaces that colour-code. Only `reviewed` is not a caveat. */
export function reviewStateSeverity(state: GrannyReviewState): 'green' | 'amber' | 'red' {
  if (state === 'reviewed') return 'green';
  if (state === 'not_assessed' || state === 'scan_inconclusive') return 'red';
  return 'amber';
}

export const GRANNY_REVIEW_STATE_TEXT = TEXT;
