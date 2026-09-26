/**
 * The page fallback (lib/citation-display, #1170) on every route that serves a DCP
 * rule's clause number to a live screen, not just /api/provisions/for-property:
 *   /api/browse/section             -> /dcp-browse
 *   /api/provisions/cross-references -> the "→ C4.9" link under a rule
 *   /api/clause/[id]                 -> quick search, referenced legislation
 * Each route is called with one proven and one unproven council row. Remove the
 * withServedCitation call from a route and its test fails.
 * @jest-environment node
 */
import { NextRequest } from 'next/server';

const mockQuery = jest.fn();
jest.mock('@/lib/db', () => ({ query: (...a: unknown[]) => mockQuery(...a) }));
jest.mock('pg', () => ({ Pool: jest.fn(() => ({ query: (...a: unknown[]) => mockQuery(...a) })) }));
jest.mock('@/lib/database/client', () => ({
  DatabaseClient: jest.fn(() => ({ execute: async (...a: unknown[]) => (await mockQuery(...a)).rows })),
}));
jest.mock('@/lib/rate-limit', () => ({
  dataRateLimiter: {},
  getClientIdentifier: () => 'test',
  checkRateLimit: async () => ({ success: true }),
  createRateLimitHeaders: () => ({}),
}));

const NL = '\n';
const proven = {
  ref_number: 'Doc__C3_2', provision_text: `# C3.2 Setbacks${NL}Text`,
  citation_status: 'proven', source_council: 'marrickville',
};
const unproven = {
  ref_number: 'Doc__C4_9', provision_text: `# C4.9 Fences${NL}Text`,
  citation_status: 'not_proven', source_council: 'woollahra',
};

beforeEach(() => mockQuery.mockReset());

describe('browse/section', () => {
  it('serves a proven number and drops an unproven one, keeping the page', async () => {
    const { POST } = await import('@/app/api/browse/section/route');
    mockQuery
      .mockResolvedValueOnce({ rows: [{ section_number: '3', section_title: 'x', page_start: 1, page_end: 9, depth: 1, parent_section: null }] })
      .mockResolvedValueOnce({ rows: [{ id: 1, pdf_page: 4, ...proven }, { id: 2, pdf_page: 5, ...unproven }] });
    const res = await POST(new NextRequest('http://x/api/browse/section', {
      method: 'POST', body: JSON.stringify({ sectionNumber: '3', documentId: 'Doc' }),
    }));
    const [a, b] = (await res.json()).data.provisions;
    expect(a.refNumber).toBe('Doc__C3_2');
    expect(a.provisionText).toContain('C3.2');
    expect(b.refNumber).toBeNull();
    expect(b.provisionText).toBe(`# Fences${NL}Text`);
    expect(b.pdfPage).toBe(5);
    expect(String(mockQuery.mock.calls[1][0])).toContain('citation_status');
  });
});

describe('provisions/cross-references', () => {
  it('drops an unproven target number', async () => {
    const { GET } = await import('@/app/api/provisions/cross-references/route');
    const target = (p: typeof proven, id: number) => ({
      id, target_provision_id: id, target_reference: p.ref_number, target_text: p.provision_text,
      target_citation_status: p.citation_status, target_source_council: p.source_council,
    });
    mockQuery.mockResolvedValueOnce({ rows: [target(proven, 1), target(unproven, 2)] });
    const res = await GET(new NextRequest('http://x/api/provisions/cross-references?provision_id=7'));
    const refs = (await res.json()).data.crossReferences;
    const [a, b] = refs;
    expect(a.targetReference).toBe('Doc__C3_2');
    expect(b.targetReference).toBeNull();
    expect(b.targetText).not.toContain('C4.9');
  });
});

describe('clause/[id]', () => {
  const call = async (row: typeof proven) => {
    const { GET } = await import('@/app/api/clause/[id]/route');
    mockQuery.mockResolvedValueOnce({ rows: [{
      id: 5, clause_reference: row.ref_number, full_text: row.provision_text, page_number: 12,
      document_id: 'Woollahra_DCP', citation_status: row.citation_status, source_council: row.source_council,
    }] });
    const res = await GET(new NextRequest('http://x/api/clause/5'), { params: { id: '5' } });
    return (await res.json()).clause;
  };

  it('keeps a proven number', async () => {
    expect((await call(proven)).clause_reference).toBe('Doc__C3_2');
  });

  it('replaces an unproven number and strips it from the text', async () => {
    const c = await call(unproven);
    expect(c.clause_reference).not.toContain('C4');
    expect(c.full_text).toBe(`# Fences${NL}Text`);
    expect(c.page_number).toBe(12);
  });

  it('serves an LEP/SEPP row (no council) as before', async () => {
    const c = await call({ ...unproven, citation_status: null as unknown as string, source_council: null as unknown as string });
    expect(c.clause_reference).toBe('Doc__C4_9');
  });
});
