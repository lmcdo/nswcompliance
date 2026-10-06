/**
 * prior-art-checked: `lib/citation-display.ts` (the module that already owns
 * "show a clause only when it is proven" — the new label lives there rather than
 * in a fourth copy), `__tests__/components/compliance/DcpRequestCta.test.tsx`
 * (render + mocked-fetch convention), `__tests__/lib/tod-no-fabricated-standards.test.ts`
 * (the same defect class for TOD, #1229), `__tests__/components/compliance/no-invented-lot-width.test.tsx`
 * (#1231). No parallel surface.
 *
 * A clause or an instrument we were not given is not stated.
 *
 * Eleven fabricated citations were removed on 2026-10-06. Every one had the same
 * shape — a real-looking regulatory reference substituted when the Planning Portal
 * response, or a database row, carried none:
 *
 *   'Clause 4.3' / 'Clause 4.4'  height and FSR, in ComplianceDashboard
 *   'Clause 2.3' / 'Clause 4.1'  zoning and minimum lot size, as DEFAULT PARAMETERS
 *   'Clause 5.10'                heritage, in HeritageDetails
 *   'Schedule 1 & 2' + 'SEPP (Sustainable Buildings) 2022'   a SEPP provision panel
 *   'SEPP (Housing) 2021'        the LMR uplift note, twice
 *   'Local Environmental Plan' and 'Inner West Local Environmental Plan 2022'
 *                                as the instrument, for a property in ANY council
 *
 * Each is the usual clause for its topic in most NSW LEPs — 4.3 height, 4.4 FSR,
 * 2.3 zoning, 4.1 minimum lot size, 5.10 heritage. That is exactly what made them
 * dangerous: a wrong one would never have looked wrong.
 *
 * Two shapes the fabricated-citation counter cannot see, and which is why its
 * figure of 12 was itself an undercount:
 *   - a DEFAULT PARAMETER (`legislativeClause = 'Clause 2.3'`), because the
 *     literal sits in the component that RECEIVES the value, not the one that
 *     passes it;
 *   - a hardcoded instrument in JSX text (`{clause} Inner West LEP 2022`), which
 *     is not a `||` fallback at all.
 *
 * Reachability, measured rather than assumed:
 *   LIVE      LandUseZoningCard   <- LepControls.tsx:84 <- app/assessment/page.tsx:592
 *   LIVE      ConstraintArithmeticCard <- the same page, and app/reports/intelligence-brief
 *   LATENT    ComplianceDashboard, HeritageDetails, MinimumLotSizeCard — nothing
 *             renders ComplianceDashboard (`<ComplianceDashboard` appears nowhere,
 *             and ComplianceDashboardV2 is unmounted too), and the other two are
 *             only reached through it.
 */

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';

import { asTrimmedString, instrumentClauseLabel } from '@/lib/citation-display';
import { lmrCitationText } from '@/components/compliance/ConstraintArithmeticCard';
import { LandUseZoningCard } from '@/components/compliance/LandUseZoningCard';
import { deduplicateConstraints } from '@/lib/compliance/constraint-dedup';
import type { ComplianceConstraint } from '@/components/compliance/ComplianceDashboard';

/** Every literal removed on 2026-10-06. None may be produced from absent data. */
const REMOVED_LITERALS = [
  'Clause 2.3',
  'Clause 4.1',
  'Clause 4.3',
  'Clause 4.4',
  'Clause 5.10',
  'Schedule 1 & 2',
  'SEPP (Housing) 2021',
  'SEPP (Sustainable Buildings) 2022',
  'Local Environmental Plan',
  'Inner West Local Environmental Plan 2022',
  'Inner West LEP 2022',
];

