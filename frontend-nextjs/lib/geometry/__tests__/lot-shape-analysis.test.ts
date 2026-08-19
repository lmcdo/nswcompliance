/**
 * Tests for battleaxe lot detection algorithm
 *
 * Run with: npx jest lib/geometry/__tests__/lot-shape-analysis.test.ts
 */

import { detectBattleaxeLot, analyzeLotShape } from '../lot-shape-analysis';
import type { LotGeometry } from '@/types/property';

const EARTH_R = 6378137.0;

/** EPSG:3857 northing for a latitude — the forward projection. */
function mercatorY(latDeg: number): number {
  const lat = (latDeg * Math.PI) / 180;
  return EARTH_R * Math.log(Math.tan(Math.PI / 4 + lat / 2));
}

/**
 * Build LotGeometry from real-world metre coordinates, placed AT A REAL LATITUDE.
 *
 * The previous helper declared its own `NSW_LATITUDE = -33.87`, scaled by it, and
 * left the ring at (0, 0) — which is the equator. That made every area assertion
 * circular: the constant used to build the fixture was the same constant the code
 * used to read it, so it cancelled and the tests passed for ANY latitude,
 * including a wrong one. The module under test now takes the latitude from the
 * ring's own northing, so the fixture has to put the ring where it claims to be.
 *
 * Defaults to Sydney so existing expectations keep their meaning; pass a latitude
 * to prove the correction holds across the state.
 */
function createGeometry(coords: [number, number][], latDeg = -33.87): LotGeometry {
  const k = 1 / Math.cos((Math.abs(latDeg) * Math.PI) / 180);
  const y0 = mercatorY(latDeg);
  const scaledCoords = coords.map(([x, y]) => [x * k, y0 + y * k]);
  // Close the polygon
  scaledCoords.push(scaledCoords[0]);

  return {
    hasM: false,
    hasZ: false,
    rings: [scaledCoords],
    spatialReference: { wkid: 3857 }
  };
}

