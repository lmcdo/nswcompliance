/**
 * OC-20: browse/section, clause/[id], provisions/by-ids and cross-references carry citation_checked.
 * A row proven only by page_check (citation_status not_proven) is checked; a NULL row is not.
 * Removing page_check from a route's SELECT, or an always-true helper, fails here.
 * @jest-environment node
 */
import { NextRequest } from 'next/server';
import { readFileSync } from 'fs';
import { join } from 'path';

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

const pageProven = { citation_status: 'not_proven', page_check: 'on_page', source_council: 'woollahra' };
const unproven = { citation_status: null, page_check: null, source_council: 'woollahra' };
const read = (rel: string) => readFileSync(join(__dirname, '../../', rel), 'utf8');

beforeEach(() => mockQuery.mockReset());

describe('browse/section', () => {
  it('flags page-proven true and NULL false, and selects page_check', async () => {
    const { POST } = await import('@/app/api/browse/section/route');
    const base = { document_id: 'Doc', ref_number: 'Doc__C3_2', provision_text: 'T', pdf_page: 4 };
    mockQuery
      .mockResolvedValueOnce({ rows: [{ section_number: '3', section_title: 'x', page_start: 1, page_end: 9, depth: 1, parent_section: null }] })
      .mockResolvedValueOnce({ rows: [{ id: 1, ...base, ...pageProven }, { id: 2, ...base, ...unproven }] });
    const res = await POST(new NextRequest('http://x/api/browse/section', {
      method: 'POST', body: JSON.stringify({ sectionNumber: '3', documentId: 'Doc' }),
    }));
    const [a, b] = (await res.json()).data.provisions;
    expect(a.citationChecked).toBe(true);
    expect(b.citationChecked).toBe(false);
    expect(String(mockQuery.mock.calls[1][0])).toContain('page_check');
  });
});

describe('provisions/cross-references', () => {
  it('flags the target', async () => {
    const { GET } = await import('@/app/api/provisions/cross-references/route');
    const t = (id: number, p: typeof pageProven) => ({
      id, target_provision_id: id, target_reference: 'Doc__C3_2', target_text: 'T',
      target_citation_status: p.citation_status, target_page_check: p.page_check, target_source_council: p.source_council,
    });
    mockQuery.mockResolvedValueOnce({ rows: [t(1, pageProven), t(2, unproven)] });
    const res = await GET(new NextRequest('http://x/api/provisions/cross-references?provision_id=7'));
    const [a, b] = (await res.json()).data.crossReferences;
    expect(a.targetCitationChecked).toBe(true);
    expect(b.targetCitationChecked).toBe(false);
  });
});

describe('selects the columns the flag needs', () => {
  it.each([
    'app/api/clause/[id]/route.ts',
    'app/api/provisions/by-ids/route.ts',
    'app/api/sepp/parking-provisions/route.ts',
  ])('%s', (rel) => {
    const src = read(rel);
    expect(src).toContain('citation_status');
    expect(src).toContain('page_check');
  });
  it('by-ids and clause return the flag', () => {
    expect(read('app/api/provisions/by-ids/route.ts')).toContain('citation_checked: isCitationChecked(row)');
    expect(read('app/api/clause/[id]/route.ts')).toContain('citation_checked');
  });
});
