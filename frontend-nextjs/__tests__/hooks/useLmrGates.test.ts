import { gatesKey, gatesForKey, type LmrGates } from '@/hooks/useLmrGates';

const A: LmrGates = {
  in_lmr_area: true, in_tod: false, near_town_centre: true, town_centre: 'X',
  lmr_excluded: false, dual_occ_prohibited: false, source: 'test',
};

describe('useLmrGates answer belongs to one lot', () => {
  it('a stored answer for lot A is not returned for lot B', () => {
    const stored = { gates: A, loading: false, failed: false, key: gatesKey(-33.8, 151.0) };
    const forB = gatesForKey(stored, gatesKey(-33.9, 151.1));
    expect(forB.gates).toBeNull();
    expect(forB.loading).toBe(true);
  });

  it('the answer is returned for the lot it was fetched for', () => {
    const k = gatesKey(-33.8, 151.0);
    expect(gatesForKey({ gates: A, loading: false, failed: false, key: k }, k).gates).toBe(A);
  });

  it('no coordinates means no answer and nothing loading', () => {
    expect(gatesKey(undefined, 151)).toBeNull();
    expect(gatesKey(NaN, 151)).toBeNull();
    expect(gatesForKey({ gates: A, loading: false, failed: false, key: 'x' }, null)).toEqual(
      { gates: null, loading: false, failed: false },
    );
  });
});
