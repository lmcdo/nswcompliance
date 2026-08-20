/**
 * A tripwire for the ancestor-key resolution, and nothing more.
 *
 * The rule itself is SQL, and its BEHAVIOUR is pinned against the real database
 * in tests/test_precinct_ancestor_resolution.py — eight cases including the two
 * that matter (a finer polygon inherits its parent's key; a precinct with its
 * own controls does not also take its parent's). Those tests are opt-in
 * (PYTEST_REAL_DB=1) because conftest_mocks stubs psycopg2, so they do not run
 * in CI.
 *
 * This file exists to catch the one thing CI otherwise could not: somebody
 * deleting the resolution while tidying the query. It asserts shape, which is
 * weak evidence on its own — a shape assertion cannot tell you the rule is
 * RIGHT, only that it is still there. Read it as a smoke alarm, not an
 * inspection.
 *
 * It also re-pins #992's invariant, because that is what forced the design:
 * the resolution went into the existing query rather than into a second lookup
 * precisely so that exactly one query per council survives.
 */

const mockQuery = jest.fn();
jest.mock('@/lib/db', () => ({ getPool: () => ({ query: mockQuery }) }));

import { getPrecinctProvisions } from '@/lib/precinct-service';

beforeEach(() => {
  mockQuery.mockReset();
  mockQuery.mockResolvedValue({ rows: [] });
});

describe('ancestor-key resolution is present in the served query', () => {
  it('resolves the key inside the provisions query', async () => {
    await getPrecinctProvisions('8.1.1.1', 'City of Parramatta', 'Parramatta');
    const sql = mockQuery.mock.calls[0][0] as string;

    expect(sql).toContain('precinct_keys');
    // The exact-match branch must be preferred over the ancestor branch.
    expect(sql).toContain('COALESCE');
    // Nearest ancestor, not the furthest: longest key wins.
    expect(sql).toContain('ORDER BY length(a.k) DESC');
  });

  it('matches ancestors by prefix, never with LIKE', async () => {
    // Marrickville ids such as '47_' contain an underscore, which LIKE reads as
    // a single-character wildcard: '47_.%' would match '470.1'. Nothing like
    // that exists today, which is exactly why it would go unnoticed.
    await getPrecinctProvisions('8.1.1.1', 'City of Parramatta', 'Parramatta');
    const sql = mockQuery.mock.calls[0][0] as string;

    expect(sql).toContain("left(r.id, length(a.k) + 1) = a.k || '.'");
    expect(sql).not.toMatch(/LIKE\s+a\.k/i);
  });

  it('still issues exactly ONE query per council', async () => {
    // #992's guarantee, and the reason the resolution is a CTE rather than a
    // second round trip. Two councils' controls merged onto one property is the
    // outcome worse than serving none.
    //
    // Rows must be returned for the preferred council, or the existing
    // former-council -> LGA-slug fallback fires and a second query is correct.
    // My first version of this test asserted 1 against an empty mock and failed
    // on that fallback, not on anything this change did.
    mockQuery.mockResolvedValue({ rows: [{ id: 1, control_type: 'height' }] });
    await getPrecinctProvisions('8.1.1.1', 'City of Parramatta', 'Parramatta');
    expect(mockQuery).toHaveBeenCalledTimes(1);

    const params = mockQuery.mock.calls[0][1];
    expect(params[0]).toEqual(['8.1.1.1']);   // ids still passed unchanged
    expect(params[1]).toBe('parramatta');      // a single slug, never an ANY()
  });

  it('keeps the currency filters the resolution reads through', async () => {
    // The CTE reads regulatory_provisions a second time to find available keys.
    // Without is_current there, a superseded precinct key could be inherited.
    await getPrecinctProvisions('8.1.1.1', 'City of Parramatta', 'Parramatta');
    const sql = mockQuery.mock.calls[0][0] as string;
    const cte = sql.slice(sql.indexOf('avail AS'), sql.indexOf('precinct_keys'));

    expect(cte).toContain('is_current');
    expect(cte).toContain('v2_is_actionable');
    expect(cte).toContain('source_council');
  });
});
