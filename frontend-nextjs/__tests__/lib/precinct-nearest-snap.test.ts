/**
 * A lot in no precinct outline is snapped to the nearest one only where the former council's
 * precincts tile its land (Marrickville, Leichhardt). Ashfield's are town centres: 145 Queen St
 * Ashfield, in no outline, was given Part 7 Hurlstone Park (address audit 2026-10-15).
 */
const mockQuery = jest.fn();
jest.mock('@/lib/db', () => ({
  getPool: () => ({ query: (...args: unknown[]) => mockQuery(...args) }),
}));
jest.mock('@/lib/nsw-planning-portal', () => ({ getPropertyCoordinates: jest.fn() }));

import { getPrecinctForAddress, NEAREST_SNAP_FORMER_COUNCILS } from '@/lib/precinct-service';

beforeEach(() => mockQuery.mockReset());

it('snaps only to precincts of councils whose precincts tile their land', async () => {
  mockQuery.mockResolvedValueOnce({ rows: [] }).mockResolvedValueOnce({ rows: [] });
  const r = await getPrecinctForAddress('145 QUEEN STREET ASHFIELD', 'Inner West', { lat: -33.9012, lon: 151.1269 });
  expect(r).toBeNull();
  const [sql, params] = mockQuery.mock.calls[1];
  expect(sql).toContain('LOWER(former_council) = ANY($4::text[])');
  expect(params[3]).toEqual(NEAREST_SNAP_FORMER_COUNCILS);
  // an exact LEP-layer overlay (Marrickville 2.26) is never snapped to
  expect(sql).toContain("COALESCE(extraction_method, '') NOT LIKE 'nsw_planning_local_provisions%'");
  expect(NEAREST_SNAP_FORMER_COUNCILS).not.toContain('ashfield');
});

it('still snaps a Marrickville edge lot to its nearest precinct', async () => {
  mockQuery.mockResolvedValueOnce({ rows: [] }).mockResolvedValueOnce({ rows: [{
    precinct_id: '22_', precinct_name: 'Dulwich Hill Station South', lga: 'Inner West',
    former_council: 'Marrickville', confidence_score: 0.5, distance_m: 12,
  }] });
  const r = await getPrecinctForAddress('9 TENNYSON STREET DULWICH HILL', 'Inner West', { lat: -33.9, lon: 151.14 });
  expect(r?.precinctId).toBe('22_');
});
