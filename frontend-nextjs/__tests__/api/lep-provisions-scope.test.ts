/**
 * /api/lep/provisions — scoped to one instrument.
 * Clause numbers repeat across every Standard Instrument LEP; the route used to match on
 * clause number alone and so served Inner West LEP 2022 text for any council's clause.
 * @jest-environment node
 */
import { NextRequest } from 'next/server';
import { GET } from '@/app/api/lep/provisions/route';

const mockQuery = jest.fn();
const mockRelease = jest.fn();
jest.mock('@/lib/database/pool-manager', () => ({
  getClient: async () => ({ query: mockQuery, release: mockRelease }),
}));

const get = (qs: string) => GET(new NextRequest(`http://localhost/api/lep/provisions?${qs}`));

beforeEach(() => jest.clearAllMocks());

describe('GET /api/lep/provisions', () => {
  it('400s without an epi — a clause number alone is ambiguous across LEPs', async () => {
    const res = await get('clause=5.10');
    expect(res.status).toBe(400);
    expect(mockQuery).not.toHaveBeenCalled();
  });

  it("404s for an LEP whose text is not stored, without touching the DB (Waverley)", async () => {
    const res = await get('clause=5.10&epi=epi-2012-0540');
    expect(res.status).toBe(404);
    expect(mockQuery).not.toHaveBeenCalled();
  });

  it("queries only that instrument's rows for a stored LEP (Inner West)", async () => {
    mockQuery.mockResolvedValueOnce({
      rows: [{ clauseNumber: '5.10', clauseTitle: 'Heritage conservation', provisionText: 'x', pageNumber: 50 }],
    });
    const res = await get('clause=5.10&epi=EPI-2022-0457');
    expect(res.status).toBe(200);

    const [sql, params] = mockQuery.mock.calls[0];
    expect(params).toEqual(['5.10', 'Inner_West_Local_Environmental_Plan_2022']);
    expect(sql).toMatch(/left\(document_id, length\(\$2\)\) = \$2/);
    expect(sql).toMatch(/is_current IS NOT FALSE/);
    expect(mockRelease).toHaveBeenCalled();
  });
});
