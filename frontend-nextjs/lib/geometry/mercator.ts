/**
 * Web Mercator scale correction — the single source of truth for EPSG:3857 rings.
 *
 * WHY THIS FILE EXISTS. EPSG:3857 stretches distance by 1/cos(latitude), so an
 * area computed on raw Portal rings is wrong by 1/cos^2(latitude). Three modules
 * each carried their own copy of `const NSW_LATITUDE = -33.87`, which is exact in
 * Sydney and wrong everywhere else. Measured against the surveyed area on title
 * over 577,081 single-part cadastre lots (median computed/surveyed):
 *
 *     Sydney    -33..-35   1.0026        far north  -28..-30   0.9021
 *     mid north -30..-33   0.9708        south      -35..-37   1.0479
 *
 * A Tweed Heads lot read ~9.8% small, a Bega lot ~4.8% large. Lengths carry half
 * that (area scales with the square), and lot WIDTH gates minimum-frontage
 * eligibility — so the constant changed yes/no answers, not just displayed
 * numbers. The Bowral golden lot measured 4188.6 m2 against a surveyed 4117.7.
 *
 * The correct method was already running in production in
 * services/granny_flat.py::_compute_lot_area_m2 — it takes the latitude from the
 * ring's own northing. It never reached these modules because each had its own
 * copy of the constant, which is exactly the duplication this file removes.
 * Import from here; do not reintroduce a local latitude constant.
 */

/** Half the EPSG:3857 world extent, in metres. */
const MERCATOR_R = 20037508.342789244;

/**
 * NSW average latitude. Retained ONLY as the degenerate fallback for a ring
 * carrying no usable northing. It is not the correction any more.
 */
const NSW_LATITUDE_FALLBACK = -33.87;
const FALLBACK_SCALE = 1 / Math.cos((Math.abs(NSW_LATITUDE_FALLBACK) * Math.PI) / 180);

/**
 * A usable coordinate: a real finite number. `Number.isFinite` is what separates
 * NaN and Infinity from a number, and `typeof` alone does not.
 */
function isFiniteNumber(v: unknown): v is number {
  return typeof v === 'number' && Number.isFinite(v);
}

/**
 * The ring if every point is a finite [x, y], else null.
 *
 * A fallback scale factor does NOT make a malformed ring safe — it only stops
 * the divisor being NaN. The coordinates are still divided and still produce NaN
 * area and frontage, which then slip past `area <= 0` style checks because every
 * comparison with NaN is false. Callers must reject the ring instead, and return
 * their own unavailable result: measured in Python before this guard existed,
 * calculate_lot_dimensions returned a LotDimensions whose area was NaN.
 */
export function usableRing(ring: unknown): number[][] | null {
  if (!Array.isArray(ring) || ring.length === 0) return null;
  for (const pt of ring) {
    if (!Array.isArray(pt) || pt.length < 2) return null;
    if (!isFiniteNumber(pt[0]) || !isFiniteNumber(pt[1])) return null;
  }
  return ring as number[][];
}

/** Latitude in radians for an EPSG:3857 northing (inverse spherical Mercator). */
export function mercatorLatitude(y: number): number {
  return 2 * Math.atan(Math.exp((y * Math.PI) / MERCATOR_R)) - Math.PI / 2;
}

/**
 * Mercator scale factor at this ring's own latitude.
 *
 * A lot-sized polygon spans far too little latitude for the choice of point
 * within it to matter, so the ring centroid is used. Falls back to the NSW
 * average only when no usable northing is present — impossible for real Portal
 * geometry, but a malformed payload should degrade rather than throw.
 */
export function scaleFactorForRing(ring: number[][]): number {
  if (!ring || ring.length === 0) return FALLBACK_SCALE;
  const ys = ring
    .filter((c) => Array.isArray(c) && c.length >= 2 && isFiniteNumber(c[1]))
    .map((c) => c[1]);
  if (ys.length === 0) return FALLBACK_SCALE;
  const cosLat = Math.cos(mercatorLatitude(ys.reduce((a, b) => a + b, 0) / ys.length));
  if (!Number.isFinite(cosLat) || !(cosLat > 0)) return FALLBACK_SCALE;
  return 1 / cosLat;
}
