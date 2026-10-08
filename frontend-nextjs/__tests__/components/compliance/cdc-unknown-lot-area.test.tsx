/**
 * An unknown lot area is not a passed check.
 *
 * WHAT THIS GUARDS. CDCPathway coerced an absent lot area to 0, which did two
 * things at once:
 *
 *   1. the `lotArea > 0 && lotArea < minArea` test went false, so the
 *      "lot too small for CDC" blocker was never added; and
 *   2. the result rendered
 *        { pass: true, text: 'Lot size 0m² — meets 200m² minimum' }
 *      an affirmative PASS on a control that was never tested, carrying a
 *      figure nobody measured.
 *
 * With no blocker and a ticked requirement, `cdcBlockers.length === 0` routed
 * the user to "your work qualifies as Complying Development" — planning advice
 * someone might act on, derived from an absent measurement.
 *
 * Measured 2026-10-07 before the fix: 0 of 120 real addresses sampled from
 * property_reports failed to return a lot area, so this is a latent path, not
 * an active one. It is guarded because the consequence is wrong planning
 * advice, not because it fires often.
 */
import { lotSizeRequirement } from '@/components/compliance/CDCPathway';

const SOURCE = 'SEPP Housing Code Part 3, page 12';

describe('lotSizeRequirement — a known area', () => {
  it('passes and states the measured figure', () => {
    const req = lotSizeRequirement(450, 200, SOURCE)!;
    expect(req.pass).toBe(true);
    expect(req.text).toContain('450m²');
    expect(req.text).toContain('200m² minimum');
  });

  it('rounds rather than printing a fractional area', () => {
    expect(lotSizeRequirement(449.6, 200, SOURCE)!.text).toContain('450m²');
  });

  it('still passes at exactly the minimum, which the caller has already tested', () => {
    // lotSizeRequirement reports; the blocker decision lives in the caller. If
    // this function also decided, there would be two places to disagree.
    expect(lotSizeRequirement(200, 200, SOURCE)!.pass).toBe(true);
  });
});

describe('lotSizeRequirement — an UNKNOWN area', () => {
  const req = lotSizeRequirement(null, 200, SOURCE)!;

  it('does NOT report a pass', () => {
    // The whole defect in one assertion.
    expect(req.pass).toBe(false);
  });

  it('is a warning, so the UI cannot render it as a satisfied control', () => {
    expect(req.warn).toBe(true);
  });

  it('says the check was not assessed', () => {
    expect(req.text).toMatch(/NOT assessed/i);
  });

  it('never prints a fabricated area', () => {
    // '0m²' was the old output. Any digit-plus-m² that is not the THRESHOLD
    // would be a measurement this function cannot have.
    expect(req.text).not.toContain('0m² —');
    expect(req.text).not.toMatch(/Lot size \d/);
  });

  it('still names the threshold and its source, because those ARE known', () => {
    // Stating the absence is not the same as going silent: the reader should
    // still learn what would have been checked, and on whose authority.
    expect(req.text).toContain('200m²');
    expect(req.text).toContain(SOURCE);
  });

  it('tells the reader who can resolve it', () => {
    expect(req.text).toMatch(/certifier/i);
  });
});

describe('lotSizeRequirement — UNDEFINED, not null', () => {
  // The QA gate caught this in the first version of the fix. propertyData is
  // typed `any` and this function is exported, so undefined is reachable. With
  // `=== null` guards it fell straight through to the pass branch.
  it('an undefined area is absent, not a measurement', () => {
    const req = lotSizeRequirement(undefined as unknown as number | null, 200, SOURCE)!;
    expect(req.pass).toBe(false);
    expect(req.warn).toBe(true);
    expect(req.text).toMatch(/NOT assessed/i);
  });

  it('never prints NaN for an undefined area', () => {
    // Math.round(undefined) is NaN, so the old guard produced
    // "Lot size NaNm² — meets 200m² minimum" with a tick beside it.
    const req = lotSizeRequirement(undefined as unknown as number | null, 200, SOURCE)!;
    expect(req.text).not.toMatch(/NaN/);
  });

  it('an undefined minimum yields no requirement line at all', () => {
    expect(
      lotSizeRequirement(450, undefined as unknown as number | null, SOURCE),
    ).toBeNull();
  });
});

describe('lotSizeRequirement — NO stated minimum', () => {
  // Measured against the live database 2026-10-07, over exactly the rows the
  // endpoint returns: 2 rows contain 'area of the lot' and BOTH are topic=Deck.
  // Fence, Carport and Pool have none. The old code answered that with a
  // hardcoded 200 labelled 'clause 3.1 (default)', so it gated a fence on a lot
  // area the Housing Code does not impose, citing a clause for it.
  it('returns null so the caller omits the line entirely', () => {
    expect(lotSizeRequirement(450, null, null)).toBeNull();
  });

  it('returns null even when the lot area IS known', () => {
    // The absence of a CONTROL is not the same as the absence of a measurement.
    // A known area with no stated minimum still has nothing to report.
    expect(lotSizeRequirement(180, null, null)).toBeNull();
  });

  it('returns null when neither is known', () => {
    expect(lotSizeRequirement(null, null, null)).toBeNull();
  });
});

