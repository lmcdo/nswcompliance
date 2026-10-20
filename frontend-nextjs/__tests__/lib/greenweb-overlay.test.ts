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

  it('reports no lot and a point outside Greenweb as not checked', async () => {
    const q = fakeQuery({ lot: { lot_count: 0, categories: [] }, point: { categories: [] } });
    // The lot was never checked, so this is not a "no": it is reported as unchecked (Sol, 2026-10-20).
    await expect(greenwebForPoint(q.fn, 151.15, -33.75)).rejects.toThrow('no cadastre lot');
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

  it('tests the lot polygon by intersection, covers the point (boundary counts), and reads only Ku-ring-gai', () => {
    expect(GREENWEB_LOT_SQL).toMatch(/ST_Intersects\(o\.geom, lot\.geom\)/);
    expect(GREENWEB_LOT_SQL).toMatch(/ST_Covers\(l\.geom, pt\.g\)/);
    expect(GREENWEB_LOT_SQL).toMatch(/layer_type = 'greenweb'/);
    expect(GREENWEB_LOT_SQL).toMatch(/lga_name = 'KU-RING-GAI'/);
    expect(GREENWEB_POINT_SQL).toMatch(/ST_Covers\(o\.geom/);
    expect(GREENWEB_POINT_SQL).toMatch(/lga_name = 'KU-RING-GAI'/);
  });
});

describe('greenwebConstraints', () => {
  it('returns a plain-words note instead of throwing when the check fails', async () => {
    const { greenwebConstraints } = await import('@/lib/greenweb-overlay');
    const failing = async () => { throw new Error('db down'); };
    const out = await greenwebConstraints(failing, 151.15, -33.75);
    expect(out.greenweb).toBeUndefined();
    expect(out.greenwebUnchecked).toMatch(/couldn't check the council's Greenweb/);
  });
});

describe('greenwebConstraints when no lot is found', () => {
  it('says the lot could not be checked instead of answering "not on Greenweb"', async () => {
    const { greenwebConstraints } = await import('@/lib/greenweb-overlay');
    const q = async (sql: string) => (sql.includes('lot_count')
      ? { rows: [{ lot_count: 0, categories: [] }] }
      : { rows: [{ categories: [] }] });
    const out = await greenwebConstraints(q, 151.15, -33.75);
    expect(out.greenweb).toBeUndefined();
    expect(out.greenwebUnchecked).toMatch(/couldn't find this property's lot/);
  });
});
