import { readFileSync } from 'fs';
import path from 'path';
import { lotRingsToWgs84Wkt } from '@/lib/geo-utils';

// A real NSW cadastre lot in Cessnock (EPSG:3857): 44.7 m2 inside the council's
// 1% AEP extent while the address point is 6 m outside it (2026-10-28).
const LOT = JSON.parse(readFileSync(path.join(__dirname, '../../../tests/fixtures/flood_partial_map_edge_lot.json'), 'utf8'));

describe('lotRingsToWgs84Wkt', () => {
  it('turns Web Mercator rings into a closed WGS84 polygon around the address point', () => {
    const wkt = lotRingsToWgs84Wkt(LOT.rings, 3857)!;
    expect(wkt.startsWith('POLYGON((')).toBe(true);
    const pts = wkt.slice('POLYGON(('.length, -2).split(', ').map((p) => p.split(' ').map(Number));
    expect(pts[0]).toEqual(pts[pts.length - 1]);
    const lons = pts.map((p) => p[0]);
    const lats = pts.map((p) => p[1]);
    expect(Math.min(...lons)).toBeLessThan(LOT.lng);
    expect(Math.max(...lons)).toBeGreaterThan(LOT.lng);
    expect(Math.min(...lats)).toBeLessThan(LOT.lat);
    expect(Math.max(...lats)).toBeGreaterThan(LOT.lat);
  });

  it('passes lat/long systems through unchanged', () => {
    const ring = [[151.5, -32.8], [151.6, -32.8], [151.6, -32.9], [151.5, -32.8]];
    expect(lotRingsToWgs84Wkt([ring], 4283)).toBe('POLYGON((151.5 -32.8, 151.6 -32.8, 151.6 -32.9, 151.5 -32.8))');
  });

  it('closes an open ring', () => {
    const ring = [[151.5, -32.8], [151.6, -32.8], [151.6, -32.9], [151.55, -32.85]];
    expect(lotRingsToWgs84Wkt([ring], 4326)!.endsWith('151.55 -32.85, 151.5 -32.8))')).toBe(true);
  });

  it.each([
    ['no rings', undefined, 3857],
    ['empty', [], 3857],
    ['a ring under 4 points', [[[1, 2], [3, 4], [1, 2]]], 3857],
    ['an unknown coordinate system', [[[1, 2], [3, 4], [5, 6], [1, 2]]], 28356],
    ['no coordinate system', [[[1, 2], [3, 4], [5, 6], [1, 2]]], null],
  ])('gives null for %s, so only the point is tested', (_n, rings, wkid) => {
    expect(lotRingsToWgs84Wkt(rings as number[][][] | undefined, wkid as number | null)).toBeNull();
  });
});
