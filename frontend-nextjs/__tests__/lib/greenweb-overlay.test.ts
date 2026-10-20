/**
 * Ku-ring-gai Greenweb is flagged by the LOT, not the address point.
 * prior-art-checked: new gate (lib/greenweb-overlay.ts), no existing test covers it.
 * @jest-environment node
 */
import { greenwebForPoint, GREENWEB_LOT_SQL, GREENWEB_POINT_SQL } from '@/lib/greenweb-overlay';

type Row = Record<string, unknown>;
function fakeQuery(answers: { lot?: Row; point?: Row }) {
  const calls: string[] = [];
  const fn = jest.fn(async (sql: string) => {
    calls.push(sql);
    if (sql === GREENWEB_LOT_SQL) return { rows: answers.lot ? [answers.lot] : [] };
    if (sql === GREENWEB_POINT_SQL) return { rows: answers.point ? [answers.point] : [] };
    throw new Error('unexpected sql');
  });
  return { fn, calls };
}

describe('greenwebForPoint', () => {
  it('flags a lot when part of it overlaps Greenweb, on the lot basis', async () => {
    const q = fakeQuery({ lot: { lot_count: 1, categories: ['core', 'corridor (and buffer)'] } });
    await expect(greenwebForPoint(q.fn, 151.15, -33.75)).resolves.toEqual({
      onGreenweb: true,
      categories: ['core', 'corridor (and buffer)'],
      basis: 'lot',
    });
    expect(q.calls).toEqual([GREENWEB_LOT_SQL]); // the point is never consulted when a lot exists
  });

  it('does not flag a lot outside Greenweb, even if the point query would have said yes', async () => {
    const q = fakeQuery({
      lot: { lot_count: 1, categories: [] },
      point: { categories: ['core'] },
    });
    await expect(greenwebForPoint(q.fn, 151.15, -33.75)).resolves.toBeNull();
    expect(q.calls).toEqual([GREENWEB_LOT_SQL]);
  });

  it('falls back to the address point when there is no lot polygon, and says so', async () => {
    const q = fakeQuery({ lot: { lot_count: 0, categories: [] }, point: { categories: ['support'] } });
    await expect(greenwebForPoint(q.fn, 151.15, -33.75)).resolves.toEqual({
      onGreenweb: true,
      categories: ['support'],
      basis: 'point',
    });
    expect(q.calls).toEqual([GREENWEB_LOT_SQL, GREENWEB_POINT_SQL]);
  });

  it('returns null with no lot and a point outside Greenweb', async () => {
    const q = fakeQuery({ lot: { lot_count: 0, categories: [] }, point: { categories: [] } });
    await expect(greenwebForPoint(q.fn, 151.15, -33.75)).resolves.toBeNull();
  });

  it('returns null, without querying, for coordinates that are not finite', async () => {
    const q = fakeQuery({});
    await expect(greenwebForPoint(q.fn, NaN, -33.75)).resolves.toBeNull();
    expect(q.fn).not.toHaveBeenCalled();
  });

  it('lets a database error through so the caller can log it', async () => {
    const boom = jest.fn(async () => {
      throw new Error('db down');
    });
    await expect(greenwebForPoint(boom, 151.15, -33.75)).rejects.toThrow('db down');
  });

  it('tests the lot polygon by intersection, and the point by containment', () => {
    expect(GREENWEB_LOT_SQL).toMatch(/ST_Intersects\(o\.geom, lot\.geom\)/);
    expect(GREENWEB_LOT_SQL).toMatch(/layer_type = 'greenweb'/);
    expect(GREENWEB_POINT_SQL).toMatch(/ST_Contains\(o\.geom/);
  });
});
