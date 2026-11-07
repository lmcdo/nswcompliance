/**
 * GET /api/law-facts — the round trip and its failure semantics.
 *
 * The query reads the law_facts table only, strictly current, for one instrument and a fixed list of facts; a thrown query is a
 * 503 with `available: false` (never an empty 200 that reads as "the law sets no figure"); the client is always released.
 * @jest-environment node
 */
import { GET } from '@/app/api/law-facts/route';
import { LAW_FACT_KEYS } from '@/lib/law-facts';

const mockQuery = jest.fn();
const mockRelease = jest.fn();
jest.mock('@/lib/database/pool-manager', () => ({
  getClient: async () => ({ query: mockQuery, release: mockRelease }),
}));

beforeEach(() => jest.clearAllMocks());
const spy = jest.spyOn(console, 'error').mockImplementation(() => undefined);
afterAll(() => spy.mockRestore());

describe('GET /api/law-facts', () => {
  it('reads only law_facts, strictly current, for one instrument and the listed facts', async () => {
    mockQuery.mockResolvedValueOnce({ rows: [] });
    await GET();
    const [sql, params] = mockQuery.mock.calls[0];
    expect(sql).toMatch(/FROM law_facts/);
    expect(sql).toMatch(/WHERE is_current\s*$/m);
    expect(sql).not.toMatch(/is_current IS NOT FALSE/);
    expect(sql).not.toMatch(/regulatory_provisions|dcp_|source_council/);
    expect(params[0]).toBe('sepp_housing_2021');
    expect(params[1]).toEqual([...LAW_FACT_KEYS]);
    expect(mockRelease).toHaveBeenCalled();
  });

  it('serves the rows as facts with clause, page and law version date', async () => {
    mockQuery.mockResolvedValueOnce({
      rows: [{ fact_key: 'tod_fsr', value: '2.5:1', value_number: null, unit: null, clause: 's155(4)', pdf_page: 76, quote: 'q', law_version_date: '2026-10-23' }],
    });
    const body = await (await GET()).json();
    expect(body.available).toBe(true);
    expect(body.facts.tod_fsr).toMatchObject({ value: '2.5:1', clause: 's155(4)', pdfPage: 76, lawVersionDate: '2026-10-23' });
  });

  it('no rows is available:true with no facts (the page then prints no figure), not an invented default', async () => {
    mockQuery.mockResolvedValueOnce({ rows: [] });
    const body = await (await GET()).json();
    expect(body).toMatchObject({ available: true, facts: {} });
  });

  it('a failed query is a 503, available:false, with a message that is not a finding, and the client is released', async () => {
    mockQuery.mockRejectedValueOnce(new Error('relation "law_facts" does not exist'));
    const res = await GET();
    expect(res.status).toBe(503);
    const body = await res.json();
    expect(body.available).toBe(false);
    expect(body.facts).toEqual({});
    expect(body.message).toMatch(/not a finding/);
    expect(mockRelease).toHaveBeenCalled();
  });
});
