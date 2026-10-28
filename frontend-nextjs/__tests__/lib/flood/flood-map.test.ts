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

import { boundaryMatchesPoint } from '@/lib/flood/flood-map';

describe('boundaryMatchesPoint', () => {
  // 3 Egret Way, Mount Annan: Portal lot ring (EPSG:3857) and its address point
  const ring = [[16781724.2, -4036617.0], [16781764.5, -4036609.5], [16781767.2, -4036597.3],
    [16781729.8, -4036596.6], [16781724.2, -4036617.0]];
  it('the lot boundary around its own address point is trusted', () => {
    expect(boundaryMatchesPoint([ring], 3857, 150.75298, -34.05807)).toBe(true);
  });
  it('a boundary mislabelled or from another lot is not trusted for a "No"', () => {
    expect(boundaryMatchesPoint([ring], 3857, 151.1047, -33.854)).toBe(false); // Concord
    expect(boundaryMatchesPoint([ring], 4326, 150.75298, -34.05807)).toBe(false); // wrong label
    expect(boundaryMatchesPoint([ring], 2056, 150.75298, -34.05807)).toBe(false); // unknown system
  });
});

describe('floodMapStatus over a mocked map service', () => {
  const ring = [[16781724.2, -4036617.0], [16781764.5, -4036609.5], [16781767.2, -4036597.3],
    [16781729.8, -4036596.6], [16781724.2, -4036617.0]];
  const boundary = { rings: [ring], spatialReference: { wkid: 3857 } };
  const plan = ['Camden Local Environmental Plan 2010'];
  const reply = (body: unknown) => Promise.resolve({ json: () => Promise.resolve(body) });
  afterEach(() => { (global as any).fetch = undefined; });

  function mock(point: unknown, lot: unknown) {
    (global as any).fetch = jest.fn((url: string, init?: { method?: string }) => {
      if (url.includes('returnDistinctValues')) return reply({ features: [{ attributes: { EPI_NAME: plan[0] } }] });
      if (init?.method === 'POST') return lot instanceof Error ? Promise.reject(lot) : reply(lot);
      return point instanceof Error ? Promise.reject(point) : reply(point);
    });
  }

  it('point query failed, boundary clear -> cannot tell (Sol 2026-10-20)', async () => {
    jest.resetModules();
    const { floodMapStatus } = await import('@/lib/flood/flood-map');
    mock(new Error('timeout'), { features: [] });
    expect((await floodMapStatus(150.75298, -34.05807, plan, boundary)).floodProne).toBeNull();
  });

  it('point and whole lot both clear -> no', async () => {
    jest.resetModules();
    const { floodMapStatus } = await import('@/lib/flood/flood-map');
    mock({ features: [] }, { features: [] });
    expect((await floodMapStatus(150.75298, -34.05807, plan, boundary)).floodProne).toBe(false);
  });

  it('boundary clear but the address point is flooded -> yes', async () => {
    jest.resetModules();
    const { floodMapStatus } = await import('@/lib/flood/flood-map');
    mock({ features: [{}] }, { features: [] });
    expect((await floodMapStatus(150.75298, -34.05807, plan, boundary)).floodProne).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// combineFloodAnswers — state layer 230 + our council map store (2026-10-28)
// ---------------------------------------------------------------------------
import { combineFloodAnswers } from '@/lib/flood/flood-map';

describe('combineFloodAnswers', () => {
  const unknownState = { floodProne: null, note: 'No published map.' };

  it('a store yes turns an unknown state answer into yes (the 47 addresses layer 230 missed)', () => {
    expect(combineFloodAnswers(unknownState, { value: true }).floodProne).toBe(true);
  });

  it('a whole-lot state no stands even when the store cannot say', () => {
    const no = { floodProne: false, note: 'No part of this lot…' };
    expect(combineFloodAnswers(no, { value: null, reason: 'x' })).toEqual(no);
  });

  it('a state yes is never overturned by a store no', () => {
    expect(combineFloodAnswers({ floodProne: true, note: 'on' }, { value: false }).floodProne).toBe(true);
  });

  it('a store no (point only) never makes a No on this page: stays not known, explained', () => {
    const got = combineFloodAnswers(unknownState, { value: false });
    expect(got.floodProne).toBeNull();
    expect(got.note).toMatch(/address point/);
    expect(got.note).toMatch(/whole lot was not checked/);
  });

  it('neither can say: still unknown, with our reason added, never false', () => {
    const got = combineFloodAnswers(unknownState, { value: null, reason: "we do not hold this council's flood planning map" });
    expect(got.floodProne).toBeNull();
    expect(got.note).toMatch(/do not hold/);
  });

  it('a backend failure leaves the state answer untouched', () => {
    const failed = { floodProne: null, note: 'unreachable', mapDidNotAnswer: true as const };
    expect(combineFloodAnswers(failed, null)).toEqual(failed);
  });
});
