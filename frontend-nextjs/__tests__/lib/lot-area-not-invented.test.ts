/**
 * prior-art-checked: `lib/geometry/mercator.ts` (the module under test, already the
 * repo's single source of truth for EPSG:3857 rings), `__tests__/api/lot-search.test.ts`
 * (the only existing geometry test, unrelated — it covers address search), and the TOD
 * fabrication suite on PR #1229's branch, from which the comment-stripping helper below
 * is reproduced. No parallel surface.
 *
 * No lot dimension or buildable-area figure may be invented.
 *
 * Five separate invented real-world values were measured on the setbacks path on
 * 2026-10-06. None of them reached a user, because nothing mounts this feature —
 * no route renders AnalysisTabs, PreciseSetbackCalculator or
 * EnhancedSetbackVerification, and `lib/geometry/calculator.ts` has no consumer.
 * They are recorded here because a one-line mount is all that stands between the
 * code and a user, and because four of the five looked like measurements:
 *
 *   1. `app/api/setbacks/calculate/route.ts` — `lot_area || (zone === 'R2' ? 500 : 400)`
 *      at two sites, returned as `total_lot_area`.
 *   2. the same route — `buildable_area: lotArea * 0.6`, `buildable_percentage: 60`,
 *      `setback_area_lost: lotArea * 0.4`, in the endpoint whose purpose is to
 *      derive buildable area from the setbacks it had just queried. It used none
 *      of them. The flat 60 also made the component's own
 *      `buildable_percentage < 50` design note unreachable.
 *   3. `PreciseSetbackCalculator.estimateLotArea` — a bounding box (not the
 *      polygon) over `1.2 * 1.2` (a hand-typed latitude constant) over 1000 (no
 *      geometric meaning), clamped to [100, 5000]. MEASURED: it returns exactly
 *      100 for every lot below 99,217 m2 — 9.92 ha — so for every residential lot
 *      in NSW it was a constant. Its no-geometry branch returned 450.
 *   4. `EnhancedSetbackVerification.estimateLotArea` — a shoelace with NO Mercator
 *      correction, so 1/cos^2(latitude) high: a factor of 1.4514 at Petersham,
 *      reporting a true 450 m2 lot as 653 m2.
 *   5. `property_zone: property.zone || 'R2'` at three call sites, plus a
 *      displayed `'9.5m'` height limit and `'0.6:1'` FSR. The zone selects which
 *      setback rules the endpoint returns, so a wrong one returns wrong rules.
 *
 * The behavioural assertions below are the real test. The source assertions after
 * them are a ratchet against the literals coming back, and they read source with
 * COMMENTS STRIPPED — the paragraph above names '9.5m', '0.6:1' and 'R2', and
 * would satisfy an unstripped scan on its own.
 */
import { readFileSync } from 'fs';
import { join } from 'path';
import { lotGeometryAreaM2, ringAreaM2, scaleFactorForRing } from '@/lib/geometry/mercator';

/** EPSG:3857 half-extent, in metres. */
const R = 20037508.342789244;
const lngToX = (lng: number) => (R * lng) / 180;
const latToY = (lat: number) => (R * Math.log(Math.tan(Math.PI / 4 + ((lat * Math.PI) / 180) / 2))) / Math.PI;

/** 118 Audley St, Petersham — the address this defect was found on. */
const PETERSHAM = { lat: -33.8945, lng: 151.154 };

/**
 * A closed square ring of a known TRUE ground area, at Petersham.
 *
 * Built by inflating the true side length by the Mercator scale factor, which is
 * what the projection does to a real lot. A correct reader divides it back out.
 */
function squareRingOfTrueArea(trueAreaM2: number): number[][] {
  const x0 = lngToX(PETERSHAM.lng);
  const y0 = latToY(PETERSHAM.lat);
  const sf = scaleFactorForRing([[x0, y0]]);
  const side = Math.sqrt(trueAreaM2) * sf;
  return [
    [x0, y0],
    [x0 + side, y0],
    [x0 + side, y0 + side],
    [x0, y0 + side],
    [x0, y0],
  ];
}

