import fs from 'fs';
import path from 'path';
import {
  measureStreetFrontage,
  widthVerdict,
  widthRange,
  type RoadShape,
  type StreetFrontage,
} from '@/lib/geometry/street-frontage';
import { scaleFactorForRing } from '@/lib/geometry/mercator';

interface Fixture { lotRing: number[][]; roads: RoadShape[] }

function load(name: string): Fixture {
  const p = path.join(__dirname, '..', '..', 'fixtures', 'street-frontage', `${name}.json`);
  return JSON.parse(fs.readFileSync(p, 'utf8')) as Fixture;
}

function run(name: string): StreetFrontage {
  const f = load(name);
  return measureStreetFrontage(f.lotRing, f.roads);
}

describe('measureStreetFrontage on real cadastre fixtures', () => {
  it('winston-hills-wedge: street edge is 13.3 m, not the 22.4 m rectangle side', () => {
    const sf = run('winston-hills-wedge');
    expect(sf.status).toBe('measured');
    expect(sf.roads).toHaveLength(1);
    expect(sf.roads[0].road).toBe('BERRIGAN ST');
    expect(Math.abs(sf.roads[0].frontage_m - 13.34)).toBeLessThanOrEqual(0.1);
    expect(sf.roads[0].frontage_m).toBeLessThan(22.4 - 5);
    expect(sf.roads[0].minFrontHalf_m).toBeGreaterThanOrEqual(12.8);
    expect(sf.roads[0].minFrontHalf_m).toBeLessThanOrEqual(14.0);
    expect(sf.roads[0].maxAll_m).toBeGreaterThan(19);
    expect(widthVerdict(sf, 12)).toBe('meets');
    expect(widthVerdict(sf, 18)).toBe('depends');
  });

  it('padstow-gap: lot and road 1.3 m apart still yield the road', () => {
    const sf = run('padstow-gap');
    expect(sf.roads).toHaveLength(1);
    expect(sf.roads[0].road).toBe('WYREEMA AVE');
    expect(Math.abs(sf.roads[0].frontage_m - 15.27)).toBeLessThanOrEqual(0.15);
  });

  it('mortdale-narrow: 6.19 m frontage is below 12 m', () => {
    const sf = run('mortdale-narrow');
    const r = sf.roads.find((x) => x.road === 'BROUGHTON ST');
    expect(r).toBeDefined();
    expect(Math.abs(r!.frontage_m - 6.19)).toBeLessThanOrEqual(0.15);
    expect(widthVerdict(sf, 12)).toBe('below');
  });

  it('haberfield-corner-lane: two named roads, lane counted separately', () => {
    const sf = run('haberfield-corner-lane');
    const names = sf.roads.map((r) => r.road);
    expect(sf.roads.length).toBeGreaterThanOrEqual(2);
    expect(names).toEqual(expect.arrayContaining(['LOGAN AVE', 'NICHOLLS AVE']));
    expect(sf.roads.every((r) => typeof r.road === 'string' && r.road.length > 0)).toBe(true);
    expect(sf.unnamedRoadEdge_m).toBeGreaterThan(0);
    for (const req of [6, 10, 12, 15, 20]) {
      const each = sf.roads.map((r) => widthVerdict({ ...sf, roads: [r] }, req));
      const combined = widthVerdict(sf, req);
      if (each.every((v) => v === each[0])) expect(combined).toBe(each[0]);
      else expect(combined).toBe('depends');
    }
  });

  it('vaucluse-battleaxe: narrow handle, wide head -> depends', () => {
    const sf = run('vaucluse-battleaxe');
    const r = sf.roads.find((x) => x.road === 'HOPETOUN AVE');
    expect(r).toBeDefined();
    expect(r!.frontage_m).toBeLessThan(8);
    expect(widthVerdict(sf, 12)).toBe('depends');
  });
});

describe('measureStreetFrontage synthetic rectangle', () => {
  const y0 = -3998985;
  const scale = scaleFactorForRing([[0, y0], [1, y0], [1, y0 + 1], [0, y0 + 1], [0, y0]]);
  const rect = (x0: number, y1: number, w: number, h: number): number[][] => {
    const a = x0 * scale, b = (x0 + w) * scale;
    const c = y0 + y1 * scale, d = y0 + (y1 + h) * scale;
    return [[a, c], [b, c], [b, d], [a, d], [a, c]];
  };

  const lot = rect(0, 0, 15, 40);
  const road: RoadShape = { name: 'TEST ST', rings: [rect(-20, -10, 55, 10)] };
  const sf = measureStreetFrontage(lot, [road]);

  it('measures 15 m frontage and front-half width', () => {
    expect(sf.status).toBe('measured');
    expect(sf.roads).toHaveLength(1);
    expect(sf.roads[0].frontage_m).toBeGreaterThan(14.6);
    expect(sf.roads[0].frontage_m).toBeLessThan(15.4);
    expect(Math.abs(sf.roads[0].minFrontHalf_m - 15)).toBeLessThanOrEqual(0.4);
  });

  it('verdicts at 12, 15, 20', () => {
    expect(widthVerdict(sf, 12)).toBe('meets');
    expect(widthVerdict(sf, 15)).toBe('depends');
    expect(widthVerdict(sf, 20)).toBe('below');
  });
});

