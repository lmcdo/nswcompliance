/**
 * The Mercator correction must use each lot's OWN latitude, not a state average.
 *
 * EPSG:3857 stretches area by 1/cos^2(latitude). Every geometry module here used
 * to carry its own `const NSW_LATITUDE = -33.87`, which is exact in Sydney and
 * progressively wrong away from it. Measured against the surveyed area on title
 * over 577,081 single-part cadastre lots (median computed/surveyed):
 *
 *     far north -28..-30  0.9021        Sydney  -33..-35  1.0026
 *     mid north -30..-33  0.9708        south   -35..-37  1.0479
 *
 * Lengths carry half that error and lot width gates SEPP minimum-frontage rules,
 * so the constant changed yes/no answers rather than only displayed numbers.
 *
 * Every case below FAILS on the fixed-constant implementation at every latitude
 * except -33.87 — which is precisely the signature that says these tests measure
 * the projection rather than agreeing with whatever the code already does. The
 * previous suite could not fail: it built fixtures by multiplying by the module's
 * own scale factor and left them at (0, 0), the equator, so the constant
 * cancelled out.
 */
import { calculateLotDimensions } from '../lot-dimensions';
import { scaleFactorForRing, mercatorLatitude, usableRing } from '../mercator';
import type { LotGeometry } from '@/types/property';

const EARTH_R = 6378137.0;

/** Every NSW latitude band the served set spans, north to south. */
const NSW_LATITUDES = [-28.2, -30.3, -32.9, -33.87, -34.48, -36.7];

/** EPSG:3857 northing for a latitude — the forward projection. */
function mercatorY(latDeg: number): number {
  const lat = (latDeg * Math.PI) / 180;
  return EARTH_R * Math.log(Math.tan(Math.PI / 4 + lat / 2));
}

/** A rectangle of real-world metres, placed where it claims to be. */
function rectAt(widthM: number, depthM: number, latDeg: number): LotGeometry {
  const k = 1 / Math.cos((Math.abs(latDeg) * Math.PI) / 180);
  const y0 = mercatorY(latDeg);
  const pts: number[][] = [
    [0, y0],
    [widthM * k, y0],
    [widthM * k, y0 + depthM * k],
    [0, y0 + depthM * k],
    [0, y0],
  ];
  return { hasM: false, hasZ: false, rings: [pts], spatialReference: { wkid: 3857 } };
}

describe('Mercator correction uses the lot latitude', () => {
  it.each(NSW_LATITUDES)('a 600 m2 lot measures 600 m2 at latitude %s', (lat) => {
    const dims = calculateLotDimensions(rectAt(20, 30, lat));
    expect(dims).not.toBeNull();
    expect(dims!.area).toBeGreaterThan(600 * 0.995);
    expect(dims!.area).toBeLessThan(600 * 1.005);
  });

  it.each(NSW_LATITUDES)('frontage and depth survive latitude %s', (lat) => {
    const dims = calculateLotDimensions(rectAt(20, 30, lat));
    expect(dims!.frontage).toBeGreaterThan(20 * 0.995);
    expect(dims!.frontage).toBeLessThan(20 * 1.005);
    expect(dims!.depth).toBeGreaterThan(30 * 0.995);
    expect(dims!.depth).toBeLessThan(30 * 1.005);
  });

  it('a minimum-frontage decision does not depend on latitude', () => {
    // 15.7 m clears a 15 m minimum. Under the Sydney constant the same lot in
    // the far north measured ~14.9 m and failed the gate — a wrong answer, not
    // a wrong number.
    for (const lat of NSW_LATITUDES) {
      const dims = calculateLotDimensions(rectAt(15.7, 40, lat));
      expect(dims!.frontage).toBeGreaterThanOrEqual(15.0);
    }
  });
});

describe('scaleFactorForRing', () => {
  it('recovers the latitude the ring was built at', () => {
    for (const lat of NSW_LATITUDES) {
      const recovered = (mercatorLatitude(mercatorY(lat)) * 180) / Math.PI;
      expect(recovered).toBeCloseTo(lat, 6);
    }
  });

  it('matches the Python implementation on the Bowral ring', () => {
    // services.lot_dimensions._scale_factor_for_ring on the same ring returns
    // 1.213232964468 at latitude -34.488080084. Verified to 12 decimal places.
    const ring = [[16748000, mercatorY(-34.488080084)], [16748020, mercatorY(-34.488080084)]];
    expect(scaleFactorForRing(ring)).toBeCloseTo(1.213232964468, 9);
  });

  it('falls back instead of throwing on a malformed ring', () => {
    const FALLBACK = 1 / Math.cos((33.87 * Math.PI) / 180);
    expect(scaleFactorForRing([])).toBeCloseTo(FALLBACK, 12);
    expect(scaleFactorForRing([[NaN, NaN]])).toBeCloseTo(FALLBACK, 12);
  });
});


describe('malformed rings produce no measurement, never a NaN one', () => {
  // Raised by scripts/cross_review.py on the first push of this branch and
  // confirmed against the code: a fallback scale factor only stops the DIVISOR
  // being NaN. The coordinates were still divided, area came out NaN, and every
  // `> 0` guard passed because comparisons with NaN are false.
  const BAD: [string, unknown][] = [
    ['NaN northing', [[0, 0], [20, 0], [20, NaN], [0, 30], [0, 0]]],
    ['infinite easting', [[0, 0], [Infinity, 0], [20, 30], [0, 30], [0, 0]]],
    ['short tuple', [[0, 0], [20], [20, 30], [0, 30], [0, 0]]],
    ['non-numeric', [[0, 0], ['x', 'y'], [20, 30], [0, 30], [0, 0]]],
    ['empty', []],
  ];

  it.each(BAD)('usableRing rejects %s', (_label, ring) => {
    expect(usableRing(ring)).toBeNull();
  });

  it.each(BAD)('calculateLotDimensions returns null for %s', (_label, ring) => {
    const geom = {
      hasM: false, hasZ: false,
      rings: [ring], spatialReference: { wkid: 3857 },
    } as unknown as LotGeometry;
    const dims = calculateLotDimensions(geom);
    expect(dims).toBeNull();
  });

  it('a valid ring still measures, so the guard is not a kill switch', () => {
    const dims = calculateLotDimensions(rectAt(20, 30, -34.48));
    expect(dims).not.toBeNull();
    expect(dims!.area).toBeGreaterThan(600 * 0.995);
    expect(dims!.area).toBeLessThan(600 * 1.005);
  });
});
