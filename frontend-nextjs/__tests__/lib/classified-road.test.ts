/**
 * The lot fronts a State road / classified road: lot touches a cadastre road corridor that a TfNSW centreline runs in.
 * prior-art-checked: new check (lib/classified-road.ts); mirrors rail-busy-road.test.ts.
 * The live check returned these answers on 2026-10-21 for the real lots named below.
 * @jest-environment node
 */
import {
  classifiedRoadForPoint,
  classifiedRoadConstraints,
  roadClass,
  INSIDE_CORRIDOR_SQL,
  CORRIDOR_URL,
  STATE_URL,
  REGIONAL_URL,
  TOLERANCE_M,
  CENTRELINE_SEARCH_M,
  MIN_INSIDE_M,
  type FetchFn,
} from '@/lib/classified-road';
import { LOT_SQL } from '@/lib/lot-adjacency';

const LOT = JSON.stringify({ type: 'Polygon', coordinates: [[[151.1, -33.7], [151.1001, -33.7], [151.1001, -33.7001], [151.1, -33.7]]] });
const LINE = { type: 'LineString', coordinates: [[151.1, -33.7], [151.11, -33.7]] };
const CORR = { type: 'Polygon', coordinates: [[[151.1, -33.7], [151.11, -33.7], [151.11, -33.6999], [151.1, -33.7]]] };

type Line = { road_number: string; road_name: string | null; admin_class: string };

/** DB fake: the lot, then which line indexes run inside a corridor (what PostGIS would answer). */
function fakeQuery(lotGeojson: string | null, insideIdx: number[] = []) {
  const calls: unknown[][] = [];
  const fn = jest.fn(async (sql: string, params: unknown[] = []) => {
    calls.push(params);
    if (sql === LOT_SQL) return { rows: [{ lot_geojson: lotGeojson }] };
    if (sql === INSIDE_CORRIDOR_SQL) return { rows: insideIdx.map((i) => ({ i })) };
    throw new Error('unexpected sql');
  });
  return { fn, calls };
}

function fakeFetch(corridors: number, state: Line[], regional: Line[], opts: { fail?: boolean } = {}) {
  const bodies: Record<string, URLSearchParams> = {};
  const fn: FetchFn = jest.fn(async (url: string, init) => {
    bodies[url] = init.body;
    if (opts.fail) return { ok: false, status: 504, json: async () => ({}) };
    const feats =
      url === CORRIDOR_URL
        ? Array.from({ length: corridors }, () => ({ properties: { roadnamelabel: 'X' }, geometry: CORR }))
        : (url === STATE_URL ? state : regional).map((p) => ({ properties: p, geometry: LINE }));
    return { ok: true, status: 200, json: async () => ({ type: 'FeatureCollection', features: feats }) };
  });
  return { fn, bodies };
}

const PACIFIC: Line = { road_number: '0000010', road_name: 'PACIFIC', admin_class: 'S' };
const MARION: Line = { road_number: '0002013', road_name: 'MARION', admin_class: 'R' };
const KISSING_PT: Line = { road_number: '0007421', road_name: 'KISSING PT', admin_class: 'R' };

describe('roadClass', () => {
  it('State = S; Regional 7000-7999 unclassified; other Regional classified; non-standard number classified', () => {
    expect(roadClass('S', '0007776')).toBe('state');
    expect(roadClass('R', '0002013')).toBe('classified_regional');
    expect(roadClass('R', '0007118')).toBe('unclassified_regional');
    expect(roadClass('R', '2350010')).toBe('classified_regional');
    expect(roadClass('L', '0000001')).toBeNull();
  });
});

describe('classifiedRoadForPoint', () => {
  it('1311 Pacific Hwy Turramurra: fronts State road 0000010', async () => {
    const f = fakeFetch(1, [PACIFIC], []);
    const q = fakeQuery(LOT, [0]);
    await expect(classifiedRoadForPoint(q.fn, f.fn, 151.127701, -33.733205)).resolves.toEqual({
      state: true, classified: true, unclassifiedRegional: false,
      roads: [{ roadNumber: '0000010', roadName: 'PACIFIC', roadClass: 'state' }],
    });
    // Corridors within the tolerance of the lot; centrelines within the search distance; the run-inside floor.
    expect(f.bodies[CORRIDOR_URL].get('distance')).toBe(String(TOLERANCE_M));
    expect(f.bodies[STATE_URL].get('distance')).toBe(String(CENTRELINE_SEARCH_M));
    expect(f.bodies[REGIONAL_URL].get('distance')).toBe(String(CENTRELINE_SEARCH_M));
    expect(q.calls[1][2]).toBe(MIN_INSIDE_M);
  });

  it('30 Marion St Leichhardt: classified Regional 0002013, not State', async () => {
    const out = await classifiedRoadForPoint(fakeQuery(LOT, [0]).fn, fakeFetch(1, [], [MARION]).fn, 151.154911, -33.884155);
    expect(out).toMatchObject({ state: false, classified: true, unclassifiedRegional: false });
  });

  it('2 Kissing Point Rd Turramurra: unclassified Regional 0007421 -> not classified', async () => {
    const out = await classifiedRoadForPoint(fakeQuery(LOT, [0]).fn, fakeFetch(1, [], [KISSING_PT]).fn, 151.128049, -33.733989);
    expect(out).toMatchObject({ state: false, classified: false, unclassifiedRegional: true });
  });

  it('1//DP519532 Turramurra (one street back from the Pacific Hwy): centreline nearby but in no corridor it touches', async () => {
    await expect(classifiedRoadForPoint(fakeQuery(LOT, []).fn, fakeFetch(4, [PACIFIC], []).fn, 151.127804, -33.73288)).resolves.toBeNull();
  });

  it('43 Werona Ave Killara: no State or Regional road near', async () => {
    const q = fakeQuery(LOT);
    await expect(classifiedRoadForPoint(q.fn, fakeFetch(1, [], []).fn, 151.1589277, -33.760852)).resolves.toBeNull();
    expect(q.fn).toHaveBeenCalledTimes(1); // no corridor test needed
  });
});

describe('classifiedRoadConstraints fails closed with a note', () => {
  it('no lot found: no flag, a note', async () => {
    const out = await classifiedRoadConstraints(fakeQuery(null).fn, fakeFetch(0, [], []).fn, 151.15, -33.76);
    expect(out.classifiedRoad).toBeUndefined();
    expect(out.classifiedRoadUnchecked).toMatch(/lot/);
  });

  it('map service fails: no flag, a note', async () => {
    const warn = jest.spyOn(console, 'warn').mockImplementation(() => undefined);
    const out = await classifiedRoadConstraints(fakeQuery(LOT).fn, fakeFetch(0, [], [], { fail: true }).fn, 151.15, -33.76);
    expect(out.classifiedRoad).toBeUndefined();
    expect(out.classifiedRoadUnchecked).toMatch(/map service/);
    warn.mockRestore();
  });

  it('a capped (cut-off) answer is a failure, not a "no"', async () => {
    const warn = jest.spyOn(console, 'warn').mockImplementation(() => undefined);
    const fn: FetchFn = async () => ({ ok: true, status: 200, json: async () => ({ features: [], properties: { exceededTransferLimit: true } }) });
    const out = await classifiedRoadConstraints(fakeQuery(LOT).fn, fn, 151.15, -33.76);
    expect(out.classifiedRoadUnchecked).toMatch(/map service/);
    warn.mockRestore();
  });
});