/** The uncorrected shoelace the two components used to carry. */
function uncorrectedShoelace(ring: number[][]): number {
  let area = 0;
  for (let i = 0; i < ring.length - 1; i++) {
    area += ring[i][0] * ring[i + 1][1];
    area -= ring[i + 1][0] * ring[i][1];
  }
  return Math.abs(area / 2);
}

describe('ringAreaM2 measures ground area, not projected area', () => {
  it.each([200, 450, 500, 1000, 4117.7])('a true %s m2 lot measures as itself', (trueArea) => {
    const got = ringAreaM2(squareRingOfTrueArea(trueArea));
    expect(got).not.toBeNull();
    // 0.5% covers the spherical-Mercator approximation over a lot-sized polygon.
    expect(got! / trueArea).toBeCloseTo(1, 2);
  });

  it('is 1/cos^2(latitude) below the uncorrected shoelace the components used', () => {
    const ring = squareRingOfTrueArea(450);
    const corrected = ringAreaM2(ring)!;
    const raw = uncorrectedShoelace(ring);
    const sf = scaleFactorForRing(ring);

    expect(raw / corrected).toBeCloseTo(sf * sf, 4);
    // The concrete defect: a 450 m2 lot read as 653 m2.
    expect(Math.round(raw)).toBe(653);
    expect(Math.round(corrected)).toBe(450);
  });

  it('gives the same area for a closed and an unclosed ring', () => {
    const closed = squareRingOfTrueArea(500);
    const unclosed = closed.slice(0, -1);
    expect(ringAreaM2(unclosed)!).toBeCloseTo(ringAreaM2(closed)!, 6);
  });
});

describe('an unmeasurable ring yields null, never a substituted number', () => {
  // null is the whole point. The old code returned 0, 450 or 100 here, each of
  // which reads downstream as a measured lot size.
  it.each<[string, unknown]>([
    ['null', null],
    ['undefined', undefined],
    ['an empty array', []],
    ['a non-array', 'rings'],
    ['a single point', [[0, 0]]],
    ['two points', [[0, 0], [1, 1]]],
    ['a ring holding NaN', [[0, 0], [NaN, 1], [1, 1], [0, 0]]],
    ['a ring holding Infinity', [[0, 0], [1, Infinity], [1, 1], [0, 0]]],
    ['a malformed point', [[0, 0], [1], [1, 1], [0, 0]]],
  ])('%s -> null', (_label, ring) => {
    expect(ringAreaM2(ring)).toBeNull();
  });

  it.each([450, 100, 500, 400, 0])('never returns the old substitute %s', (substitute) => {
    expect(ringAreaM2(null)).not.toBe(substitute);
  });

  /**
   * A zero-area ring is structurally valid and must still be null.
   *
   * Cross-review finding, 2026-10-06, confirmed by measurement before it was
   * fixed: ringAreaM2([[0,0],[10,0],[20,0],[0,0]]) returned 0. That 0 is not
   * merely a misleading figure -- `lot_area` at the endpoint is
   * z.number().positive(), so a 0 fails validation and returns 400 for the WHOLE
   * request, discarding the zone setback rules that need no area at all.
   */
  it.each<[string, number[][]]>([
    ['a collinear ring', [[0, 0], [10, 0], [20, 0], [0, 0]]],
    ['a ring of one repeated point', [[5, 5], [5, 5], [5, 5], [5, 5]]],
    ['a there-and-back ring', [[0, 0], [10, 0], [0, 0], [0, 0]]],
  ])('%s encloses no area, so it is null and never 0', (_label, ring) => {
    expect(ringAreaM2(ring)).toBeNull();
    expect(lotGeometryAreaM2({ rings: [ring] })).toBeNull();
  });

  it('never returns a value the endpoint would reject as non-positive', () => {
    // The guard that ties this module to the schema it feeds.
    for (const ring of [
      [[0, 0], [10, 0], [20, 0], [0, 0]],
      squareRingOfTrueArea(450),
    ]) {
      const got = ringAreaM2(ring);
      if (got !== null) expect(got).toBeGreaterThan(0);
    }
  });
});

