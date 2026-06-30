import { battleaxeAwareLotWidth, battleaxeAwareLotDepth } from '../effective-lot-width';

describe('battleaxeAwareLotWidth', () => {
  describe('battleaxe lots — must use the HEAD width, not the handle frontage', () => {
    it('returns the head width (the bug: 18.6m handle was used for eligibility)', () => {
      // 38 Park Rd Bowral: frontage is the ~18.6m handle, head is ~70m
      const ld = {
        lotType: 'battleaxe' as const,
        frontage: 18.6,
        battleaxe: { isBattleaxe: true, mainLotWidth: 70.09 },
      };
      expect(battleaxeAwareLotWidth(ld)).toBe(70.09);
    });

    it('falls back to frontage when head width is missing', () => {
      const ld = {
        lotType: 'battleaxe' as const,
        frontage: 18.6,
        battleaxe: { isBattleaxe: true, mainLotWidth: null },
      };
      expect(battleaxeAwareLotWidth(ld)).toBe(18.6);
    });

    it('falls back to frontage when head width is zero or negative (bad data)', () => {
      expect(
        battleaxeAwareLotWidth({ lotType: 'battleaxe', frontage: 15, battleaxe: { mainLotWidth: 0 } }),
      ).toBe(15);
      expect(
        battleaxeAwareLotWidth({ lotType: 'battleaxe', frontage: 15, battleaxe: { mainLotWidth: -3 } }),
      ).toBe(15);
    });

    it('returns null when battleaxe has neither head width nor frontage', () => {
      expect(
        battleaxeAwareLotWidth({ lotType: 'battleaxe', frontage: null, battleaxe: { mainLotWidth: null } }),
      ).toBeNull();
    });

    it('ignores a missing battleaxe object, using frontage', () => {
      expect(battleaxeAwareLotWidth({ lotType: 'battleaxe', frontage: 12, battleaxe: null })).toBe(12);
    });
  });

  describe('non-battleaxe lots — must use frontage unchanged', () => {
    it('rectangular lot returns frontage', () => {
      expect(battleaxeAwareLotWidth({ lotType: 'rectangular', frontage: 12.5 })).toBe(12.5);
    });

    it('irregular lot returns frontage', () => {
      expect(battleaxeAwareLotWidth({ lotType: 'irregular', frontage: 15 })).toBe(15);
    });

    it('does NOT use mainLotWidth for a non-battleaxe lot even if present', () => {
      // Guards against over-eager substitution on a rectangular lot
      const ld = { lotType: 'rectangular' as const, frontage: 12, battleaxe: { mainLotWidth: 99 } };
      expect(battleaxeAwareLotWidth(ld)).toBe(12);
    });
  });

  describe('missing / malformed input', () => {
    it('returns null for null/undefined input', () => {
      expect(battleaxeAwareLotWidth(null)).toBeNull();
      expect(battleaxeAwareLotWidth(undefined)).toBeNull();
    });

    it('returns null when frontage is absent on a non-battleaxe lot', () => {
      expect(battleaxeAwareLotWidth({ lotType: 'rectangular' })).toBeNull();
    });

    it('returns null when frontage is non-numeric', () => {
      // @ts-expect-error — guarding against bad runtime data
      expect(battleaxeAwareLotWidth({ lotType: 'rectangular', frontage: '12' })).toBeNull();
    });
  });
});

describe('battleaxeAwareLotDepth', () => {
  describe('battleaxe lots — head depth = head area / head width, not the L-shape depth', () => {
    it('derives head depth from area and width (not the 32.4m heuristic depth)', () => {
      const ld = {
        lotType: 'battleaxe' as const,
        depth: 32.4,
        battleaxe: { isBattleaxe: true, mainLotWidth: 70, mainLotArea: 3500 },
      };
      expect(battleaxeAwareLotDepth(ld)).toBeCloseTo(50, 5); // 3500 / 70
    });

    it('falls back to raw depth when head area is missing', () => {
      const ld = {
        lotType: 'battleaxe' as const,
        depth: 32.4,
        battleaxe: { isBattleaxe: true, mainLotWidth: 70, mainLotArea: null },
      };
      expect(battleaxeAwareLotDepth(ld)).toBe(32.4);
    });

    it('falls back to raw depth when head width is zero (no divide-by-zero)', () => {
      const ld = {
        lotType: 'battleaxe' as const,
        depth: 30,
        battleaxe: { mainLotWidth: 0, mainLotArea: 1000 },
      };
      expect(battleaxeAwareLotDepth(ld)).toBe(30);
    });
  });

  describe('non-battleaxe and malformed', () => {
    it('rectangular lot returns raw depth', () => {
      expect(battleaxeAwareLotDepth({ lotType: 'rectangular', depth: 40 })).toBe(40);
    });

    it('does NOT derive for a non-battleaxe lot even with head area present', () => {
      const ld = { lotType: 'rectangular' as const, depth: 40, battleaxe: { mainLotWidth: 70, mainLotArea: 3500 } };
      expect(battleaxeAwareLotDepth(ld)).toBe(40);
    });

    it('returns null for null input or non-numeric depth', () => {
      expect(battleaxeAwareLotDepth(null)).toBeNull();
      // @ts-expect-error — bad runtime data
      expect(battleaxeAwareLotDepth({ lotType: 'rectangular', depth: '40' })).toBeNull();
    });
  });
});