describe('edge cases', () => {
  const lotRing = load('winston-hills-wedge').lotRing;

  it('null lot is unavailable', () => {
    const sf = measureStreetFrontage(null, []);
    expect(sf.status).toBe('unavailable');
    expect(widthVerdict(sf, 12)).toBe('depends');
    expect(widthRange(sf)).toBeNull();
  });

  it('no roads is not_identified and depends', () => {
    const sf = measureStreetFrontage(lotRing, []);
    expect(sf.status).toBe('not_identified');
    expect(widthVerdict(sf, 12)).toBe('depends');
    expect(widthRange(sf)).toBeNull();
  });

  it('whitespace road name is unnamed', () => {
    const f = load('winston-hills-wedge');
    const sf = measureStreetFrontage(f.lotRing, f.roads.map((r) => ({ ...r, name: '  ' })));
    expect(sf.roads).toHaveLength(0);
    expect(sf.status).toBe('not_identified');
    expect(sf.unnamedRoadEdge_m).toBeGreaterThan(0);
  });

  it('widthRange returns a range when measured, null for null/undefined', () => {
    const f = load('winston-hills-wedge');
    const sf = measureStreetFrontage(f.lotRing, f.roads);
    const wr = widthRange(sf);
    expect(wr).not.toBeNull();
    expect(wr!.min).toBeLessThanOrEqual(wr!.max);
    expect(widthRange(null)).toBeNull();
    expect(widthRange(undefined)).toBeNull();
  });
});

describe('streetFrontageText', () => {
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  const { streetFrontageText } = require('@/lib/geometry/street-frontage');
  it('names the road and the measured length', () => {
    const sf = { status: 'measured', unnamedRoadEdge_m: 0,
      roads: [{ road: 'BERRIGAN ST', frontage_m: 13.34, minFrontHalf_m: 13.38, maxAll_m: 22.4, depth_m: 39.5 }] };
    expect(streetFrontageText(sf)).toBe('13.3 m along Berrigan St');
  });
  it('lists every road on a corner lot', () => {
    const sf = { status: 'measured', unnamedRoadEdge_m: 14, roads: [
      { road: 'LOGAN AVE', frontage_m: 26.25, minFrontHalf_m: 18.5, maxAll_m: 26.2, depth_m: 40 },
      { road: 'NICHOLLS AVE', frontage_m: 46.14, minFrontHalf_m: 45.9, maxAll_m: 46.1, depth_m: 20 }] };
    expect(streetFrontageText(sf)).toBe('26.3 m along Logan Ave and 46.1 m along Nicholls Ave');
  });
  it('is null, never a substitute number, when nothing was measured', () => {
    expect(streetFrontageText(null)).toBeNull();
    expect(streetFrontageText({ status: 'not_identified', roads: [], unnamedRoadEdge_m: 0 })).toBeNull();
    expect(streetFrontageText({ status: 'unavailable', roads: [], unnamedRoadEdge_m: 0 })).toBeNull();
  });
});

describe('which lot edges count as street frontage (each rule alone)', () => {
  const y0 = -3998985;
  const scale = scaleFactorForRing([[0, y0], [1, y0], [1, y0 + 1], [0, y0 + 1], [0, y0]]);
  const ring = (pts: [number, number][]): number[][] => [...pts, pts[0]].map(([x, y]) => [x * scale, y0 + y * scale]);
  // Road along the south side, y in [-10, 0].
  const road: RoadShape = { name: 'TEST ST', rings: [ring([[-20, -10], [60, -10], [60, 0], [-20, 0]])] };

  it('a short side step at the road is not frontage (parallel rule)', () => {
    // 4 m step up from the road at x=15: within 2.5 m of the road for most of its length, but at right angles.
    const sf = measureStreetFrontage(ring([[0, 0], [15, 0], [15, 4], [20, 4], [20, 40], [0, 40]]), [road]);
    expect(sf.roads[0].frontage_m).toBeGreaterThan(14.6);
    expect(sf.roads[0].frontage_m).toBeLessThan(15.4);
  });

  it('a side boundary that slants away from the road is not frontage (half-the-edge rule)', () => {
    // Edge from (15,0) to (40,12): within 30 degrees of the road but only its first few metres are near it.
    const sf = measureStreetFrontage(ring([[0, 0], [15, 0], [40, 12], [40, 40], [0, 40]]), [road]);
    expect(sf.roads[0].frontage_m).toBeGreaterThan(14.6);
    expect(sf.roads[0].frontage_m).toBeLessThan(15.4);
  });
});
