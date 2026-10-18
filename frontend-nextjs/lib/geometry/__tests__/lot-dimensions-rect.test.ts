/**
 * Frontage and depth come from the lot's minimum-area bounding rectangle, the
 * same method as services/lot_dimensions.py (#499).
 *
 * The bug this replaces: boundary classification took ONE segment per side. A
 * curved side is stored as many short straight pieces, so 6 Berrigan Street,
 * Winston Hills (Lot 23 DP217713, 688 m2) was served as 38.4 m x 3.9 m — a lot
 * 3.9 m deep cannot hold 688 m2 on a 38.4 m front. The Python service reads the
 * same ring as 22.4 m x 39.7 m. The first test fails on the old code.
 */
import { calculateLotDimensions } from '../lot-dimensions';
import type { LotGeometry } from '@/types/property';

/** Lot 23 DP217713, EPSG:3857, as served by /api/property on 2026-10-18. */
const BERRIGAN_ST_RING: number[][] = [
  [16808947.274, -3998985.339], [16808900.652, -3998974.959], [16808900.511, -3998976.959],
  [16808900.284, -3998978.952], [16808899.973, -3998980.932], [16808899.577, -3998982.898],
  [16808899.098, -3998984.845], [16808898.535, -3998986.769], [16808897.891, -3998988.667],
  [16808897.177, -3998990.547], [16808938.568, -3999011.032], [16808940.984, -3999004.055],
  [16808947.274, -3998985.339],
];

const EARTH_R = 6378137.0;
function mercatorY(latDeg: number): number {
  const lat = (latDeg * Math.PI) / 180;
  return EARTH_R * Math.log(Math.tan(Math.PI / 4 + lat / 2));
}

/** A polygon given in real metres, rotated, placed at a Sydney latitude. */
function ringFromMetres(pts: [number, number][], rotateDeg: number, latDeg = -33.8): LotGeometry {
  const k = 1 / Math.cos((Math.abs(latDeg) * Math.PI) / 180);
  const y0 = mercatorY(latDeg);
  const t = (rotateDeg * Math.PI) / 180;
  const ring = pts.map(([x, y]) => {
    const rx = x * Math.cos(t) - y * Math.sin(t);
    const ry = x * Math.sin(t) + y * Math.cos(t);
    return [16800000 + rx * k, y0 + ry * k];
  });
  ring.push(ring[0]);
  return { rings: [ring] } as LotGeometry;
}

describe('lot frontage and depth from the bounding rectangle', () => {
  it('reads the curved-side Winston Hills lot as the Python service does, not 3.9 m deep', () => {
    const d = calculateLotDimensions({ rings: [BERRIGAN_ST_RING] } as LotGeometry);
    expect(d).not.toBeNull();
    expect(d!.area).toBeGreaterThan(680);
    expect(d!.area).toBeLessThan(696);
    // services/lot_dimensions.py on the same ring: frontage_m=22.4 depth_m=39.7
    expect(d!.frontage).toBeCloseTo(22.4, 0);
    expect(d!.depth).toBeCloseTo(39.7, 0);
  });

  it('gives a rotated 15 x 40 m rectangle as 15 and 40 whatever the start vertex', () => {
    const corners: [number, number][] = [[0, 0], [15, 0], [15, 40], [0, 40]];
    for (const start of [0, 1, 2, 3]) {
      const order = [...corners.slice(start), ...corners.slice(0, start)];
      const d = calculateLotDimensions(ringFromMetres(order, 37));
      expect(d!.frontage).toBeCloseTo(15, 1);
      expect(d!.depth).toBeCloseTo(40, 1);
    }
  });

  it('does not depend on how finely a side is cut into pieces', () => {
    const plain: [number, number][] = [[0, 0], [20, 0], [20, 30], [0, 30]];
    const cut: [number, number][] = [[0, 0], [20, 0], ...Array.from({ length: 9 }, (_, i) => [20, 3 * (i + 1)] as [number, number]), [20, 30], [0, 30]];
    const a = calculateLotDimensions(ringFromMetres(plain, 12));
    const b = calculateLotDimensions(ringFromMetres(cut, 12));
    expect(b!.frontage).toBeCloseTo(a!.frontage as number, 1);
    expect(b!.depth).toBeCloseTo(a!.depth as number, 1);
  });

  it('returns null, not a number, for a lot too irregular for a rectangle (L-shape)', () => {
    // 1,100 m2 inside a convex hull of about 2,350 m2: under the 60% rule at any rotation.
    const lShape: [number, number][] = [[0, 0], [60, 0], [60, 10], [10, 10], [10, 60], [0, 60]];
    const d = calculateLotDimensions(ringFromMetres(lShape, 0));
    expect(d).not.toBeNull();
    expect(d!.frontage).toBeNull();
    expect(d!.depth).toBeNull();
    expect(d!.area).toBeGreaterThan(1000);
  });

  it('never reports a width larger than the shorter side, so a minimum-frontage test cannot pass on it wrongly', () => {
    // Wide, shallow lot: 30 m along the street, 15 m deep.
    const d = calculateLotDimensions(ringFromMetres([[0, 0], [30, 0], [30, 15], [0, 15]], 0));
    expect(d!.frontage).toBeCloseTo(15, 1);
    expect(d!.frontage as number).toBeLessThanOrEqual(30);
  });
});