describe('instrumentClauseLabel names only what the source named', () => {
  it('joins the instrument and the clause when both are known', () => {
    expect(instrumentClauseLabel('Bayside Local Environmental Plan 2021', 'Clause 4.3')).toBe(
      'Bayside Local Environmental Plan 2021 — Clause 4.3',
    );
  });

  it('returns whichever single one is known', () => {
    expect(instrumentClauseLabel('Bayside Local Environmental Plan 2021', null)).toBe(
      'Bayside Local Environmental Plan 2021',
    );
    expect(instrumentClauseLabel(null, 'Clause 4.3')).toBe('Clause 4.3');
  });

  it.each<[string, unknown, unknown]>([
    ['both null', null, null],
    ['both undefined', undefined, undefined],
    ['both empty', '', ''],
    ['both whitespace', '   ', '\t'],
    ['empty instrument, whitespace clause', '', ' '],
  ])('%s -> null, so the caller can drop the badge entirely', (_label, epi, clause) => {
    expect(instrumentClauseLabel(epi as string | null, clause as string | null)).toBeNull();
  });

  it.each(REMOVED_LITERALS)('never invents %s from absent data', (literal) => {
    for (const out of [
      instrumentClauseLabel(null, null),
      instrumentClauseLabel(undefined, undefined),
      instrumentClauseLabel('', ''),
    ]) {
      expect(out ?? '').not.toContain(literal);
    }
  });

  it('passes a supplied value through unchanged, including one of the old literals', () => {
    // The guard above must not be implemented by blacklisting strings: a Portal
    // response that genuinely says Clause 4.3 must still show Clause 4.3.
    expect(instrumentClauseLabel(null, 'Clause 4.3')).toBe('Clause 4.3');
  });
});

describe('a value from an untyped Portal response cannot crash the page', () => {
  /**
   * The QA gate blocked a push on three unguarded calls -- epiName.trim(),
   * clause.replace(), clause.trim() -- and it was right. `planningLayers` and the
   * heritage record are `any`, so the declared `string | null` was a statement of
   * intent, not of runtime: a numeric 'EPI Name' would make .trim() throw and take
   * the whole page down. That is a worse failure than the fabricated citation this
   * change removed, so it is covered rather than merely typed.
   */
  it.each<[string, unknown]>([
    ['a number', 4.3],
    ['a boolean', true],
    ['an array', ['Clause 4.3']],
    ['an object', { clause: 'Clause 4.3' }],
    ['null', null],
    ['undefined', undefined],
    ['an empty string', ''],
    ['whitespace', '   '],
  ])('%s is not text, so it yields null rather than throwing', (_label, value) => {
    expect(() => asTrimmedString(value)).not.toThrow();
    expect(asTrimmedString(value)).toBeNull();
  });

  it('trims a real string and keeps it', () => {
    expect(asTrimmedString('  Bayside Local Environmental Plan 2021  ')).toBe(
      'Bayside Local Environmental Plan 2021',
    );
  });

  it.each<[string, unknown, unknown]>([
    ['numbers for both', 4.3, 2021],
    ['an object for the instrument', { name: 'x' }, 'Clause 4.3'],
    ['an array for the clause', 'Bayside LEP 2021', ['Clause 4.3']],
  ])('instrumentClauseLabel survives %s', (_label, epi, clause) => {
    expect(() => instrumentClauseLabel(epi, clause)).not.toThrow();
  });

  it('a numeric EPI name yields the clause alone, not a stringified number', () => {
    // The specific shape the gate warned about: a Portal field that is not text.
    expect(instrumentClauseLabel(2021, 'Clause 4.3')).toBe('Clause 4.3');
  });
});

describe('lmrCitationText names the instrument only when the data names one', () => {
  it('uses the document when present', () => {
    expect(lmrCitationText('State Environmental Planning Policy (Housing) 2021', '157')).toBe(
      'State Environmental Planning Policy (Housing) 2021 cl 157',
    );
  });

  it.each<[string, unknown]>([
    ['null', null],
    ['undefined', undefined],
    ['empty', ''],
  ])('falls back to the bare clause when the document is %s', (_label, doc) => {
    expect(lmrCitationText(doc as string | null, '157')).toBe('clause 157');
  });

  it('never invents SEPP (Housing) 2021', () => {
    // The old code read `lmr_source_document || 'SEPP (Housing) 2021'`, and
    // services/housing_sepp_eligibility.py defaults source_document to None.
    for (const doc of [null, undefined, '']) {
      expect(lmrCitationText(doc as string | null, '157')).not.toContain('SEPP (Housing) 2021');
    }
  });
});

