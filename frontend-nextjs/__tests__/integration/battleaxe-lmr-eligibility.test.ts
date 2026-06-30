/**
 * Integration test: battleaxe lot width must flow through LMR eligibility.
 *
 * Exercises the REAL chain wired in StateLevelControls — no mocks:
 *   battleaxeAwareLotWidth(lotDimensions)  ->  lmrFrontageStatus(lotWidth)
 *
 * Proves the unit fix actually changes the eligibility verdict end-to-end:
 * before the fix a battleaxe's handle frontage drove the LMR width test; now the
 * head width does. LMR minimums (lib/see/propertyUtils): dual occ 12m, manor 12m,
 * multi-dwelling 15m.
 */
import { battleaxeAwareLotWidth } from '@/lib/geometry/effective-lot-width';
import { lmrFrontageStatus } from '@/lib/see/propertyUtils';

describe('battleaxe lot width → LMR frontage eligibility (integration)', () => {
  it('a battleaxe with a sub-threshold handle but a wide head is ELIGIBLE on all LMR types', () => {
    // Handle 10m would fail every LMR minimum (12/12/15); head 30m passes all.
    const lotDimensions = {
      lotType: 'battleaxe' as const,
      frontage: 10,
      battleaxe: { isBattleaxe: true, mainLotWidth: 30, mainLotArea: 900 },
    };

    const lotWidth = battleaxeAwareLotWidth(lotDimensions);
    expect(lotWidth).toBe(30); // head, not the 10m handle

    const status = lmrFrontageStatus(lotWidth as number);
    expect(status.excluded).toHaveLength(0);
    expect(status.eligible.map((e) => e.devType).sort()).toEqual(
      ['dual_occupancy', 'manor_house', 'multi_dwelling'],
    );
  });

  it('REGRESSION GUARD: the old behaviour (handle width) would have excluded all three', () => {
    // Demonstrates the bug the fix closes: feeding the handle into the same test.
    const handleStatus = lmrFrontageStatus(10);
    expect(handleStatus.excluded).toHaveLength(3);
    expect(handleStatus.eligible).toHaveLength(0);
  });

  it('partial flip: head between thresholds includes the 12m types but still excludes 15m', () => {
    // Head 13m: passes dual occ + manor (12m), still fails multi-dwelling (15m).
    const lotDimensions = {
      lotType: 'battleaxe' as const,
      frontage: 8,
      battleaxe: { isBattleaxe: true, mainLotWidth: 13, mainLotArea: 260 },
    };
    const status = lmrFrontageStatus(battleaxeAwareLotWidth(lotDimensions) as number);
    expect(status.eligible.map((e) => e.devType).sort()).toEqual(['dual_occupancy', 'manor_house']);
    expect(status.excluded.map((e) => e.devType)).toEqual(['multi_dwelling']);
  });

  it('rectangular lot is unaffected — frontage drives the verdict as before', () => {
    const lotDimensions = { lotType: 'rectangular' as const, frontage: 14 };
    const lotWidth = battleaxeAwareLotWidth(lotDimensions);
    expect(lotWidth).toBe(14);
    const status = lmrFrontageStatus(lotWidth as number);
    // 14m: passes the 12m types, fails the 15m multi-dwelling
    expect(status.eligible.map((e) => e.devType).sort()).toEqual(['dual_occupancy', 'manor_house']);
    expect(status.excluded.map((e) => e.devType)).toEqual(['multi_dwelling']);
  });

  it("38 Park Rd Bowral case: no flip — both handle and head clear every minimum", () => {
    // Documents the honest limit: this property's verdict does NOT change
    // (handle 18.6m and head 70m both exceed 12/12/15). The fix matters for
    // battleaxes whose handle falls below a minimum, like the cases above.
    const lotDimensions = {
      lotType: 'battleaxe' as const,
      frontage: 18.6,
      battleaxe: { isBattleaxe: true, mainLotWidth: 70.09, mainLotArea: 4189 },
    };
    const headStatus = lmrFrontageStatus(battleaxeAwareLotWidth(lotDimensions) as number);
    const handleStatus = lmrFrontageStatus(18.6);
    expect(headStatus.excluded).toHaveLength(0);
    expect(handleStatus.excluded).toHaveLength(0); // same verdict here
  });
});
