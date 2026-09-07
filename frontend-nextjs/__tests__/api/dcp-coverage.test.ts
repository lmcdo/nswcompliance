/**
 * /api/dcp/coverage — Inner West sub-council omission fixed 2026-09-07.
 *
 * The route's SQL used to filter `r.parent_lga IS NULL`, meant to bucket a
 * sub-council's rows under its parent's display name ("shown under Inner
 * West"). But Inner West's own registry row holds zero current controls, so
 * the filter silently DROPPED Ashfield/Leichhardt/Marrickville instead of
 * showing them under anything — 99 current controls, and the councils with
 * the deepest DCP integration, invisible to the one endpoint that answers
 * "which councils do you cover".
 *
 * First fix attempt (same day) removed the filter with no aggregation,
 * which listed the three ABOLISHED pre-2016-merger councils as separate
 * current councils (25 -> 28) — Sol cross-review (HIGH 0.96, on push)
 * caught this as its own overclaim: those three no longer exist as their
 * own local government areas, only "Inner West Council" does. Corrected to
 * aggregate them under the parent's CURRENT display name via COALESCE
 * (25 -> 26: the 25 unaffected councils plus Inner West, newly surfaced).
 * Sol also caught (HIGH 0.99) that the verification script's mirror of this
 * query was missing the needs_review guard despite claiming to match the
 * route exactly — this suite pins both corrections.
 *
 * This suite pins the query shape rather than re-deriving a full mock DB,
 * matching this file's sibling suites.
 * @jest-environment node
 */
import { NextResponse } from 'next/server';

const mockQuery = jest.fn();
jest.mock('@/lib/db', () => ({
  getPool: () => ({ query: (...args: unknown[]) => mockQuery(...args) }),
}));

import { GET } from '@/app/api/dcp/coverage/route';

function rows(names: string[]) {
  return { rows: names.map((display_name) => ({ display_name })) };
}

describe('GET /api/dcp/coverage', () => {
  beforeEach(() => {
    mockQuery.mockReset();
  });

  it('no longer excludes sub-councils outright -- the exact standalone filter that dropped Inner West', async () => {
    // The OLD bug was `AND r.parent_lga IS NULL` as its own exclusionary
    // clause. The FIX still legitimately contains the substring
    // "parent_lga IS NULL" (as one arm of the new OR-based is_active
    // guard below), so this must not be a blanket substring check -- Sol
    // cross-review (MEDIUM 0.99) caught the first version of this test
    // failing against the very query it was meant to validate. Anchored
    // to the specific standalone-AND-clause shape instead.
    mockQuery.mockResolvedValue(rows(['Inner West']));
    await GET();
    const [sql] = mockQuery.mock.calls[0];
    expect(sql).not.toMatch(/AND\s+r\.parent_lga\s+IS\s+NULL\s*(?:AND|ORDER BY|$)/i);
  });

  it('aggregates a sub-council under its CURRENT parent via COALESCE, not as a separate council, and gates both rows on is_active', async () => {
    mockQuery.mockResolvedValue(rows(['Inner West']));
    await GET();
    const [sql] = mockQuery.mock.calls[0];
    expect(sql).toMatch(/COALESCE\(parent\.display_name,\s*r\.display_name\)/i);
    expect(sql).toMatch(/LEFT JOIN lga_registry parent ON parent\.slug = r\.parent_lga/i);
    // Currency filter on BOTH sides of the self-join -- a retired child or
    // a retired parent must not surface a council. 0 rows are currently
    // inactive (checked live, not assumed), so this guards a future state.
    expect(sql).toMatch(/r\.is_active = TRUE/i);
    // A row WITH a declared parent must require that parent to be
    // explicitly active -- not merely "parent.is_active is not FALSE",
    // which would also pass a missing parent row or one with NULL
    // is_active (Sol HIGH 0.99, round 2). Only a PARENTLESS row may pass
    // on r.parent_lga IS NULL alone.
    expect(sql).toMatch(/r\.parent_lga IS NULL OR parent\.is_active = TRUE/i);
  });

  it('still gates on needs_review, matching every other serving path', async () => {
    mockQuery.mockResolvedValue(rows(['Inner West']));
    await GET();
    const [sql] = mockQuery.mock.calls[0];
    expect(sql).toMatch(/needs_review IS NULL OR c\.needs_review = FALSE/i);
  });

  it('still excludes nsw_statewide (not a real council)', async () => {
    mockQuery.mockResolvedValue(rows(['Inner West']));
    await GET();
    const [sql] = mockQuery.mock.calls[0];
    expect(sql).toMatch(/nsw_statewide/);
  });

  it('returns the aggregated result set the query produces, unmodified', async () => {
    mockQuery.mockResolvedValue(
      rows(['Bayside', 'Inner West', 'Woollahra']),
    );
    const res = (await GET()) as NextResponse;
    const body = await res.json();
    expect(body.councils).toEqual(['Bayside', 'Inner West', 'Woollahra']);
    // The abolished pre-2016-merger names must never appear as their own
    // entries -- if they do, the aggregation regressed to the first,
    // Sol-caught, overclaiming fix attempt. Asserted independently, not
    // via arrayContaining(all three) -- Sol cross-review (LOW 0.99): that
    // form only fails when ALL three leak together, silently passing a
    // regression that leaks just one or two.
    for (const abolished of ['Ashfield', 'Leichhardt', 'Marrickville']) {
      expect(body.councils).not.toContain(abolished);
    }
  });

  it('fails visibly (500, empty list) on a DB error -- never a silent empty success', async () => {
    mockQuery.mockRejectedValue(new Error('connection refused'));
    const res = (await GET()) as NextResponse;
    expect(res.status).toBe(500);
    const body = await res.json();
    expect(body.councils).toEqual([]);
  });
});
