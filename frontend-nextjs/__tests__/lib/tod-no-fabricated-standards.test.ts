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

/**
 * Read a source file with its COMMENTS STRIPPED.
 *
 * The first version of these assertions scanned raw source, so the comment quoting
 * s155(5) beside the JSX could satisfy them even after the visible paragraph was
 * deleted. Forcing that deletion did fail the suite — but only because the comment
 * happens to say "maximum building height" while the rendered text says "maximum
 * height", so the regex missed it by one word. A comment worded like the paragraph
 * would have kept the suite green while users lost the caveat. Cross-review caught
 * this, and it is the same flaw already fixed in
 * __tests__/compliance/sepp-parking-cards-match-law.test.tsx — written again in a new
 * file, which is why the helper now lives here rather than in each assertion.
 */
const read = (...parts: string[]) =>
  readFileSync(join(__dirname, '..', '..', ...parts), 'utf8')
    .replace(/\{\s*\/\*[\s\S]*?\*\/\s*\}/g, ' ')   // {/* JSX comment */}
    .replace(/\/\*[\s\S]*?\*\//g, ' ')                 // /* block */
    .replace(/^\s*\/\/.*$/gm, ' ')                      // // line
    .replace(/\s+/g, ' ');

describe('s155(5) — the standard yields to a higher one elsewhere', () => {
  // s155(5): "This section does not apply to the extent a provision of another chapter of
  // this policy or another environmental planning instrument permits a greater maximum
  // building height or floor space ratio". Stating 2.5:1 without it presents a figure the
  // section itself defers as if it were the property's ceiling.
  /**
   * Scoped to each TOD panel's own region, not the whole file.
   *
   * A whole-file match was demonstrably hollow: deleting the visible caveat from the
   * assessment page's panel and moving the same words into an unused constant left all
   * 21 assertions green. Cross-review raised it; forcing it proved it. Each region runs
   * from the panel's own heading to the first thing after it, so text parked anywhere
   * else in the file — a dead branch, another component, a constant — cannot satisfy it.
   */
  const panel = (file: string, from: string, to: string) => {
    const src = read(file);
    const start = src.indexOf(from);
    const end = src.indexOf(to, start + 1);
    expect(start).toBeGreaterThan(-1);
    expect(end).toBeGreaterThan(start);
    const region = src.slice(start, end);
    expect(region.length).toBeGreaterThan(150);
    return region;
  };

  it.each([
    ['components/compliance/StateLevelControls.tsx', 'TOD development standards',
     'remain in force until the rezoning is gazetted'],
    ['app/assessment/page.tsx', 'Transport Oriented Development Area', 'acceleratedTOD'],
  ])('%s discloses the subsection (5) exception inside the TOD panel itself', (file, from, to) => {
    const region = panel(file, from, to);
    expect(region).toMatch(/155\(5\)|subsection \(5\)/);
    expect(region).toMatch(/permits a greater height or floor space ratio/i);
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

describe('the mapped-TOD panel does not tell the reader to wait for a rezoning', () => {
  // s155 operates for an area already on the Transport Oriented Development Sites Map.
  // "LEP controls remain in force until rezoning is gazetted" belongs to the ACCELERATED
  // precinct panel, which does await one; in the mapped panel it inverts the meaning and
  // would have a reader treat a lower LEP limit as governing. Cross-review, 2026-10-06.
  const src = read('components/compliance/StateLevelControls.tsx');
  // The mapped panel runs from its own heading to the accelerated panel's rezoning
  // sentence. 'Accelerated TOD Precinct' is NOT the end marker — that string appears
  // earlier in the file too, which made this slice empty and the assertion vacuous.
  const start = src.indexOf('TOD development standards');
  const end = src.indexOf('remain in force until the rezoning is gazetted');
  const mapped = src.slice(start, end);

  it('slices a non-empty region, so the assertions below are not vacuous', () => {
    expect(start).toBeGreaterThan(-1);
    expect(end).toBeGreaterThan(start);
    expect(mapped.length).toBeGreaterThan(200);
  });

  it('says the controls are read together, not sequenced by a rezoning', () => {
    expect(mapped).toMatch(/Read the LEP and SEPP controls together/);
    expect(mapped).toMatch(/including subsection \(5\)/);
  });

  it('does not claim LEP controls hold until rezoning', () => {
    expect(mapped).not.toMatch(/remain in force until rezoning is gazetted/);
  });

  it('leaves the accelerated panel saying it, where it IS correct', () => {
    expect(src).toMatch(/remain in force until the rezoning is gazetted/);
  });
});
