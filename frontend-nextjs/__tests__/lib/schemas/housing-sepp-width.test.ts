import { HousingSEPPSchema } from '@/lib/schemas';

const base = { zoneCode: 'R2', lotSize: 600 }; // noqa: zone-codes

describe('HousingSEPPSchema lot width', () => {
  it.each([
    [{ lotWidth: 15 }, true],
    [{ lotWidthMin: 12, lotWidthMax: 18 }, true],
    [{ lotWidth: 15, lotWidthMin: 12, lotWidthMax: 18 }, true],
    // Sol on #1347: half a range, or min above max, was accepted next to lotWidth
    [{ lotWidth: 15, lotWidthMin: 20, lotWidthMax: 5 }, false],
    [{ lotWidth: 15, lotWidthMin: 20 }, false],
    [{ lotWidthMax: 18 }, false],
    [{}, false],
  ])('%o -> valid %s', (widths, ok) => {
    expect(HousingSEPPSchema.safeParse({ ...base, ...widths }).success).toBe(ok);
  });
});
