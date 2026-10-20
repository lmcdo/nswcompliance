import { decideFloodMap } from '@/lib/flood/flood-map';

const hornsby = ['Hornsby Local Environmental Plan 2013'];
const plans = new Set(hornsby);
const whole = (n: number | null) => ({ features: n, wholeLot: true });
const point = (n: number | null) => ({ features: n, wholeLot: false });

describe('decideFloodMap', () => {
  it('a flood polygon touching the lot -> yes (whole lot or point)', () => {
    expect(decideFloodMap(whole(1), hornsby, plans).floodProne).toBe(true);
    expect(decideFloodMap(point(1), hornsby, plans).floodProne).toBe(true);
  });
  it('whole lot tested, plan publishes a map, nothing touches it -> no', () => {
    const s = decideFloodMap(whole(0), hornsby, plans);
    expect(s.floodProne).toBe(false);
    expect(s.note).toMatch(/No part of this lot/);
  });
  it('only the centre point tested -> never "no" (Sol 2026-10-20: a partly flooded lot read No)', () => {
    const s = decideFloodMap(point(0), hornsby, plans);
    expect(s.floodProne).toBeNull();
    expect(s.note).toMatch(/whole lot could not be checked/);
  });
  it('council publishes no map -> cannot tell, with that reason', () => {
    const s = decideFloodMap(whole(0), ['Parramatta Local Environmental Plan 2023'], plans);
    expect(s.floodProne).toBeNull();
    expect(s.note).toMatch(/found no flood planning map on the NSW Planning Portal/);
  });
  it('each unknown says its own reason, not "no published map"', () => {
    expect(decideFloodMap(whole(null), hornsby, plans).note).toMatch(/couldn't reach the NSW flood planning map/);
    expect(decideFloodMap(whole(0), hornsby, null).note).toMatch(/couldn't check whether this council publishes/);
    expect(decideFloodMap(whole(0), [], plans).note).toMatch(/couldn't tell which local environmental plan/);
  });
});
