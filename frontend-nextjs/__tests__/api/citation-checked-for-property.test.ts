/**
 * OC-20: the address page's rules carry citation_checked (lib/citation-display isCitationChecked,
 * the DQ-145 condition). Proven clause OR proven page = true; anything else, including NULL
 * columns, = false. Always-true mutation of isCitationChecked or removal of the SELECT columns fails.
 * @jest-environment node
 */
import { NextRequest } from 'next/server';
import { readFileSync } from 'fs';
import { join } from 'path';

const rowFor = (id: number, extra: Record<string, unknown>) => ({
  id, document_id: 'Doc', provision_text: 'Text', v2_dcp_layer: 'generic',
  pdf_page: 4, ref_number: `Doc__C${id}`, source_council: 'woollahra',
  citation_status: null, page_check: null, relevance_level: null, ...extra,
});
const ROWS = [
  rowFor(1, { citation_status: 'proven' }),
  rowFor(2, { page_check: 'on_page' }),
  rowFor(3, { citation_status: 'not_proven', page_check: 'not_found' }),
  rowFor(4, {}),
  rowFor(5, { citation_status: 'read_by_person' }),
];
const client = {
  query: jest.fn(async (sql: string) => ({
    rows: /FROM regulatory_provisions rp/.test(sql) && /rp\.page_check/.test(sql) ? ROWS : [],
  })),
  release: jest.fn(),
};
jest.mock('@/lib/db', () => ({ getPool: () => ({ connect: async () => client }) }));
jest.mock('@/lib/rate-limit', () => ({
  dataRateLimiter: {},
  getClientIdentifier: () => 'test',
  checkRateLimit: async () => ({ success: true }),
  createRateLimitHeaders: () => ({}),
}));
jest.mock('@/lib/posthog-server', () => ({ captureServerException: jest.fn() }));

describe('for-property citation_checked', () => {
  it('is true only for a proven clause or a proven page; false for unproven and NULL', async () => {
    const { GET } = await import('@/app/api/provisions/for-property/route');
    const res = await GET(new NextRequest(
      'http://x/api/provisions/for-property?groupBy=toc&zone=R2&former_council=woollahra'));
    const body = await res.json();
    const all = (body.data.by_layer as any[]).flatMap((l) => l.provisions);
    const byId = new Map<number, boolean>(all.map((p) => [p.id, p.citation_checked]));
    expect(byId.size).toBe(5);
    expect(byId.get(1)).toBe(true);
    expect(byId.get(2)).toBe(true);
    expect(byId.get(3)).toBe(false);
    expect(byId.get(4)).toBe(false);
    expect(byId.get(5)).toBe(false);
  });

  it('selects the columns the flag is computed from', () => {
    const src = readFileSync(join(__dirname, '../../app/api/provisions/for-property/route.ts'), 'utf8');
    const start = src.indexOf('const PROVISION_BASE_SELECT');
    const block = src.slice(start, src.indexOf('`;', start));
    expect(block).toContain('rp.citation_status');
    expect(block).toContain('rp.page_check');
  });
});
