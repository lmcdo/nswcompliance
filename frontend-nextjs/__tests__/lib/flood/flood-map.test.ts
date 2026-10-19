import { decideFloodMap } from '@/lib/flood/flood-map';

const plans = new Set(['Hornsby Local Environmental Plan 2013']);

describe('decideFloodMap', () => {
  it('on the map -> yes', () => {
    expect(decideFloodMap(1, ['Hornsby Local Environmental Plan 2013'], plans).floodProne).toBe(true);
  });
  it("council publishes a map and the lot is not on it -> no", () => {
    expect(decideFloodMap(0, ['Hornsby Local Environmental Plan 2013'], plans).floodProne).toBe(false);
  });
  it('council publishes no map -> cannot tell, never "no" (Parramatta, 2026-10-19)', () => {
    const s = decideFloodMap(0, ['Parramatta Local Environmental Plan 2023'], plans);
    expect(s.floodProne).toBeNull();
    expect(s.note).toMatch(/has not published a flood planning map/);
  });
  it('map unreachable -> cannot tell', () => {
    expect(decideFloodMap(null, ['Hornsby Local Environmental Plan 2013'], plans).floodProne).toBeNull();
    expect(decideFloodMap(0, ['Hornsby Local Environmental Plan 2013'], null).floodProne).toBeNull();
  });
});