describe('detectBattleaxeLot', () => {
  describe('Standard battleaxe lots', () => {
    it('detects classic battleaxe: 3.5m handle, 15m long, 12m×18m head', () => {
      // Classic battleaxe shape:
      //     ┌──────────────┐
      //     │              │  <- Head (12m × 18m)
      //     │              │
      //     └──┬────────┬──┘
      //        │        │     <- Handle (3.5m × 15m)
      //        │        │
      //        └────────┘

      const coords: [number, number][] = [
        [0, 0],           // Bottom left of handle
        [3.5, 0],         // Bottom right of handle
        [3.5, 15],        // Where handle meets head (right)
        [12, 15],         // Head bottom right
        [12, 33],         // Head top right (15 + 18 = 33)
        [0, 33],          // Head top left
        [0, 15],          // Where handle meets head (left)
        [0, 0],           // Close (will be deduplicated)
      ];

      // Adjust to center the head
      const centeredCoords: [number, number][] = [
        [4.25, 0],        // Handle bottom left
        [7.75, 0],        // Handle bottom right (3.5m wide)
        [7.75, 15],       // Handle top right
        [12, 15],         // Head bottom right
        [12, 33],         // Head top right
        [0, 33],          // Head top left
        [0, 15],          // Head bottom left
        [4.25, 15],       // Back to handle
      ];

      const geometry = createGeometry(centeredCoords);
      const result = detectBattleaxeLot(geometry);

      console.log('Classic battleaxe result:', JSON.stringify(result, null, 2));

      expect(result.isBattleaxe).toBe(true);
      expect(result.accessWayWidth).toBeLessThan(6);
      expect(result.mainLotWidth).toBeGreaterThan(9);
      expect(result.meetsMinimumRequirements).toBe(true);
      expect(result.confidence).toBeGreaterThan(0.6);
    });

    it('detects narrow battleaxe: 3m handle, 25m long', () => {
      // Very narrow, long handle
      const coords: [number, number][] = [
        [5, 0],
        [8, 0],           // 3m wide handle
        [8, 25],          // 25m long handle
        [15, 25],
        [15, 40],         // 15m deep head
        [0, 40],
        [0, 25],
        [5, 25],
      ];

      const geometry = createGeometry(coords);
      const result = detectBattleaxeLot(geometry);

      console.log('Narrow battleaxe result:', JSON.stringify(result, null, 2));

      expect(result.isBattleaxe).toBe(true);
      expect(result.accessWayWidth).toBeLessThanOrEqual(3.5);
    });

    it('detects non-compliant battleaxe: 2.5m handle (below 3m minimum)', () => {
      const coords: [number, number][] = [
        [5, 0],
        [7.5, 0],         // Only 2.5m wide - below minimum
        [7.5, 15],
        [12, 15],
        [12, 30],
        [0, 30],
        [0, 15],
        [5, 15],
      ];

      const geometry = createGeometry(coords);
      const result = detectBattleaxeLot(geometry);

      console.log('Non-compliant battleaxe result:', JSON.stringify(result, null, 2));

      expect(result.isBattleaxe).toBe(true);
      expect(result.meetsMinimumRequirements).toBe(false);
      expect(result.complianceIssues.length).toBeGreaterThan(0);
      expect(result.complianceIssues.some(i => i.includes('Access way width'))).toBe(true);
    });
  });

  describe('Wide-handle (rural) battleaxe — regression for handle-length/area bug', () => {
    // A large rural battleaxe: 16m-wide handle (wider than the old fixed 9m
    // MIN_HEAD_WIDTH threshold) feeding a 50m-wide head. Previously the handle
    // length collapsed to 0 and the "main lot" area was computed over the full
    // lot length, producing a main-lot area LARGER than the whole lot.
    const coords: [number, number][] = [
      [17, 0],   // handle bottom-left
      [33, 0],   // handle bottom-right (16m wide)
      [33, 30],  // handle meets head (right) — 30m long handle
      [50, 30],  // head bottom-right
      [50, 70],  // head top-right (40m deep)
      [0, 70],   // head top-left
      [0, 30],   // head bottom-left (50m wide)
      [17, 30],  // back to handle
    ];
    // Total lot area via shoelace on the raw coords = 2480 m²
    const TOTAL_AREA = 2480;

    it('detects the wide handle as a battleaxe', () => {
      const result = detectBattleaxeLot(createGeometry(coords));
      expect(result.isBattleaxe).toBe(true);
      // Handle is genuinely wide — the exact scenario the old 9m threshold broke on
      expect(result.accessWayWidth).toBeGreaterThan(9);
    });

    it('reports a non-zero access-way length (was 0 before the fix)', () => {
      const result = detectBattleaxeLot(createGeometry(coords));
      expect(result.accessWayLength).toBeGreaterThan(0);
    });

    it('reports a main-lot area smaller than the whole lot (was inflated before)', () => {
      const result = detectBattleaxeLot(createGeometry(coords));
      expect(result.mainLotArea).toBeGreaterThan(0);
      expect(result.mainLotArea).toBeLessThan(TOTAL_AREA);
    });
  });

  describe('Non-battleaxe lots (should NOT detect)', () => {
    it('rejects standard rectangular lot: 12m × 40m', () => {
      const coords: [number, number][] = [
        [0, 0],
        [12, 0],
        [12, 40],
        [0, 40],
      ];

      const geometry = createGeometry(coords);
      const result = detectBattleaxeLot(geometry);

      console.log('Rectangular lot result:', JSON.stringify(result, null, 2));

      expect(result.isBattleaxe).toBe(false);
    });

    it('rejects wide lot: 15m × 30m', () => {
      const coords: [number, number][] = [
        [0, 0],
        [15, 0],
        [15, 30],
        [0, 30],
      ];

      const geometry = createGeometry(coords);
      const result = detectBattleaxeLot(geometry);

      console.log('Wide lot result:', JSON.stringify(result, null, 2));

      expect(result.isBattleaxe).toBe(false);
    });

    it('rejects square lot: 20m × 20m', () => {
      const coords: [number, number][] = [
        [0, 0],
        [20, 0],
        [20, 20],
        [0, 20],
      ];

      const geometry = createGeometry(coords);
      const result = detectBattleaxeLot(geometry);

      expect(result.isBattleaxe).toBe(false);
    });

    it('rejects lot with wide "handle" (6.5m) - not narrow enough', () => {
      // This has a narrow section but it's too wide to be a battleaxe handle
      const coords: [number, number][] = [
        [3, 0],
        [9.5, 0],         // 6.5m - at the threshold
        [9.5, 15],
        [15, 15],
        [15, 35],
        [0, 35],
        [0, 15],
        [3, 15],
      ];

      const geometry = createGeometry(coords);
      const result = detectBattleaxeLot(geometry);

      console.log('Wide handle result:', JSON.stringify(result, null, 2));

      // May or may not detect depending on exact thresholds
      // The key is it should have lower confidence if detected
      if (result.isBattleaxe) {
        expect(result.confidence).toBeLessThan(0.8);
      }
    });
  });

  describe('Edge cases', () => {
    it('handles rotated battleaxe (handle at angle)', () => {
      // 45-degree rotated battleaxe - should still detect based on width profile
      const cos45 = Math.cos(Math.PI / 4);
      const sin45 = Math.sin(Math.PI / 4);

      // Simple L-shape rotated
      const coords: [number, number][] = [
        [0, 0],
        [3 * cos45, 3 * sin45],
        [3 * cos45 + 15 * sin45, 3 * sin45 - 15 * cos45],
        [3 * cos45 + 15 * sin45 + 12 * cos45, 3 * sin45 - 15 * cos45 + 12 * sin45],
        [15 * sin45 + 12 * cos45, -15 * cos45 + 12 * sin45],
        [15 * sin45, -15 * cos45],
      ];

      const geometry = createGeometry(coords);
      const result = detectBattleaxeLot(geometry);

      console.log('Rotated battleaxe result:', JSON.stringify(result, null, 2));

      // Rotated detection is harder - may or may not detect
      // Just ensure it doesn't crash
      expect(result).toBeDefined();
    });

    it('handles very small lot (should not crash)', () => {
      const coords: [number, number][] = [
        [0, 0],
        [5, 0],
        [5, 5],
        [0, 5],
      ];

      const geometry = createGeometry(coords);
      const result = detectBattleaxeLot(geometry);

      expect(result.isBattleaxe).toBe(false);
    });

    it('handles L-shaped lot (similar to battleaxe)', () => {
      // L-shape but with equal width throughout - not battleaxe
      const coords: [number, number][] = [
        [0, 0],
        [10, 0],
        [10, 20],
        [20, 20],
        [20, 30],
        [0, 30],
      ];

      const geometry = createGeometry(coords);
      const result = detectBattleaxeLot(geometry);

      console.log('L-shaped lot result:', JSON.stringify(result, null, 2));

      // L-shape with equal widths is NOT a battleaxe
      // Width profile would show 10m everywhere
      expect(result.isBattleaxe).toBe(false);
    });

    it('handles empty/invalid geometry gracefully', () => {
      const emptyGeometry: LotGeometry = {
        hasM: false,
        hasZ: false,
        rings: [],
        spatialReference: { wkid: 3857 }
      };

      const result = detectBattleaxeLot(emptyGeometry);

      expect(result.isBattleaxe).toBe(false);
      expect(result.confidence).toBe(0);
    });

    it('handles geometry with too few points', () => {
      const geometry = createGeometry([
        [0, 0],
        [10, 0],
        [5, 10],
      ]);

      const result = detectBattleaxeLot(geometry);

      expect(result.isBattleaxe).toBe(false);
    });
  });

  describe('analyzeLotShape', () => {
    it('classifies rectangular lot correctly', () => {
      const coords: [number, number][] = [
        [0, 0],
        [12, 0],
        [12, 40],
        [0, 40],
      ];

      const geometry = createGeometry(coords);
      const result = analyzeLotShape(geometry);

      expect(result.lotType).toBe('rectangular');
      expect(result.battleaxe).toBeUndefined();
    });

    it('classifies battleaxe lot correctly', () => {
      const coords: [number, number][] = [
        [4, 0],
        [8, 0],
        [8, 15],
        [14, 15],
        [14, 33],
        [0, 33],
        [0, 15],
        [4, 15],
      ];

      const geometry = createGeometry(coords);
      const result = analyzeLotShape(geometry);

      console.log('analyzeLotShape battleaxe result:', JSON.stringify(result, null, 2));

      expect(result.lotType).toBe('battleaxe');
      expect(result.battleaxe).toBeDefined();
      expect(result.battleaxe?.isBattleaxe).toBe(true);
    });

    it('classifies irregular lot (many sides) correctly', () => {
      // Hexagonal lot
      const coords: [number, number][] = [
        [5, 0],
        [15, 0],
        [20, 10],
        [15, 20],
        [5, 20],
        [0, 10],
      ];

      const geometry = createGeometry(coords);
      const result = analyzeLotShape(geometry);

      // Should be irregular since it's not battleaxe and not 4-sided
      expect(['irregular', 'rectangular']).toContain(result.lotType);
    });
  });
});

describe('Width profile measurements', () => {
  it('correctly measures width at different positions', () => {
    // Create a battleaxe and check the width profile
    const coords: [number, number][] = [
      [4, 0],
      [8, 0],           // 4m wide handle
      [8, 20],          // 20m long handle
      [15, 20],         // Transition
      [15, 40],         // 15m wide head
      [0, 40],
      [0, 20],
      [4, 20],
    ];

    const geometry = createGeometry(coords);
    const result = detectBattleaxeLot(geometry);

    console.log('Width profile:', result.widthProfile);

    expect(result.widthProfile).toBeDefined();
    expect(result.widthProfile!.length).toBe(20);

    // Early slices should be narrow (handle)
    const handleWidths = result.widthProfile!.slice(0, 8);
    const headWidths = result.widthProfile!.slice(12);

    const avgHandleWidth = handleWidths.reduce((a, b) => a + b, 0) / handleWidths.length;
    const avgHeadWidth = headWidths.reduce((a, b) => a + b, 0) / headWidths.length;

    console.log('Avg handle width:', avgHandleWidth);
    console.log('Avg head width:', avgHeadWidth);

    // Handle should be narrower than head
    expect(avgHandleWidth).toBeLessThan(avgHeadWidth);
  });
});
