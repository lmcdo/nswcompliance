/**
 * for-property: no council = refused, and a layer over its row cap fails the request.
 * Without the council check every council's rules were served (a Bayside parking lookup got
 * 1,980 rules from 12 other councils, live 2026-10-21). Without the cap check a layer over
 * 3,000 rows was cut silently.
 * @jest-environment node
 */
import { NextRequest } from 'next/server';

let genericRows = 0;
const row = (id: number) => ({
  id, document_id: 'Doc', provision_text: 'Text', v2_dcp_layer: 'generic',
  pdf_page: 4, ref_number: `Doc__C${id}`, source_council: 'marrickville',
});
// The mock stands in for the route queries: rows are is_current = TRUE rows, as the route filters.
const client = {
  query: jest.fn(async (sql: string, params?: unknown[]) => ({
    rows: /FROM regulatory_provisions rp/.test(sql) && (params ?? []).includes('generic')
      ? Array.from({ length: genericRows }, (_, i) => row(i + 1))
      : [],
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

const req = (qs: string) => new NextRequest(`http://x/api/provisions/for-property?${qs}`);

beforeEach(() => { client.query.mockClear(); genericRows = 0; });

describe('for-property council scope', () => {
  it('refuses an lga-only request before any rule query', async () => {
    const { GET } = await import('@/app/api/provisions/for-property/route');
    const res = await GET(req('lga=Bayside&zone=R2&topic=parking'));
    expect(res.status).toBe(400);
    // Any rule query (is_current = TRUE / v2_is_actionable) at all means the refusal came too late.
    const sqls = client.query.mock.calls.map((c) => String(c[0]));
    expect(sqls.some((s) => /FROM regulatory_provisions/.test(s))).toBe(false);
  });
});

describe('for-property row cap', () => {
  it('serves a layer at exactly the cap', async () => {
    genericRows = 3000;
    const { GET } = await import('@/app/api/provisions/for-property/route');
    const res = await GET(req('former_council=marrickville&zone=R2'));
    expect(res.status).toBe(200);
    expect((await res.json()).data.summary.layer_1_generic).toBe(3000);
  });

  it('fails the request when a layer has more rows than the cap', async () => {
    genericRows = 3001;
    const { GET } = await import('@/app/api/provisions/for-property/route');
    const res = await GET(req('former_council=marrickville&zone=R2'));
    expect(res.status).toBe(500);
    expect((await res.json()).details).toMatch(/exceed 3000 rows/);
  });

  it('asks the database for one row more than the cap', async () => {
    const { GET } = await import('@/app/api/provisions/for-property/route');
    await GET(req('former_council=marrickville&zone=R2'));
    const layerSql = client.query.mock.calls.map((c) => String(c[0]))
      .filter((s) => /AND v2_dcp_layer = \$/.test(s));
    expect(layerSql.length).toBeGreaterThan(0);
    for (const s of layerSql) expect(s).toMatch(/LIMIT 3001\b/);
  });
});
