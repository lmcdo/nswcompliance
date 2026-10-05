/**
 * GET /api/sepp/parking-provisions — the round trip and its failure semantics.
 *
 * The card -> provision mapping is asserted in __tests__/lib/sepp-parking-cards.test.ts.
 * What this file pins is the part only the route can get wrong: the query is scoped to
 * one extraction generation, `is_current` is strict, a thrown query is a 503 rather than
 * six empty cards, and the client is always released.
 * @jest-environment node
 */
import { GET } from '@/app/api/sepp/parking-provisions/route';
import { HOUSING_SEPP_DOCUMENT_ID } from '@/lib/sepp-parking-cards';

const mockQuery = jest.fn();
const mockRelease = jest.fn();
jest.mock('@/lib/database/pool-manager', () => ({
  getClient: async () => ({ query: mockQuery, release: mockRelease }),
}));

beforeEach(() => jest.clearAllMocks());

describe('GET /api/sepp/parking-provisions', () => {
  it('scopes the query to one instrument and one extraction generation', async () => {
    mockQuery.mockResolvedValueOnce({ rows: [] });
    await GET();

    const [sql, params] = mockQuery.mock.calls[0];
    expect(params[0]).toBe(HOUSING_SEPP_DOCUMENT_ID);
    // Equality, not LIKE: the split generation's ids start with the same words, and
    // '_' is a LIKE wildcard, so a prefix match would pull both generations in.
    expect(sql).toMatch(/document_id = \$1/);
    expect(sql).not.toMatch(/document_id\s+I?LIKE/i);
    // `is_current` strict, not `IS NOT FALSE`: a NULL means we cannot say the
    // paragraph is still in force, and an unknown must not be served as the law.
    expect(sql).toMatch(/WHERE is_current\s*$/m);
    expect(sql).not.toMatch(/is_current IS NOT FALSE/);
    expect(sql).toMatch(/source_council IS NULL/);
    expect(mockRelease).toHaveBeenCalled();
  });

  it('asks for all nine predicates in a single round trip', async () => {
    mockQuery.mockResolvedValueOnce({ rows: [] });
    await GET();

    expect(mockQuery).toHaveBeenCalledTimes(1);
    const [, params] = mockQuery.mock.calls[0];
    expect(params[1]).toHaveLength(9);
    expect(params[1].every((p: string) => p.startsWith('%') && p.endsWith('%'))).toBe(true);
  });

  it('names the cards that found nothing, so drift is a number a check can watch', async () => {
    mockQuery.mockResolvedValueOnce({ rows: [] });
    const body = await (await GET()).json();

    expect(body.available).toBe(true);
    // The five cards that expect provisions, not the unsourced one — an in-fill card
    // with no rate is the answer, not a defect.
    expect(body.unmatchedCards).toEqual([
      'boarding_house',
      'co_living',
      'build_to_rent',
      'seniors_independent_living',
      'tod_affordable',
    ]);
    expect(body.citationNote).toMatch(/not\s+database-sourced/);
  });

  it('returns 503 on a failed query, never an empty answer', async () => {
    // "No rates found" and "the instrument could not be read" must not read the same:
    // the first is an answer about the law, the second is an outage.
    mockQuery.mockRejectedValueOnce(new Error('connection terminated'));
    const res = await GET();
    const body = await res.json();

    expect(res.status).toBe(503);
    expect(body.available).toBe(false);
    expect(body.cards).toBeUndefined();
    expect(body.message).toMatch(/not a finding that the SEPP sets no parking rates/);
    expect(mockRelease).toHaveBeenCalled();
  });

  it('carries each card a provision id and page through to the response', async () => {
    mockQuery.mockResolvedValueOnce({
      rows: [
        {
          id: 40310,
          ref_number: 'provision_187',
          pdf_page: 11,
          citation_status: null,
          provision_text:
            '(i) for development on land within an accessible area—0.2 parking spaces for each boarding room, (ii) otherwise—0.5 parking spaces for each boarding room,',
          document_id: HOUSING_SEPP_DOCUMENT_ID,
        },
      ],
    });
    const body = await (await GET()).json();

    const boardingHouse = body.cards.find((c: any) => c.key === 'boarding_house');
    expect(boardingHouse.resolved).toBe(true);
    expect(boardingHouse.provisions).toEqual([
      {
        role: 'rate',
        provisionId: 40310,
        refNumber: 'provision_187',
        pdfPage: 11,
        citationProven: false,
        text: expect.stringContaining('0.2 parking spaces for each boarding room'),
      },
    ]);
  });
});
