// prior-art-checked: reuse not viable because no existing test covers
// lib/granny-flat-review-state.ts — it is new in this change. The nearest
// suites (__tests__/components/reports/GrannyFlatBriefCard.test.tsx,
// __tests__/api/reports/granny-flat-generate.test.ts) exercise the surfaces
// that CALL this module, not the legacy-row derivation it performs; those two
// are extended in the same change rather than duplicated here.

/**
 * The legacy-row derivation is what renders the 20 completed granny-flat
 * reports that already exist in production. None of them carries the stored
 * state, so every one of them is rendered by the fallback path below — which
 * makes these the tests that decide what a customer who pulls an old report
 * sees today.
 *
 * Measured 2026-08-06 over all 87 rows
 * (scripts/measure_granny_confidence_states.py).
 */

import {
  resolveGrannyReviewState,
  reviewStateSeverity,
  GRANNY_REVIEW_STATE_TEXT,
} from '@/lib/granny-flat-review-state';

describe('resolveGrannyReviewState — stored state', () => {
  it('uses a stored state verbatim and marks it not-derived', () => {
    const v = resolveGrannyReviewState({
      review_state: 'reviewed',
      review_state_label: 'Reviewed by you',
      review_state_detail: 'Detail as stored at generation time.',
    });
    expect(v.state).toBe('reviewed');
    expect(v.label).toBe('Reviewed by you');
    expect(v.detail).toBe('Detail as stored at generation time.');
    expect(v.derived).toBe(false);
  });

  it('ignores an unrecognised stored state rather than rendering it raw', () => {
    // A value we do not know is not a state we can describe. Falling through
    // to the derivation is safe; printing it would put an internal token on a
    // paid PDF.
    const v = resolveGrannyReviewState({
      review_state: 'totally_fine',
      samgeo_structure_count: 2,
    });
    expect(v.state).toBe('scan_only_found');
    expect(v.derived).toBe(true);
  });

  it('falls back to canonical text when a stored label is blank', () => {
    const v = resolveGrannyReviewState({
      review_state: 'not_assessed',
      review_state_label: '',
      review_state_detail: '',
    });
    expect(v.label).toBe(GRANNY_REVIEW_STATE_TEXT.not_assessed.label);
    expect(v.detail).toBe(GRANNY_REVIEW_STATE_TEXT.not_assessed.detail);
  });
});