describe('LandUseZoningCard — the live surface', () => {
  beforeEach(() => {
    global.fetch = jest.fn(() =>
      Promise.resolve({ ok: true, json: () => Promise.resolve({ success: true, data: {} }) }),
    ) as unknown as jest.Mock;
  });
  afterEach(() => jest.resetAllMocks());

  it('states no clause when the Planning Portal response carried none', async () => {
    // LepControls passes `zoneResult?.['Legislative Clause']`, i.e. undefined when
    // the response has no clause. That is what used to trigger `= 'Clause 2.3'`.
    const { container } = render(<LandUseZoningCard zone="R2" lga="Bayside" />);
    await waitFor(() => expect(screen.getByText(/R2/)).toBeInTheDocument());

    for (const literal of REMOVED_LITERALS) {
      expect(container.textContent).not.toContain(literal);
    }
  });

  it('shows the real instrument and clause when the response carries them', async () => {
    render(
      <LandUseZoningCard
        zone="R2"
        lga="Bayside"
        epiName="Bayside Local Environmental Plan 2021"
        legislativeClause="Clause 2.3"
      />,
    );
    expect(
      await screen.findByText(/Bayside Local Environmental Plan 2021 — Clause 2.3/),
    ).toBeInTheDocument();
  });

  it('renders NO badge at all when it has neither instrument nor clause', async () => {
    /**
     * Asserting on the TEXT is not enough, and the mutation harness proved it:
     * changing `{citation && (` to `{true && (` renders an EMPTY badge, which
     * contains none of the forbidden literals, so every text assertion still
     * passed. An empty badge is not harmless — it is a labelled source slot with
     * nothing in it, which reads as a rendering fault rather than as "the Portal
     * named no instrument". So the element itself must be absent.
     */
    const { container } = render(<LandUseZoningCard zone="R2" lga="Bayside" />);
    await waitFor(() => expect(screen.getByText(/R2/)).toBeInTheDocument());
    expect(container.querySelectorAll('[data-slot="badge"]')).toHaveLength(0);
  });

  it('renders exactly one badge when it has a citation', async () => {
    // The positive control for the assertion above: it must be possible to fail.
    const { container } = render(
      <LandUseZoningCard
        zone="R2"
        lga="Bayside"
        epiName="Bayside Local Environmental Plan 2021"
        legislativeClause="Clause 2.3"
      />,
    );
    await waitFor(() => expect(screen.getByText(/R2/)).toBeInTheDocument());
    expect(container.querySelectorAll('[data-slot="badge"]')).toHaveLength(1);
  });

  it('shows the instrument alone rather than pairing it with a guessed clause', async () => {
    const { container } = render(
      <LandUseZoningCard zone="R2" lga="Bayside" epiName="Bayside Local Environmental Plan 2021" />,
    );
    expect(await screen.findByText('Bayside Local Environmental Plan 2021')).toBeInTheDocument();
    expect(container.textContent).not.toContain('Clause 2.3');
  });
});

/**
 * Source ratchet. Read with COMMENTS STRIPPED, because this file's own header and
 * the provenance comments left at each fix site name every literal above.
 */
import { readFileSync } from 'fs';
import { join } from 'path';