describe('lotSizeRequirement — a COMPOUND threshold', () => {
  // The real page-129 wording: "at least 200 m2 but not more than 300 m2 and the
  // width of the lot ... is more than 7 m, or ... more than 300 m2". The parser
  // returns the 300 from the first match, which is the STRICTER branch, so a
  // 250m2 lot 8m wide would be refused CDC that the Code permits.
  const req = lotSizeRequirement(450, 300, 'SEPP Housing Code Part 3, page 129', true);

  it('still reports the measured area as meeting the stated figure', () => {
    expect(req).not.toBeNull();
    expect(req!.pass).toBe(true);
    expect(req!.text).toContain('450m²');
  });

  it('warns, because one number is not the whole control', () => {
    expect(req!.warn).toBe(true);
  });

  it('says a smaller lot may still qualify', () => {
    expect(req!.text).toMatch(/smaller lot may still qualify/i);
  });

  it('does not warn when the threshold is a single unambiguous minimum', () => {
    const plain = lotSizeRequirement(450, 300, SOURCE, false);
    expect(plain!.warn).toBeUndefined();
  });
});

describe('the source assertion that the fix is actually wired in', () => {
  // A pure function proven correct is worth nothing if the component stopped
  // calling it. Chasing the call, not the name.
  const { readFileSync } = require('fs') as typeof import('fs');
  const { join } = require('path') as typeof import('path');
  const src = readFileSync(
    join(process.cwd(), 'components', 'compliance', 'CDCPathway.tsx'),
    'utf8',
  );

  it('CDCPathway builds its lot-size line through lotSizeRequirement', () => {
    expect(src).toMatch(
      /lotSizeRequirement\(lotArea, minArea, lotAreaSource, minAreaCompound\)/,
    );
  });

  it('a null requirement is filtered out rather than rendered', () => {
    // Without this the array would carry a null and the UI would decide what a
    // null requirement looks like -- which is how an absent control becomes a
    // blank row instead of no row.
    expect(src).toMatch(/\.filter\(\(r\): r is Requirement => r !== null\)/);
  });

  it('parseMinLotArea no longer invents a 200m² default or a clause for it', () => {
    // Measured: Fence, Carport and Pool have NO lot-area provision, so this
    // default was gating them on a figure from a literal in this file.
    //
    // Asserted on the CODE forms, not on bare strings. A bare
    // /clause 3\.1 \(default\)/ also matches the comment that documents the
    // removal, so the first version of this test failed against the very
    // explanation of the fix -- a negative source assertion has to name the
    // syntax it forbids, or prose about the defect counts as the defect.
    expect(src).not.toMatch(/minArea:\s*200\b/);
    expect(src).not.toMatch(/source:\s*'SEPP Housing Code Part 3, clause 3\.1 \(default\)'/);
    expect(src).toMatch(/minArea: null, source: null, compound: false/);
  });

  it('the absent area is null, not 0', () => {
    // `|| 0` is what made an unknown area indistinguishable from a measured one.
    expect(src).toMatch(/lotDimensions\?\.area \?\? null/);
    expect(src).not.toMatch(/lotDimensions\?\.area \|\| 0/);
  });

  it('the blocker test compares against null, not against 0', () => {
    expect(src).not.toMatch(/lotArea > 0 && lotArea < minArea/);
    // All three guards must be present: an unknown area cannot block, an absent
    // minimum cannot block, and a compound threshold must not block on its
    // stricter branch alone. `!=`, not `!==`, so undefined counts as absent.
    expect(src).toMatch(
      /lotArea != null && minArea != null && !minAreaCompound && lotArea < minArea/,
    );
  });

  it('the absence guards catch undefined, not only null', () => {
    // The QA gate blocked a push on this. With `=== null`, an undefined lotArea
    // fell through to the pass branch and printed "Lot size NaNm² — meets 200m²
    // minimum" with pass: true — the original defect reached by the other
    // absent value. propertyData is `any`, and this function is exported.
    expect(src).toMatch(/if \(minArea == null\) return null;/);
    expect(src).toMatch(/if \(lotArea == null\) \{/);
    expect(src).not.toMatch(/if \(minArea === null\)/);
    expect(src).not.toMatch(/if \(lotArea === null\)/);
  });

  it('the GFA blocker cannot print a rounded null', () => {
    // Math.round(null) is 0, so an unguarded interpolation would have printed
    // "0m² lot" as the multiplicand of a figure shown to the user.
    expect(src).not.toMatch(/×\s*\$\{Math\.round\(lotArea\)\}/);
  });
});