describe('lotGeometryAreaM2 refuses a geometry it cannot measure as a whole lot', () => {
  const ring = squareRingOfTrueArea(600);

  it('measures a single-ring geometry', () => {
    expect(lotGeometryAreaM2({ rings: [ring] })!).toBeCloseTo(600, 0);
  });

  it.each<[string, unknown]>([
    ['no rings key', {}],
    ['an empty rings array', { rings: [] }],
    ['null', null],
    ['a string', 'geometry'],
  ])('%s -> null', (_label, geometry) => {
    expect(lotGeometryAreaM2(geometry)).toBeNull();
  });

  it('returns null for a multi-ring geometry rather than the outer ring alone', () => {
    // An inner ring is a hole. Reporting the outer ring as the lot would overstate
    // it, and this code has no caller that subtracts holes.
    expect(lotGeometryAreaM2({ rings: [ring, ring] })).toBeNull();
  });
});

/**
 * Source read with COMMENTS STRIPPED.
 *
 * Reproduced deliberately from the TOD fabrication suite on PR #1229's branch — not
 * present on this branch — where an unstripped scan was satisfied by a comment beside
 * the code it was meant to check. This file's own header names every forbidden literal.
 */
const readStripped = (...parts: string[]) =>
  readFileSync(join(__dirname, '..', '..', ...parts), 'utf8')
    .replace(/\{\s*\/\*[\s\S]*?\*\/\s*\}/g, ' ') // {/* JSX comment */}
    .replace(/\/\*[\s\S]*?\*\//g, ' ') //           /* block */
    .replace(/(^|[^:])\/\/.*$/gm, '$1 ') //         // line, and trailing
    .replace(/\s+/g, ' ');

describe('the setbacks endpoint states no figure it did not derive', () => {
  const src = readStripped('app', 'api', 'setbacks', 'calculate', 'route.ts');

  it('reads the file at all, so the assertions below are not vacuous', () => {
    expect(src.length).toBeGreaterThan(2000);
    expect(src).toContain('buildable_area_analysis');
  });

  it.each([
    ["the zone-defaulted lot area", /\?\s*500\s*:\s*400/],
    ['the 60% buildable ratio', /\*\s*0\.6/],
    ['the 40% lost ratio', /\*\s*0\.4/],
    ['a hardcoded buildable percentage', /buildable_percentage:\s*\d/],
    ['a hardcoded lot area', /total_lot_area:\s*\d/],
    ['the old local variable', /estimatedLotArea/],
  ])('does not contain %s', (_label, pattern) => {
    expect(src).not.toMatch(pattern);
  });

  it('routes every buildable-area response through the one helper', () => {
    // `buildableAreaNotDerived(` matches its own declaration too, so the
    // declaration is excluded — counting it as a call is what made the first
    // version of this assertion read 6 against 5 and fail on correct code.
    const calls = (src.match(/buildableAreaNotDerived\(/g) ?? []).length
      - (src.match(/function buildableAreaNotDerived\(/g) ?? []).length;
    const blocks = (src.match(/buildable_area_analysis:/g) ?? []).length;

    expect(blocks).toBeGreaterThanOrEqual(5);
    // Every response block is a call to the helper and nothing else. A new block
    // written as a literal object raises `blocks` without raising `calls`.
    expect(calls).toBe(blocks);
  });

  it('states why a figure is absent', () => {
    expect(src).toMatch(/unavailable_reason/);
  });
});

describe('neither setback component invents a dimension or a control', () => {
  const files = [
    ['components', 'analysis', 'PreciseSetbackCalculator.tsx'],
    ['components', 'analysis', 'EnhancedSetbackVerification.tsx'],
  ] as const;

  it.each(files.map((f) => [f.join('/'), f] as const))('%s is read, not skipped', (_name, parts) => {
    expect(readStripped(...parts).length).toBeGreaterThan(2000);
  });

  it.each(files.map((f) => [f.join('/'), f] as const))(
    '%s takes lot area from the shared corrected function',
    (_name, parts) => {
      const src = readStripped(...parts);
      // The trailing `(` matters. `toMatch(/lotGeometryAreaM2/)` was satisfied by
      // the IMPORT line alone, so replacing the real call with `= 450` left this
      // suite green -- found by the mutation harness, 2026-10-06. Only a call
      // site has a paren after the name.
      expect(src).toMatch(/lotGeometryAreaM2\(/);
      expect(src).toMatch(/@\/lib\/geometry\/mercator/);
      // No local copy of the arithmetic, under any name.
      expect(src).not.toMatch(/estimateLotArea/);
      expect(src).not.toMatch(/function\s+\w*[Ll]otArea\w*\s*\(/);
      // And lot_area is never assigned a number from anywhere but that call.
      expect(src).not.toMatch(/lot_area\s*[:=]\s*[\d.]/);
      expect(src).not.toMatch(/measuredArea\s*=\s*[\d.]/);
    },
  );

  it.each(files.map((f) => [f.join('/'), f] as const))(
    '%s does not substitute a zone, a height or an FSR',
    (_name, parts) => {
      const src = readStripped(...parts);
      expect(src).not.toMatch(/\|\|\s*'R2'/);
      expect(src).not.toMatch(/'9\.5m'/);
      expect(src).not.toMatch(/'0\.6:1'/);
      expect(src).not.toMatch(/return\s+450/);
      expect(src).not.toMatch(/1\.2\s*\*\s*1\.2/);
    },
  );

  it('the dead bounding-box estimator and its clamp are gone', () => {
    const src = readStripped('components', 'analysis', 'PreciseSetbackCalculator.tsx');
    expect(src).not.toMatch(/areaEstimate/);
    expect(src).not.toMatch(/Math\.min\([^)]*5000/);
  });

  it('a null figure renders as text, not as a number', () => {
    for (const parts of files) {
      expect(readStripped(...parts)).toMatch(/'Not available'/);
    }
  });
});

describe('no module reintroduces a local latitude constant for area', () => {
  // lib/geometry/mercator.ts is the single source of truth and says so in its own
  // header. Three modules each carried `const NSW_LATITUDE = -33.87` before it
  // existed; the two setback components carried no correction at all.
  it.each([
    ['lib', 'geometry', 'calculator.ts'],
    ['components', 'analysis', 'PreciseSetbackCalculator.tsx'],
    ['components', 'analysis', 'EnhancedSetbackVerification.tsx'],
  ])('%s/%s/%s holds no latitude literal', (...parts) => {
    const src = readStripped(...parts);
    expect(src).not.toMatch(/-?33\.87/);
    expect(src).not.toMatch(/NSW_LATITUDE/);
  });

  it('calculator.ts has one shoelace, and it is the shared one', () => {
    const src = readStripped('lib', 'geometry', 'calculator.ts');
    expect(src).toMatch(/ringAreaM2\(/);
    // The duplicated loop is gone.
    expect(src).not.toMatch(/points\[i\]\.x\s*\*\s*points\[j\]\.y/);
  });
});

/**
 * PreciseSetbackCalculator.calculateBuildableArea must not report 0 as an area.
 *
 * Cross-review finding, 2026-10-06. The delegation added earlier that day kept
 * the old `?? 0`, which turned malformed or missing geometry into a plausible
 * numeric area that the three return paths then rounded and reported as
 * `total_lot_area`. Asserted on source because the class's constructor opens a
 * database client, which a unit test has no business doing.
 */
describe('the buildable-area calculator reports null, not 0, for an unmeasurable lot', () => {
  const src = readStripped('lib', 'geometry', 'calculator.ts');

  it('is read, so the assertions below are not vacuous', () => {
    expect(src.length).toBeGreaterThan(2000);
    expect(src).toContain('calculateBuildableArea');
  });

  it('no longer coalesces an unmeasurable ring to zero', () => {
    expect(src).not.toMatch(/ringAreaM2\([^)]*\)\s*\?\?\s*0/);
    expect(src).toMatch(/lotAreaFromGeometry\(geometry: LotGeometry\): number \| null/);
  });

  it('states no buildable figure as 0 beside a note saying it could not be calculated', () => {
    expect(src).not.toMatch(/buildable_area:\s*0/);
    expect(src).not.toMatch(/buildable_percentage:\s*0,/);
    expect(src).not.toMatch(/setback_area_lost:\s*0,/);
  });

  it('guards every figure derived from the lot area', () => {
    // Three return paths, each taking total_lot_area from the one guarded local.
    const guarded = (src.match(/total_lot_area:\s*lotArea/g) ?? []).length;
    expect(guarded).toBe(3);
    expect(src).toMatch(/totalArea != null \? this\.roundToCentimeter\(totalArea\) : null/);
  });
});