const readStripped = (...parts: string[]) =>
  readFileSync(join(__dirname, '..', '..', '..', ...parts), 'utf8')
    /**
     * The MINIMAL block-comment matcher, `(?:[^*]|\*(?!\/))*`, which cannot cross
     * a `*&#47;` and is therefore bounded.
     *
     * The helper copied from the earlier suites led with a JSX-comment rule,
     * `\{\s*\/\*[\s\S]*?\*\/\s*\}`. In JSX a bare `{` opens every expression and
     * `*&#47;}` closes every JSX comment, so that non-greedy span ran from one `{`
     * to a much later `*&#47;}` and deleted everything between. On
     * ComplianceDashboard.tsx it cut 66,075 characters to 17,106 — 59% of the
     * file, including both blocks this suite exists to check. Measured 2026-10-06
     * by the mutation harness: reintroducing `|| 'Clause 4.3'` changed nothing,
     * because the line was no longer in the text being searched.
     *
     * Measured on every other file these suites read (StateLevelControls.tsx,
     * app/api/setbacks/calculate/route.ts, PreciseSetbackCalculator.tsx,
     * EnhancedSetbackVerification.tsx, lib/geometry/calculator.ts,
     * lib/see/seeBuilders.ts): the old rule lost no marker, differing by under
     * 200 characters. So #1229, #1230 and #1231 were lucky rather than wrong —
     * verified, not assumed.
     */
    .replace(/\/\*(?:[^*]|\*(?!\/))*\*\//g, ' ')
    .replace(/(^|[^:])\/\/.*$/gm, '$1 ')
    .replace(/\s+/g, ' ');

/**
 * Markers that MUST survive stripping, per file.
 *
 * A length check is not a non-vacuity guard: the truncated ComplianceDashboard
 * was still 17,106 characters, so `length > 500` passed while the region under
 * test had been deleted. Naming the code each file's assertions depend on is the
 * only check that fails when the text is silently cut.
 */
const SURVIVING_MARKERS: Record<string, string[]> = {
  'ComplianceDashboard.tsx': ['heightClause', 'fsrClause', 'lepMetadataFrom', 'lepName'],
  'ConstraintArithmeticCard.tsx': ['lmrCitationText'],
  'HeritageDetails.tsx': ['legislativeControlLabel'],
  'LandUseZoningCard.tsx': ['instrumentClauseLabel'],
  'MinimumLotSizeCard.tsx': ['instrumentClauseLabel'],
};

const TOUCHED: Array<[string, string[]]> = [
  ['ComplianceDashboard', ['components', 'compliance', 'ComplianceDashboard.tsx']],
  ['ConstraintArithmeticCard', ['components', 'compliance', 'ConstraintArithmeticCard.tsx']],
  ['HeritageDetails', ['components', 'compliance', 'HeritageDetails.tsx']],
  ['LandUseZoningCard', ['components', 'compliance', 'LandUseZoningCard.tsx']],
  ['MinimumLotSizeCard', ['components', 'compliance', 'MinimumLotSizeCard.tsx']],
];

describe('removing the invented clause must not make two controls collide', () => {
  // Cross-review finding, 2026-10-07: the invented 'Clause 4.3' / 'Clause 4.4'
  // were doing unintended work as the deduplication key. With both nulled, a
  // Portal response naming an instrument but no clause gave height and FSR the
  // same key, and FSR was silently dropped from the assessment.
  const constraint = (
    type: ComplianceConstraint['type'],
    value: number,
    unit: string,
    clause: string | null,
    document: string | null,
  ): ComplianceConstraint => ({
    type,
    value,
    unit,
    source: { clause, document, authority_level: 'LEP' },
  });

  it('keeps height and FSR when the Portal named an instrument but no clause', () => {
    const kept = deduplicateConstraints([
      constraint('height', 8.5, 'm', null, 'Bayside LEP 2021'),
      constraint('fsr', 0.5, ':1 sq m', null, 'Bayside LEP 2021'),
    ]);
    expect(kept).toHaveLength(2);
    expect(kept.map(c => c.type)).toEqual(['height', 'fsr']);
  });

  it('keeps them when the response names neither instrument nor clause', () => {
    const kept = deduplicateConstraints([
      constraint('height', 8.5, 'm', null, null),
      constraint('fsr', 0.5, ':1 sq m', null, null),
    ]);
    expect(kept).toHaveLength(2);
  });

  it('still drops a genuine repeat of the same control', () => {
    // The positive control: if this passed too, the key would just be unique
    // per row and the function would be deduplicating nothing at all.
    const kept = deduplicateConstraints([
      constraint('height', 8.5, 'm', null, 'Bayside LEP 2021'),
      constraint('height', 8.5, 'm', null, 'Bayside LEP 2021'),
    ]);
    expect(kept).toHaveLength(1);
  });

  it('does not let a hyphen inside a field forge a collision', () => {
    // Cross-review round 2: the key joined fields with '-', so a separator that
    // can also occur INSIDE a field made two distinct constraints serialise
    // identically -- 'A-B' + 'C' and 'A' + 'B-C' both gave '...:A-B-C'.
    const kept = deduplicateConstraints([
      constraint('height', 8.5, 'm', 'A-B', 'C'),
      constraint('height', 8.5, 'm', 'A', 'B-C'),
    ]);
    expect(kept).toHaveLength(2);
  });

  it('still prefers provision_id when there is one', () => {
    const a = { ...constraint('height', 8.5, 'm', null, null), provision_id: 7 };
    const b = { ...constraint('fsr', 0.5, ':1 sq m', null, null), provision_id: 7 };
    expect(deduplicateConstraints([a, b])).toHaveLength(1);
  });
});

describe('an untyped Portal value cannot reach the citation as-is', () => {
  // Cross-review finding, 2026-10-07: these four read from `planningLayers`,
  // which is `any`, and were assigned straight to `string | null`. A numeric
  // clause reaches ConstraintCard's `.match()` and crashes the surface; a
  // whitespace clause renders a blank source.
  const src = () => readStripped('components', 'compliance', 'ComplianceDashboard.tsx');

  it.each([
    ['heightClause', 'Legislative Clause'],
    ['heightEpi', 'EPI Name'],
    ['fsrClause', 'Legislative Clause'],
    ['fsrEpi', 'EPI Name'],
  ])('%s is guarded by asTrimmedString', (name) => {
    // Requires the CALL on that binding, not merely the identifier somewhere.
    expect(src()).toMatch(new RegExp(`const ${name}\\s*=\\s*asTrimmedString\\(`));
  });

  it('the LEP section heading is guarded too', () => {
    expect(src()).toMatch(/const lepName\s*=\s*asTrimmedString\(/);
  });

  it('a whitespace-only instrument is treated as absent, not rendered blank', () => {
    expect(asTrimmedString('   ')).toBeNull();
    expect(instrumentClauseLabel('   ', '  ')).toBeNull();
  });
});

describe('no touched file substitutes a citation any more', () => {
  it.each(TOUCHED)('%s keeps the code its assertions depend on', (_name, parts) => {
    const file = parts[parts.length - 1];
    const src = readStripped(...parts);
    expect(src.length).toBeGreaterThan(500);
    for (const marker of SURVIVING_MARKERS[file] ?? []) {
      // If stripping ever eats the region again, this says so instead of passing.
      expect(src).toContain(marker);
    }
  });

  it.each(TOUCHED)('%s has no fallback to a regulatory literal', (_name, parts) => {
    const src = readStripped(...parts);
    // The `||` / `??` shape.
    // All three quote styles, matched by backreference so the closing quote is
    // the same as the opening one. Single quotes alone left the gate open to
    // `|| "Clause 5.10"`, which is the same defect spelled differently, and this
    // tree uses double quotes too -- HeritageDetails.tsx opens with "use client".
    // `[^'"`$]` rather than `[^'"`]`: a template literal that INTERPOLATES is
    // not a hardcoded citation -- `Part ${provision.v2_part}` names whatever the
    // data said. A backtick literal with no ${ is hardcoded and still caught.
    expect(src).not.toMatch(/(\|\||\?\?)\s*(['"`])(?:Clause|Schedule|SEPP|Part |Section )[^'"`$]*\2/);
    // The DEFAULT PARAMETER shape, which the counter cannot see.
    expect(src).not.toMatch(/=\s*(['"`])(?:Clause|Schedule|SEPP|Part |Section )[^'"`$]*\1\s*[},]/);
    // A hardcoded instrument in JSX text, which is not a fallback at all.
    expect(src).not.toMatch(/Inner West (Local Environmental Plan|LEP)/);
    expect(src).not.toMatch(/Inner_West_Local_Environmental_Plan/);
  });

  it('the height and FSR panels no longer post a hardcoded LEP document id', () => {
    const src = readStripped('components', 'compliance', 'ComplianceDashboard.tsx');
    // It used to post Inner West + clause 4.3 / 4.4 to /api/lep/full-text for every
    // property in NSW, so another council's lot was served Inner West clause text.
    expect(src).toMatch(/lepMetadataFrom\(/);
    expect(src).not.toMatch(/documentId: '[A-Za-z_]+___NSW_Legislation'/);
    expect(src).not.toMatch(/refNumber: '\d/);
  });

  it('the one honest fallback is left alone', () => {
    // 'Clause Reference Not Available' states the absence instead of filling it,
    // so it is not in this class and must not be "fixed" into silence.
    const src = readStripped('components', 'compliance', 'ReferencedLegislationAccordion.tsx');
    expect(src).toContain('Clause Reference Not Available');
  });
});
