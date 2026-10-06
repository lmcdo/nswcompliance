/**
 * The TOD precinct constraint must carry only what the map actually supplies.
 *
 * Until 2026-10-06 `extractConstraints` populated a TOD precinct with five values the
 * Transport Oriented Development Sites Map does not contain:
 *
 *   maxFSRBonus       -> 2.5                      (no FSR field on the layer)
 *   maxHeightBonus    -> 24                       (no height field)
 *   legislativeClause -> 'Clause 4.4'             (no clause field)
 *   seppReference     -> 'SEPP (Housing) 2021'    (EPI_NAME exists, read as 'EPI Name')
 *   precinctName      -> 'TOD Precinct'           (PRECINCT exists, read as 'Precinct Name')
 *
 * Verified against the layer's own metadata on 2026-10-06 — MapServer/3 returns exactly
 * OBJECTID, EPI_NAME, PUBLISHED_DATE, COMMENCED_DATE, AMENDMENT, MAP_NAME, LAY_CLASS,
 * LABEL, PRECINCT, SHAPE, and holds 9,562 features. None of the keys that code tested
 * for existed, so these were not fallbacks for an occasional gap: they were the only
 * code path, firing for every mapped area.
 *
 * Two of them were also wrong on the law. s155 of SEPP (Housing) 2021 sets 22m for a
 * residential flat building and 24m for seniors or shop top housing, so a single height
 * cannot be right for an address; and the TOD standard is s155, not Clause 4.4, which is
 * the ordinary LEP floor-space clause.
 *
 * ATTRIBUTES below are a real feature from the live layer, not invented.
 */
import { NSWPlanningPortalService } from '@/lib/nsw-planning-portal';

/** A real TOD Sites Map feature, fetched 2026-10-06. */
const LIVE_TOD_ATTRIBUTES = {
  OBJECTID: 258648,
  EPI_NAME: 'State Environmental Planning Policy (Housing) 2021',
  PUBLISHED_DATE: 1715299200000,
  COMMENCED_DATE: 1715558400000,
  AMENDMENT: 'Newcastle Local Environmental Plan (Housing) (Map Amendment No 1)',
  MAP_NAME: 'Transport Oriented Development Sites Map',
  LAY_CLASS: 'Transport Oriented Development Area',
  LABEL: '//SP7820',
  PRECINCT: 'KOGARAH',
};

const extract = (attributes: Record<string, unknown>): Record<string, any> =>
  NSWPlanningPortalService.extractPlanningConstraints([
    { layerName: 'Transport Oriented Development Sites Map', results: [attributes] },
  ] as never) as Record<string, any>;

describe('TOD precinct constraints, from a real map feature', () => {
  const tod = extract(LIVE_TOD_ATTRIBUTES).todPrecinct;

  it('is detected', () => {
    expect(tod).toBeDefined();
    expect(tod.inTODArea).toBe(true);
  });

  it("takes the precinct name from the map's own PRECINCT field", () => {
    // Read as 'Precinct Name' before the fix, which never matched, so every area was
    // labelled with the placeholder 'TOD Precinct'.
    expect(tod.precinctName).toBe('KOGARAH');
  });

  it("takes the instrument from the map's own EPI_NAME field", () => {
    // Read as 'EPI Name' before the fix — a space instead of an underscore — so the
    // right answer was reached only by coincidence, via a hardcoded literal.
    expect(tod.seppReference).toBe('State Environmental Planning Policy (Housing) 2021');
  });

  it('states NO floor space ratio or height, because the map carries neither', () => {
    expect(tod.maxFSRBonus).toBeUndefined();
    expect(tod.maxHeightBonus).toBeUndefined();
  });

  it('states NO clause, because the map carries none', () => {
    expect(tod.legislativeClause).toBeUndefined();
  });
});

describe('a map feature with nothing in it', () => {
  // The guard that matters: a silent layer must yield undefined, not a literal. This is
  // the exact shape the old code turned into 2.5 / 24 / 'Clause 4.4' / 'TOD Precinct'.
  const tod = extract({}).todPrecinct;

  it('still reports the property as in a TOD area', () => {
    expect(tod.inTODArea).toBe(true);
  });

  it.each(['precinctName', 'seppReference', 'maxFSRBonus', 'maxHeightBonus', 'legislativeClause'])(
    'leaves %s undefined rather than inventing one',
    (field) => {
      expect(tod[field]).toBeUndefined();
    },
  );

  it('never produces the literals the old code used', () => {
    const serialised = JSON.stringify(tod);
    for (const literal of ['2.5', '24', 'Clause 4.4', 'TOD Precinct', 'SEPP (Housing) 2021']) {
      expect(serialised).not.toContain(literal);
    }
  });
});

/**
 * Cross-review additions, 2026-10-06. Both were real findings against the first version
 * of this fix, and both are the same class of error: a standard stated without the
 * condition that limits it, and a citation pointing at the wrong provision.
 */
import { readFileSync } from 'fs';
import { join } from 'path';

const read = (...parts: string[]) =>
  readFileSync(join(__dirname, '..', '..', ...parts), 'utf8').replace(/\s+/g, ' ');

describe('s155(5) — the standard yields to a higher one elsewhere', () => {
  // s155(5): "This section does not apply to the extent a provision of another chapter of
  // this policy or another environmental planning instrument permits a greater maximum
  // building height or floor space ratio". Stating 2.5:1 without it presents a figure the
  // section itself defers as if it were the property's ceiling.
  it.each([
    ['components/compliance/StateLevelControls.tsx'],
    ['app/assessment/page.tsx'],
  ])('%s discloses the subsection (5) exception', (file) => {
    const src = read(file);
    expect(src).toMatch(/155\(5\)/);
    expect(src).toMatch(/permits a greater (maximum )?height or floor space ratio/i);
  });

  it('does not claim section 155 "sets" the controls', () => {
    // "sets" reads as a ceiling; "identifies ... standards" is the section's own framing
    // and survives subsection (5).
    const src = read('components/compliance/StateLevelControls.tsx');
    expect(src).not.toMatch(/floor space ratio are set by section 155/i);
    expect(src).toMatch(/Section 155 identifies/);
  });
});

describe("the SEE parking control cites parking provisions, not the TOD chapter", () => {
  const src = read('lib/see/seeBuilders.ts');

  it('names the development-type parking sections', () => {
    expect(src).toMatch(/sections 24, 42, 68 and 74/);
  });

  it('does not cite Chapter 5, which is height and FSR', () => {
    // An earlier edit put 'Chapter 5' in this clause field. The requirement beside it is
    // about parking rates, so Chapter 5 sends a reader to the wrong chapter entirely.
    expect(src).not.toMatch(/clause: 'SEPP \(Housing\) 2021 — Transport Oriented Development, Chapter 5'/);
  });
});
