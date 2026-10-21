/**
 * Ku-ring-gai Part 20: the lot adjoins a busy road corridor or the LEP SP2 railway land.
 * prior-art-checked: new gate (lib/rail-busy-road.ts), no existing test covers it.
 * Map answers below are what the live services returned on 2026-10-21 for these real lots.
 * @jest-environment node
 */
import {
  railOrBusyRoadForPoint,
  railOrBusyRoadConstraints,
  RAIL_ROAD_LOT_SQL,
  ROAD_WHERE,
  RAIL_WHERE,
  TOLERANCE_M,
  type FetchFn,
} from '@/lib/rail-busy-road';

const LOT = JSON.stringify({ type: 'Polygon', coordinates: [[[151.1, -33.7], [151.1001, -33.7], [151.1001, -33.7001], [151.1, -33.7]]] });

function fakeQuery(lotGeojson: string | null) {
  return jest.fn(async (sql: string) => {
    if (sql !== RAIL_ROAD_LOT_SQL) throw new Error('unexpected sql');
    return { rows: [{ lot_geojson: lotGeojson }] };
  });
}

function fakeFetch(road: unknown[], rail: unknown[], opts: { fail?: boolean } = {}) {
  const bodies: URLSearchParams[] = [];
  const fn: FetchFn = jest.fn(async (url: string, init) => {
    bodies.push(init.body);
    if (opts.fail) return { ok: false, status: 504, json: async () => ({}) };
    const features = url.includes('MapServer/2') ? rail : road;
    return { ok: true, status: 200, json: async () => ({ features: features.map((attributes) => ({ attributes })) }) };
  });
  return { fn, bodies };
}

describe('railOrBusyRoadForPoint', () => {
  it('1311 Pacific Highway Turramurra (lot C//DP397027): adjoins the Pacific Highway', async () => {
    const f = fakeFetch([{ roadnamelabel: 'PACIFIC HWY' }], []);
    await expect(railOrBusyRoadForPoint(fakeQuery(LOT), f.fn, 151.1277007, -33.7332054)).resolves.toEqual({
      adjoins: true,
      roads: ['Pacific Highway'],
      rail: false,
    });
    // Both queries ask for features within the tolerance of the lot, with the data file's filters.
    expect(f.bodies.map((b) => b.get('where')).sort()).toEqual([RAIL_WHERE, ROAD_WHERE].sort());
    for (const b of f.bodies) {
      expect(b.get('distance')).toBe(String(TOLERANCE_M));
      expect(b.get('units')).toBe('esriSRUnit_Meter');
      expect(JSON.parse(b.get('geometry')!).rings).toEqual(JSON.parse(LOT).coordinates);
    }
  });

  it('33 Killara Avenue Killara (lot 10//DP666517): backs onto the North Shore line', async () => {
    const f = fakeFetch([], [{ PURPOSE: 'Railway Infrastructure' }]);
    await expect(railOrBusyRoadForPoint(fakeQuery(LOT), f.fn, 151.1644482, -33.7697379)).resolves.toEqual({
      adjoins: true,
      roads: [],
      rail: true,
    });
  });

  it('43 Werona Avenue Killara (lot B//DP395838, across the street from the line): not flagged', async () => {
    const f = fakeFetch([], []);
    await expect(railOrBusyRoadForPoint(fakeQuery(LOT), f.fn, 151.1589277, -33.760852)).resolves.toBeNull();
  });

  it('ignores a road label that is not a DCP busy road', async () => {
    const f = fakeFetch([{ roadnamelabel: 'WERONA AVE' }], []);
    await expect(railOrBusyRoadForPoint(fakeQuery(LOT), f.fn, 151.15, -33.76)).resolves.toBeNull();
  });

  it('the road filter names only DCP busy roads', () => {
    expect(ROAD_WHERE).toContain("'PACIFIC HWY'");
    expect(ROAD_WHERE).toContain("'SYDNEY NEWCASTLE FWY'");
    expect(RAIL_WHERE).toContain("SYM_CODE = 'SP2'");
  });
});

describe('railOrBusyRoadConstraints fails closed with a note', () => {
  it('no lot found: no flag, a note', async () => {
    const out = await railOrBusyRoadConstraints(fakeQuery(null), fakeFetch([], []).fn, 151.15, -33.76);
    expect(out.railOrBusyRoad).toBeUndefined();
    expect(out.railOrBusyRoadUnchecked).toMatch(/lot/);
  });

  it('map service fails: no flag, a note', async () => {
    const warn = jest.spyOn(console, 'warn').mockImplementation(() => undefined);
    const out = await railOrBusyRoadConstraints(fakeQuery(LOT), fakeFetch([], [], { fail: true }).fn, 151.15, -33.76);
    expect(out.railOrBusyRoad).toBeUndefined();
    expect(out.railOrBusyRoadUnchecked).toMatch(/map service/);
    warn.mockRestore();
  });

  it('a lot that adjoins nothing: no flag and no note', async () => {
    await expect(railOrBusyRoadConstraints(fakeQuery(LOT), fakeFetch([], []).fn, 151.15, -33.76)).resolves.toEqual({});
  });
});
