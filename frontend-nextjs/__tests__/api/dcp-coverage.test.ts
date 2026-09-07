/**
 * /api/dcp/coverage — Inner West sub-council omission fixed 2026-09-07.
 *
 * The route's SQL used to filter `r.parent_lga IS NULL`, meant to bucket a
 * sub-council's rows under its parent's display name ("shown under Inner
 * West"). But Inner West's own registry row holds zero current controls, so
 * the filter silently DROPPED Ashfield/Leichhardt/Marrickville instead of
 * showing them under anything — 99 current controls, and the three councils
 * with the deepest DCP integration in the product, invisible to the one
 * endpoint that answers "which councils do you cover". Verified against
 * production before shipping: dropping the filter took the result from 25
 * to 28, adding exactly those three, zero duplicates.
 *
 * This suite pins the query shape (no parent_lga predicate) rather than
 * re-deriving a full mock DB, matching this file's sibling suites.
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

  it('does not filter on parent_lga -- the exact predicate that dropped Inner West sub-councils', async () => {
    mockQuery.mockResolvedValue(rows(['Ashfield']));
    await GET();
    const [sql] = mockQuery.mock.calls[0];
    expect(sql).not.toMatch(/parent_lga/i);
  });

  it('still excludes nsw_statewide (not a real council)', async () => {
    mockQuery.mockResolvedValue(rows(['Ashfield']));
    await GET();
    const [sql] = mockQuery.mock.calls[0];
    expect(sql).toMatch(/nsw_statewide/);
  });

  it('passes through Inner West sub-council names by their own display name', async () => {
    mockQuery.mockResolvedValue(
      rows(['Ashfield', 'Leichhardt', 'Marrickville', 'Woollahra']),
    );
    const res = (await GET()) as NextResponse;
    const body = await res.json();
    expect(body.councils).toEqual(
      expect.arrayContaining(['Ashfield', 'Leichhardt', 'Marrickville']),
    );
  });

  it('fails visibly (500, empty list) on a DB error -- never a silent empty success', async () => {
    mockQuery.mockRejectedValue(new Error('connection refused'));
    const res = (await GET()) as NextResponse;
    expect(res.status).toBe(500);
    const body = await res.json();
    expect(body.councils).toEqual([]);
  });
});
