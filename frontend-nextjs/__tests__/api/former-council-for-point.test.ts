/**
 * An Inner West property's former council comes from its own lot, not the suburb/postcode guess.
 *
 * Measured live 2026-10-11 (the lot centre of each real address, through this exact SQL):
 * 15 of 16 lots carry the right former council; the 16th (18-20 Wilson St Newtown) carries none,
 * so the caller keeps the mapping's answer. The mapping alone was wrong for 3 of 16:
 * 50 Edith St St Peters (-> Ashfield), 100 Enmore Rd Enmore and 5 George St Lewisham (-> Leichhardt).
 */
const mockQuery = jest.fn();
jest.mock('@/lib/db', () => ({
  getPool: () => ({ query: (...args: unknown[]) => mockQuery(...args) }),
}));
jest.mock('@/lib/nsw-planning-portal', () => ({ getPropertyCoordinates: jest.fn() }));

import { getFormerCouncilForPoint } from '@/lib/precinct-service';

beforeEach(() => mockQuery.mockReset());

it('returns the lot\'s stored former council, capitalised', async () => {
  mockQuery.mockResolvedValue({ rows: [{ former_council: 'marrickville' }] });
  await expect(getFormerCouncilForPoint(-33.9115, 151.1795)).resolves.toBe('Marrickville');
  const [sql, params] = mockQuery.mock.calls[0];
  expect(sql).toContain('ST_Contains');
  expect(params).toEqual([151.1795, -33.9115]); // lon, lat
});

it('returns null when no Inner West lot is under the point, so the caller keeps its answer', async () => {
  mockQuery.mockResolvedValue({ rows: [] });
  await expect(getFormerCouncilForPoint(-33.89, 151.17)).resolves.toBeNull();
});

it('returns null, not a guess, when the query fails or the point is not a number', async () => {
  mockQuery.mockRejectedValue(new Error('timeout'));
  await expect(getFormerCouncilForPoint(-33.89, 151.17)).resolves.toBeNull();
  await expect(getFormerCouncilForPoint(Number.NaN, 151.17)).resolves.toBeNull();
});