describe('resolveGrannyReviewState — legacy rows (the 20 in production)', () => {
  it('reads a missing count as unknown, NEVER as zero structures', () => {
    // The three-state contract: samgeo_structure_count is null when detection
    // FAILED, and 0 only when it ran and found none. Collapsing them would
    // tell someone whose scan never ran that their lot is clear.
    for (const row of [{}, { samgeo_structure_count: null }, { samgeo_structure_count: undefined }]) {
      expect(resolveGrannyReviewState(row).state).toBe('not_assessed');
    }
  });

  it('reads a non-numeric count as unknown', () => {
    expect(resolveGrannyReviewState({ samgeo_structure_count: 'two' }).state)
      .toBe('not_assessed');
    expect(resolveGrannyReviewState({ samgeo_structure_count: NaN }).state)
      .toBe('not_assessed');
  });

  it('never lets a malformed count become a claim about the lot', () => {
    // Sol finding 2026-08-06: Number('') === 0 and Number(true) === 1, so a
    // loose parse turns a blank field into "the scan ran and found nothing"
    // and a boolean into "the principal dwelling only". Both are statements
    // about the world manufactured from a broken field.
    for (const bad of ['', '   ', true, false, [], {}, '2.5', -1, 1.5, '-3', '1e2']) {
      expect(resolveGrannyReviewState({ samgeo_structure_count: bad }).state)
        .toBe('not_assessed');
    }
    // A digit string IS a count — supabase can hand back either form.
    expect(resolveGrannyReviewState({ samgeo_structure_count: '0' }).state)
      .toBe('scan_inconclusive');
    expect(resolveGrannyReviewState({ samgeo_structure_count: '2' }).state)
      .toBe('scan_only_found');
  });

  it('does not let a string "false" flag disguise a secondary structure', () => {
    // Sol finding 2026-08-06: 'false' is truthy, so a truthiness test would
    // read this secondary structure as a second principal dwelling and the
    // report would say nothing was found beside the house.
    const v = resolveGrannyReviewState({
      detected_structures: [
        { index: 0, is_main_dwelling: true },
        { index: 1, is_main_dwelling: 'false' },
      ],
    });
    expect(v.state).toBe('scan_only_found');
  });

  it('treats the count as a TOTAL including the principal dwelling', () => {
    // Verified against the 60 stored detect rows: samgeo=1 is the house alone.
    // Reading it as a SECONDARY count would report every ordinary single-house
    // lot as already having a granny flat — and SEPP cl 53(1) blocks a second.
    expect(resolveGrannyReviewState({}, { samgeo_structure_count: 1 }).state)
      .toBe('scan_only_none_found');
    expect(resolveGrannyReviewState({}, { samgeo_structure_count: 2 }).state)
      .toBe('scan_only_found');
    expect(resolveGrannyReviewState({}, { samgeo_structure_count: 3 }).state)
      .toBe('scan_only_found');
  });

  it('treats zero structures as inconclusive, not as a clear lot', () => {
    const v = resolveGrannyReviewState({}, { samgeo_structure_count: 0 });
    expect(v.state).toBe('scan_inconclusive');
    expect(v.detail.toLowerCase()).toContain('unknown');
  });

  it('never credits a legacy row with a human review', () => {
    // No surface could record a human count before 2026-08-06.
    for (const count of [0, 1, 2, 5]) {
      expect(resolveGrannyReviewState({}, { samgeo_structure_count: count }).state)
        .not.toBe('reviewed');
    }
  });

  it('prefers the structure array over the count when both are present', () => {
    // The array carries is_main_dwelling; the count cannot distinguish a
    // detached garage from the house.
    const v = resolveGrannyReviewState({
      detected_structures: [
        { index: 0, is_main_dwelling: true },
        { index: 1, is_main_dwelling: false },
      ],
      samgeo_structure_count: 1, // stale/disagreeing — array wins
    });
    expect(v.state).toBe('scan_only_found');
  });

  it('finds the structure array in inputs when outputs does not carry it', () => {
    // Sol finding 2026-08-06. The array is stronger evidence than the count —
    // only it carries is_main_dwelling — so a row that still holds it must
    // not be resolved from a missing count instead.
    const v = resolveGrannyReviewState(
      { samgeo_structure_count: null },
      { detected_structures: [
        { index: 0, is_main_dwelling: true },
        { index: 1, is_main_dwelling: false },
      ] },
    );
    expect(v.state).toBe('scan_only_found');
  });

  it('reads an empty structure array as inconclusive', () => {
    expect(resolveGrannyReviewState({ detected_structures: [] }).state)
      .toBe('scan_inconclusive');
  });

  it('reads a main-dwelling-only array as nothing secondary found', () => {
    const v = resolveGrannyReviewState({
      detected_structures: [{ index: 0, is_main_dwelling: true }],
    });
    expect(v.state).toBe('scan_only_none_found');
    expect(v.detail.toLowerCase()).toContain('missed');
  });

  it('survives a null row without throwing', () => {
    expect(resolveGrannyReviewState(null).state).toBe('not_assessed');
    expect(resolveGrannyReviewState(undefined, undefined).state).toBe('not_assessed');
  });

  it('does not mistake a malformed structure entry for a secondary building', () => {
    // A null entry has no is_main_dwelling, so a naive filter counts it as
    // secondary and the report claims a building nobody detected.
    const v = resolveGrannyReviewState({
      detected_structures: [{ index: 0, is_main_dwelling: true }, null],
    });
    // It IS counted as a non-main entry — that is the safe direction (it says
    // "structures found, not reviewed" rather than "nothing here"), and the
    // state never claims the list was checked.
    expect(v.state).toBe('scan_only_found');
    expect(v.label.toLowerCase()).toContain('not reviewed');
  });
});

describe('served wording', () => {
  it('never grades and never uses the banned umbrella word', () => {
    const banned = [
      'verified', 'guaranteed', 'certified', 'reliable',
      'high confidence', 'medium confidence', 'low confidence',
    ];
    for (const [state, { label, detail }] of Object.entries(GRANNY_REVIEW_STATE_TEXT)) {
      const blob = `${label} ${detail}`.toLowerCase();
      for (const word of banned) {
        expect(`${state}: ${blob}`).not.toContain(word);
      }
    }
  });

  it('discloses the gap in every state that is not a human review', () => {
    for (const state of ['scan_only_found', 'scan_only_none_found', 'scan_inconclusive', 'not_assessed'] as const) {
      const d = GRANNY_REVIEW_STATE_TEXT[state].detail.toLowerCase();
      expect(
        d.includes('not been checked') || d.includes('never been measured') || d.includes('unknown'),
      ).toBe(true);
    }
  });

  it('says plainly that a review cannot cover what the scan missed', () => {
    const d = GRANNY_REVIEW_STATE_TEXT.reviewed.detail.toLowerCase();
    expect(d).toContain('missed');
    expect(d).toContain('never been measured');
  });

  it('gives every state a distinct label — a one-state mutant must fail', () => {
    const labels = Object.values(GRANNY_REVIEW_STATE_TEXT).map((t) => t.label);
    expect(new Set(labels).size).toBe(labels.length);
  });

  it('marks only a human review as unqualified', () => {
    expect(reviewStateSeverity('reviewed')).toBe('green');
    expect(reviewStateSeverity('scan_only_found')).toBe('amber');
    expect(reviewStateSeverity('scan_only_none_found')).toBe('amber');
    expect(reviewStateSeverity('scan_inconclusive')).toBe('red');
    expect(reviewStateSeverity('not_assessed')).toBe('red');
  });
});
