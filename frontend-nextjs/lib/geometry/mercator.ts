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

/**
 * Ground area of an EPSG:3857 ring, in square metres — or null if not measurable.
 *
 * The scale correction above is the whole reason this function exists here rather
 * than at each call site. Two components carried their own shoelace with NO
 * correction at all (`EnhancedSetbackVerification.tsx` and
 * `PreciseSetbackCalculator.tsx`, both until 2026-10-06), so every lot area they
 * produced was high by 1/cos^2(latitude): a factor of 1.4514 at Petersham
 * (-33.8945), which reports a true 450 m2 lot as 653 m2. That figure then became
 * `lot_area` in the request body and `total_lot_area` on screen.
 *
 * Returns null, never 0, for a ring that cannot be measured. 0 is a legitimate
 * area for a degenerate polygon and reads downstream as a measurement; the
 * previous `return 0` was indistinguishable from "a lot with no size". A caller
 * that cannot get a number must omit the field, not substitute one.
 */
export function ringAreaM2(ring: unknown): number | null {
  const safe = usableRing(ring);
  if (safe == null || safe.length < 3) return null;

  // Drop a repeated closing point; the shoelace wraps on its own.
  const first = safe[0];
  const last = safe[safe.length - 1];
  const pts =
    safe.length > 3 && first[0] === last[0] && first[1] === last[1]
      ? safe.slice(0, -1)
      : safe;
  if (pts.length < 3) return null;

  // Taken from `pts`, not `safe`: averaging a duplicated closing point shifts the
  // centroid, which made a closed and an unclosed ring of the same polygon differ.
  const scale = scaleFactorForRing(pts);
  if (!Number.isFinite(scale) || !(scale > 0)) return null;

  let acc = 0;
  for (let i = 0; i < pts.length; i++) {
    const j = (i + 1) % pts.length;
    acc += pts[i][0] * pts[j][1] - pts[j][0] * pts[i][1];
  }
  const area = Math.abs(acc / 2) / (scale * scale);
  return Number.isFinite(area) ? area : null;
}

/**
 * Ground area of a Portal lot geometry, in square metres, or null.
 *
 * Only the outer ring is measured. A multi-ring geometry would need the inner
 * rings subtracted, and no caller here has one, so the honest answer for a ring
 * count above 1 is null rather than an outer-ring area presented as the lot.
 */
export function lotGeometryAreaM2(geometry: unknown): number | null {
  if (geometry == null || typeof geometry !== 'object') return null;
  const rings = (geometry as { rings?: unknown }).rings;
  if (!Array.isArray(rings) || rings.length !== 1) return null;
  return ringAreaM2(rings[0]);
}
