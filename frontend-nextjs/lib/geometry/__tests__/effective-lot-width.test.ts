import {
  battleaxeAwareLotWidth,
  battleaxeAwareLotDepth,
  firstMeasuredWidth,
  positiveFiniteOrNull,
} from '../effective-lot-width';

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

/**
 * Added 2026-10-06 over two cross-review rounds, both about the same thing: a
 * value that is a `number` but not a measurement.
 */
describe('positiveFiniteOrNull', () => {
  it.each<[string, unknown]>([
    ['zero', 0],
    ['negative zero', -0],
    ['a negative', -3],
    ['NaN', NaN],
    ['Infinity', Infinity],
    ['-Infinity', -Infinity],
    ['a numeric string', '12'],
    ['null', null],
    ['undefined', undefined],
    ['an object', {}],
  ])('%s is not a measurement', (_label, value) => {
    expect(positiveFiniteOrNull(value)).toBeNull();
  });

  it.each([0.1, 11.4, 12, 15, 70.09])('%s is a measurement and is returned unchanged', (v) => {
    expect(positiveFiniteOrNull(v)).toBe(v);
  });
});

describe('firstMeasuredWidth normalises each candidate before comparing', () => {
  it('skips an invalid earlier candidate and uses a valid later one', () => {
    // THE BUG this function exists for. `??` falls through only on null and
    // undefined, so a NaN or 0 first candidate won the coalesce; normalising the
    // finished chain then turned that winner into null and threw away the 13.
    expect(firstMeasuredWidth(NaN, 13)).toBe(13);
    expect(firstMeasuredWidth(0, 13)).toBe(13);
    expect(firstMeasuredWidth(-5, 13)).toBe(13);
    expect(firstMeasuredWidth(Infinity, 13)).toBe(13);
  });

  it('prefers the earliest candidate that is a real measurement', () => {
    expect(firstMeasuredWidth(12.5, 13, 14)).toBe(12.5);
    expect(firstMeasuredWidth(null, undefined, 14, 15)).toBe(14);
  });

  it('is null when no candidate is a measurement', () => {
    expect(firstMeasuredWidth()).toBeNull();
    expect(firstMeasuredWidth(null, undefined)).toBeNull();
    expect(firstMeasuredWidth(0, NaN, -1, Infinity)).toBeNull();
  });

  it('never returns 15 unless 15 was actually supplied', () => {
    // The deleted DEFAULT_LOT_WIDTH_M cleared all three LMR minimums.
    expect(firstMeasuredWidth(NaN, 0, null)).not.toBe(15);
    expect(firstMeasuredWidth(15)).toBe(15);
  });
});

describe('a NaN or 0 frontage no longer escapes battleaxeAwareLotWidth', () => {
  it.each<[string, unknown]>([
    ['NaN', NaN],
    ['zero', 0],
    ['a negative', -4],
    ['Infinity', Infinity],
  ])('%s frontage yields null, not a number', (_label, frontage) => {
    expect(
      battleaxeAwareLotWidth({ lotType: 'rectangular', frontage } as never),
    ).toBeNull();
  });

  it('falls back to the frontage when a battleaxe head width is NaN', () => {
    expect(
      battleaxeAwareLotWidth({
        lotType: 'battleaxe',
        frontage: 18.6,
        battleaxe: { mainLotWidth: NaN },
      } as never),
    ).toBe(18.6);
  });

  it.each<[string, unknown]>([
    ['NaN', NaN],
    ['zero', 0],
    ['a negative', -4],
  ])('%s depth yields null, not a number', (_label, depth) => {
    expect(battleaxeAwareLotDepth({ lotType: 'rectangular', depth } as never)).toBeNull();
  });
});
